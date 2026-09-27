from dataclasses import dataclass, field
from typing import Any, Optional

import gymnasium as gym
from gymnasium.spaces import Box
import numpy as np
from pettingzoo import ParallelEnv
from scipy.spatial.distance import cdist

from sensors.sensors import ConeSensor, SensorConfig
from sensors.exploration import ExplorationMap, ExplorationConfig
from sensors.rewards import RewardConfig, calculate_reward


MAX_HORIZ_VEL = 10.0
MAX_VERT_VEL = 3.0
MAX_YAW_RATE = np.pi
COMM_RADIUS = 30.0
DEFAULT_NUM_AGENTS = 50


@dataclass
class DroneState:
    position: np.ndarray
    velocity: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=np.float32))
    heading: float = 0.0
    alive: bool = True


@dataclass
class ArenaObject:
    id: str
    type: str
    position: np.ndarray
    radius: float = 1.0
    found: bool = False


class SwarmRLParallelEnv(ParallelEnv):
    metadata = {"render_modes": ["human"], "name": "swarmrl_v0"}

    def __init__(
        self,
        num_agents: int = DEFAULT_NUM_AGENTS,
        max_steps: int = 1000,
        dt: float = 0.05,
        world_size: tuple[float, float] = (100.0, 100.0),
        reward_config: Optional[RewardConfig] = None,
        sensor_config: Optional[SensorConfig] = None,
        include_global_state: bool = False,
    ):
        super().__init__()
        self.swarm_size = num_agents
        self.max_steps = max_steps
        self.dt = dt
        self.world_size = world_size
        self.reward_config = reward_config or RewardConfig()
        self.sensor_config = sensor_config or SensorConfig(range=20.0, field_of_view=np.pi / 2.0)
        self.include_global_state = include_global_state

        self.cone_sensor = ConeSensor(self.sensor_config)
        self.exploration_map = ExplorationMap(
            config=ExplorationConfig(
                world_size=self.world_size,
                cell_size=2.0,
                exploration_radius=2.0,
            )
        )

        self.possible_agents = [f"drone_{i}" for i in range(self.swarm_size)]
        self.agents = self.possible_agents.copy()

        # 4-DoF continuous action: [vx, vy, vz, yaw_rate] normalized to [-1.0, 1.0]
        self._action_spaces = {
            agent: Box(low=-1.0, high=1.0, shape=(4,), dtype=np.float32)
            for agent in self.possible_agents
        }

        # 81-dim continuous observation: 8 ego + 24 KNN + 24 ConeSensor + 25 local patch
        # (Optionally wrapped in Dict({"obs": (81,), "state": (471,)}) for RLlib MAPPO Centralized Critic)
        state_dim = self.swarm_size * 9 + 5 * 4 + 1
        self._observation_spaces = {}
        for agent in self.possible_agents:
            local_box = Box(low=-np.inf, high=np.inf, shape=(81,), dtype=np.float32)
            if self.include_global_state:
                self._observation_spaces[agent] = gym.spaces.Dict({
                    "obs": local_box,
                    "state": Box(low=-np.inf, high=np.inf, shape=(state_dim,), dtype=np.float32),
                })
            else:
                self._observation_spaces[agent] = local_box

        self.drones: dict[str, DroneState] = {}
        self.targets: list[ArenaObject] = []
        self.obstacles: list[ArenaObject] = []
        self.step_count = 0

    def action_space(self, agent: str) -> gym.Space:
        return self._action_spaces[agent]

    def observation_space(self, agent: str) -> gym.Space:
        return self._observation_spaces[agent]

    def _init_world(self, seed: Optional[int] = None):
        rng = np.random.default_rng(seed)
        self.drones.clear()
        self.targets.clear()
        self.obstacles.clear()

        # Place 50 drones spaced in a 10x5 grid around origin
        cols, rows = 10, self.swarm_size // 10
        spacing = 5.0
        start_x = -((cols - 1) * spacing) / 2.0
        start_z = -((rows - 1) * spacing) / 2.0

        for i, agent_id in enumerate(self.possible_agents):
            c = i % cols
            r = i // cols
            pos = np.array([start_x + c * spacing, 5.0, start_z + r * spacing], dtype=np.float32)
            # Add slight jitter to avoid exact collinear initial alignments
            pos[0] += float(rng.uniform(-0.5, 0.5))
            pos[2] += float(rng.uniform(-0.5, 0.5))
            heading = float(rng.uniform(0.0, 2.0 * np.pi))
            self.drones[agent_id] = DroneState(position=pos, heading=heading)

        # Place 5 rescue targets across arena
        for i in range(5):
            t_pos = np.array(
                [
                    float(rng.uniform(-40.0, 40.0)),
                    0.5,
                    float(rng.uniform(-40.0, 40.0)),
                ],
                dtype=np.float32,
            )
            self.targets.append(ArenaObject(id=f"target_{i}", type="target", position=t_pos, radius=1.5))

        # Place 8 static obstacles
        for i in range(8):
            o_pos = np.array(
                [
                    float(rng.uniform(-35.0, 35.0)),
                    float(rng.uniform(2.0, 8.0)),
                    float(rng.uniform(-35.0, 35.0)),
                ],
                dtype=np.float32,
            )
            self.obstacles.append(ArenaObject(id=f"obstacle_{i}", type="obstacle", position=o_pos, radius=2.0))

    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[dict] = None,
    ) -> tuple[dict[str, np.ndarray], dict[str, dict]]:
        self.agents = self.possible_agents.copy()
        self.step_count = 0
        self._init_world(seed=seed)
        self.exploration_map.reset()

        # Initial symmetric exploration marking
        agent_positions = {a: d.position for a, d in self.drones.items()}
        self.exploration_map.mark_explored_per_agent(agent_positions, radius=2.0)

        global_state = self.state() if self.include_global_state else None
        observations = {}
        for agent in self.agents:
            local_obs = self._get_observation(agent)
            if self.include_global_state:
                observations[agent] = {"obs": local_obs, "state": global_state}
            else:
                observations[agent] = local_obs
        infos = {agent: {} for agent in self.agents}
        return observations, infos

    def _get_sensor_objects(self, exclude_agent_id: str) -> list[dict[str, Any]]:
        objects: list[dict[str, Any]] = []
        for target in self.targets:
            if not target.found:
                objects.append({"id": target.id, "type": "target", "position": target.position})

        for obstacle in self.obstacles:
            objects.append({"id": obstacle.id, "type": "obstacle", "position": obstacle.position})

        for agent_id, drone in self.drones.items():
            if agent_id != exclude_agent_id and drone.alive:
                objects.append({"id": agent_id, "type": "drone", "position": drone.position})

        return objects

    def _get_observation(self, agent_id: str) -> np.ndarray:
        drone = self.drones[agent_id]

        # 1. Self Kinematics (8 floats)
        self_feat = [
            drone.position[0] / 50.0,
            drone.position[1] / 20.0,
            drone.position[2] / 50.0,
            drone.velocity[0] / 10.0,
            drone.velocity[1] / 3.0,
            drone.velocity[2] / 10.0,
            float(np.cos(drone.heading)),
            float(np.sin(drone.heading)),
        ]

        # 2. K-Nearest Neighbors (24 floats: 6 neighbors * 4 features)
        alive_neighbors = [
            (a_id, d) for a_id, d in self.drones.items()
            if a_id != agent_id and d.alive
        ]

        if alive_neighbors:
            diffs = np.array([d.position - drone.position for _, d in alive_neighbors], dtype=np.float32)
            dists = np.linalg.norm(diffs, axis=1)
            sorted_indices = np.argsort(dists)[:6]

            knn_feat: list[float] = []
            for idx in sorted_indices:
                dist = float(dists[idx])
                if dist <= COMM_RADIUS:
                    rel = diffs[idx] / COMM_RADIUS
                    knn_feat.extend([float(rel[0]), float(rel[1]), float(rel[2]), dist / COMM_RADIUS])
                else:
                    knn_feat.extend([0.0, 0.0, 0.0, 1.0])
        else:
            knn_feat = []

        while len(knn_feat) < 24:
            knn_feat.extend([0.0, 0.0, 0.0, 1.0])

        # 3. Sensor Cone Vector (24 floats: 8 objects * 3 features)
        sensor_objs = self._get_sensor_objects(exclude_agent_id=agent_id)
        detections = self.cone_sensor.detect(drone.position, drone.heading, sensor_objs)
        sensor_feat = self.cone_sensor.vectorize(detections).tolist()

        # 4. Local Exploration Patch (25 floats: 5x5 grid slice)
        local_patch = self.exploration_map.get_local_patch(drone.position, radius_cells=2)
        grid_feat = local_patch.flatten().tolist()

        obs = np.asarray(self_feat + knn_feat + sensor_feat + grid_feat, dtype=np.float32)
        return obs

    def step(
        self,
        actions: dict[str, np.ndarray],
    ) -> tuple[
        dict[str, np.ndarray],
        dict[str, float],
        dict[str, bool],
        dict[str, bool],
        dict[str, dict],
    ]:
        self.step_count += 1
        active_agents = [a for a in self.agents if self.drones[a].alive]

        # 1. Apply actions to kinematics
        for agent_id in active_agents:
            if agent_id in actions:
                act = np.clip(np.asarray(actions[agent_id], dtype=np.float32), -1.0, 1.0)
                v_x = float(act[0]) * MAX_HORIZ_VEL
                v_y = float(act[1]) * MAX_VERT_VEL
                v_z = float(act[2]) * MAX_HORIZ_VEL
                yaw_rate = float(act[3]) * MAX_YAW_RATE

                drone = self.drones[agent_id]
                drone.heading = float((drone.heading + yaw_rate * self.dt) % (2.0 * np.pi))
                drone.velocity = np.array([v_x, v_y, v_z], dtype=np.float32)
                drone.position = drone.position + drone.velocity * self.dt

        # 2. Symmetric exploration update
        agent_positions = {a: self.drones[a].position for a in active_agents}
        agent_new_cells, total_team_cells = self.exploration_map.mark_explored_per_agent(
            agent_positions,
            radius=2.0,
        )

        # 3. Vectorized pairwise neighbor distances & drone collisions
        min_neighbor_dists: dict[str, Optional[float]] = {a: None for a in active_agents}
        drone_collisions: set[str] = set()

        if len(active_agents) > 1:
            pos_matrix = np.array([self.drones[a].position for a in active_agents], dtype=np.float32)
            dist_matrix = cdist(pos_matrix, pos_matrix)
            np.fill_diagonal(dist_matrix, np.inf)

            min_dists = np.min(dist_matrix, axis=1)
            for i, a in enumerate(active_agents):
                min_neighbor_dists[a] = float(min_dists[i])

            collision_indices = np.where(dist_matrix < 2.0)
            for idx in collision_indices[0]:
                drone_collisions.add(active_agents[idx])

        # 4. Obstacle collisions, boundary violations, and target discovery
        obstacle_collisions: set[str] = set()
        boundary_violations: set[str] = set()
        targets_found_by_agent: set[str] = set()
        team_target_found_this_step = False

        for agent_id in active_agents:
            pos = self.drones[agent_id].position

            # Boundary checks
            if not (-50.0 <= pos[0] <= 50.0 and 0.0 <= pos[1] <= 20.0 and -50.0 <= pos[2] <= 50.0):
                boundary_violations.add(agent_id)

            # Obstacle checks
            for obs in self.obstacles:
                if float(np.linalg.norm(pos - obs.position)) < (obs.radius + 1.0):
                    obstacle_collisions.add(agent_id)
                    break

            # Target checks
            for target in self.targets:
                if not target.found:
                    if float(np.linalg.norm(pos - target.position)) <= 3.0:
                        target.found = True
                        targets_found_by_agent.add(agent_id)
                        team_target_found_this_step = True

        # 5. Reward computation & unpack
        rewards: dict[str, float] = {}
        infos: dict[str, dict] = {}
        terminations: dict[str, bool] = {}
        truncations: dict[str, bool] = {}

        is_truncated = self.step_count >= self.max_steps

        for agent_id in active_agents:
            has_drone_coll = agent_id in drone_collisions
            has_obs_coll = agent_id in obstacle_collisions
            has_bound_viol = agent_id in boundary_violations

            total_reward, details = calculate_reward(
                agent_id=agent_id,
                new_cells=agent_new_cells.get(agent_id, 0),
                previously_explored=(agent_new_cells.get(agent_id, 0) == 0),
                target_found=(agent_id in targets_found_by_agent),
                drone_collision=has_drone_coll,
                obstacle_collision=has_obs_coll,
                boundary_violation=has_bound_viol,
                config=self.reward_config,
                team_cells=total_team_cells,
                team_target_found=team_target_found_this_step,
                min_neighbor_dist=min_neighbor_dists.get(agent_id),
            )

            rewards[agent_id] = float(total_reward)
            infos[agent_id] = {"reward_breakdown": details}

            is_terminated = has_drone_coll or has_obs_coll or has_bound_viol
            if is_terminated:
                self.drones[agent_id].alive = False

            terminations[agent_id] = is_terminated
            truncations[agent_id] = is_truncated

        global_state = self.state() if self.include_global_state else None
        observations = {}
        for agent in active_agents:
            local_obs = self._get_observation(agent)
            if self.include_global_state:
                observations[agent] = {"obs": local_obs, "state": global_state}
            else:
                observations[agent] = local_obs

        # Update remaining active agents
        self.agents = [a for a in self.agents if self.drones[a].alive and not is_truncated]

        all_targets_found = all(t.found for t in self.targets)
        all_drones_dead = all(not self.drones[a].alive for a in self.possible_agents)
        terminations["__all__"] = bool(all_drones_dead or all_targets_found)
        truncations["__all__"] = bool(is_truncated)

        return observations, rewards, terminations, truncations, infos

    def state(self) -> np.ndarray:
        """Canonical global state vector for MAPPO centralized critic."""
        state_vector: list[float] = []

        for agent_id in self.possible_agents:
            if agent_id in self.drones and self.drones[agent_id].alive:
                d = self.drones[agent_id]
                state_vector.extend([
                    d.position[0] / 50.0,
                    d.position[1] / 20.0,
                    d.position[2] / 50.0,
                    d.velocity[0] / 10.0,
                    d.velocity[1] / 3.0,
                    d.velocity[2] / 10.0,
                    float(np.cos(d.heading)),
                    float(np.sin(d.heading)),
                    1.0,
                ])
            else:
                state_vector.extend([0.0] * 8 + [0.0])

        for target in self.targets:
            state_vector.extend([
                target.position[0] / 50.0,
                target.position[1] / 20.0,
                target.position[2] / 50.0,
                1.0 if target.found else 0.0,
            ])

        state_vector.append(self.exploration_map.explored_fraction)
        return np.asarray(state_vector, dtype=np.float32)
