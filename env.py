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

WORLD_X_MIN: float = -50.0
WORLD_X_MAX: float = 50.0
WORLD_Y_MIN: float = 0.0
WORLD_Y_MAX: float = 20.0
WORLD_Z_MIN: float = -50.0
WORLD_Z_MAX: float = 50.0


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
        terminate_on_boundary: bool = False,
    ):
        super().__init__()
        self.swarm_size = num_agents
        self.max_steps = max_steps
        self.dt = dt
        self.world_size = world_size
        self.reward_config = reward_config or RewardConfig()
        self.sensor_config = sensor_config or SensorConfig(range=20.0, field_of_view=np.pi / 2.0)
        self.include_global_state = include_global_state
        self.terminate_on_boundary = terminate_on_boundary

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

        # Place 8 static obstacles with rejection sampling to prevent Step-1 spawn collisions
        drone_positions_arr = np.array([d.position for d in self.drones.values()], dtype=np.float32)
        target_positions_arr = np.array([t.position for t in self.targets], dtype=np.float32)
        for i in range(8):
            obs_radius = 2.0
            o_pos = np.zeros(3, dtype=np.float32)
            for _ in range(50):
                candidate = np.array(
                    [
                        float(rng.uniform(-35.0, 35.0)),
                        float(rng.uniform(2.0, 8.0)),
                        float(rng.uniform(-35.0, 35.0)),
                    ],
                    dtype=np.float32,
                )
                min_drone_d = float(np.min(np.linalg.norm(drone_positions_arr - candidate, axis=1)))
                min_target_d = float(
                    np.min(np.linalg.norm(target_positions_arr[:, [0, 2]] - candidate[[0, 2]], axis=1))
                )
                if min_drone_d >= (obs_radius + 3.5) and min_target_d >= (obs_radius + 3.5):
                    o_pos = candidate
                    break
            else:
                o_pos = candidate
            self.obstacles.append(ArenaObject(id=f"obstacle_{i}", type="obstacle", position=o_pos, radius=obs_radius))

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
        batch_obs = self._compute_observations_batch(self.agents)
        observations = {}
        for i, agent in enumerate(self.agents):
            local_obs = batch_obs[i]
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

    def _compute_observations_batch(
        self,
        agent_ids: list[str],
        pos_matrix: Optional[np.ndarray] = None,
        dist_matrix: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """Vectorized observation computation for a batch of active agents."""
        n_agents = len(agent_ids)
        if n_agents == 0:
            return np.zeros((0, 81), dtype=np.float32)

        if pos_matrix is None:
            pos_matrix = np.array([self.drones[a].position for a in agent_ids], dtype=np.float32)
        vel_matrix = np.array([self.drones[a].velocity for a in agent_ids], dtype=np.float32)
        headings = np.array([self.drones[a].heading for a in agent_ids], dtype=np.float32)

        # 1. Self Kinematics (N, 8)
        self_feat = np.empty((n_agents, 8), dtype=np.float32)
        self_feat[:, 0] = pos_matrix[:, 0] / 50.0
        self_feat[:, 1] = pos_matrix[:, 1] / 20.0
        self_feat[:, 2] = pos_matrix[:, 2] / 50.0
        self_feat[:, 3] = vel_matrix[:, 0] / 10.0
        self_feat[:, 4] = vel_matrix[:, 1] / 3.0
        self_feat[:, 5] = vel_matrix[:, 2] / 10.0
        self_feat[:, 6] = np.cos(headings)
        self_feat[:, 7] = np.sin(headings)

        # 2. K-Nearest Neighbors (N, 24: 6 neighbors * 4 features)
        knn_feat = np.zeros((n_agents, 24), dtype=np.float32)
        knn_feat[:, 3::4] = 1.0  # Default normalized distance = 1.0

        alive_ids = [a_id for a_id, d in self.drones.items() if d.alive]
        if len(alive_ids) > 1:
            if alive_ids == agent_ids and dist_matrix is not None:
                all_alive_pos = pos_matrix
                d_mat = dist_matrix.copy()
                np.fill_diagonal(d_mat, np.inf)
            else:
                all_alive_pos = np.array([self.drones[a].position for a in alive_ids], dtype=np.float32)
                d_mat = cdist(pos_matrix, all_alive_pos).astype(np.float32)
                d_mat[d_mat <= 1e-8] = np.inf

            diffs = all_alive_pos[None, :, :] - pos_matrix[:, None, :]  # (N, M_alive, 3)
            k_neighbors = min(6, len(alive_ids) - 1)
            if k_neighbors > 0:
                if d_mat.shape[1] > k_neighbors:
                    part_idx = np.argpartition(d_mat, kth=k_neighbors - 1, axis=1)[:, :k_neighbors]
                    part_d = np.take_along_axis(d_mat, part_idx, axis=1)
                    order = np.argsort(part_d, axis=1)
                    sorted_idx = np.take_along_axis(part_idx, order, axis=1)
                else:
                    sorted_idx = np.argsort(d_mat, axis=1)[:, :k_neighbors]

                for slot in range(k_neighbors):
                    nbr_idx = sorted_idx[:, slot]
                    nbr_dist = d_mat[np.arange(n_agents), nbr_idx]
                    in_comm = nbr_dist <= COMM_RADIUS
                    nbr_diff = diffs[np.arange(n_agents), nbr_idx] / COMM_RADIUS
                    base = slot * 4
                    knn_feat[:, base : base + 3] = np.where(in_comm[:, None], nbr_diff, 0.0)
                    knn_feat[:, base + 3] = np.where(in_comm, nbr_dist / COMM_RADIUS, 1.0)

        # 3. Vectorized Sensor Cone Vector (N, 24)
        obj_pos_list: list[np.ndarray] = []
        obj_type_list: list[float] = []
        for target in self.targets:
            if not target.found:
                obj_pos_list.append(target.position)
                obj_type_list.append(1.0)
        for obstacle in self.obstacles:
            obj_pos_list.append(obstacle.position)
            obj_type_list.append(2.0)
        for a_id in alive_ids:
            obj_pos_list.append(self.drones[a_id].position)
            obj_type_list.append(3.0)

        if obj_pos_list:
            obj_positions = np.asarray(obj_pos_list, dtype=np.float32)
            obj_types = np.asarray(obj_type_list, dtype=np.float32)
            sensor_feat = self.cone_sensor.detect_and_vectorize_batch(
                agent_positions=pos_matrix,
                agent_headings=headings,
                object_positions=obj_positions,
                object_type_codes=obj_types,
            )
        else:
            sensor_feat = np.zeros((n_agents, 24), dtype=np.float32)

        # 4. Local Exploration Patch (N, 25: 5x5 grid slice)
        grid_feat = np.empty((n_agents, 25), dtype=np.float32)
        for i in range(n_agents):
            local_patch = self.exploration_map.get_local_patch(pos_matrix[i], radius_cells=2)
            grid_feat[i] = local_patch.ravel()

        return np.concatenate([self_feat, knn_feat, sensor_feat, grid_feat], axis=1).astype(np.float32)

    def _get_observation(self, agent_id: str) -> np.ndarray:
        return self._compute_observations_batch([agent_id])[0]

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
        pos_matrix: Optional[np.ndarray] = None
        dist_matrix: Optional[np.ndarray] = None

        if len(active_agents) > 0:
            pos_matrix = np.array([self.drones[a].position for a in active_agents], dtype=np.float32)
            if len(active_agents) > 1:
                dist_matrix = cdist(pos_matrix, pos_matrix).astype(np.float32)
                np.fill_diagonal(dist_matrix, np.inf)

                min_dists = np.min(dist_matrix, axis=1)
                for i, a in enumerate(active_agents):
                    min_neighbor_dists[a] = float(min_dists[i])

                collision_indices = np.where(dist_matrix < 2.0)
                for idx in collision_indices[0]:
                    drone_collisions.add(active_agents[idx])

        # 4. Obstacle collisions, boundary violations, and symmetric target discovery
        obstacle_collisions: set[str] = set()
        boundary_violations: set[str] = set()
        targets_found_by_agent: set[str] = set()
        newly_discovered_targets: list[ArenaObject] = []

        for agent_id in active_agents:
            pos = self.drones[agent_id].position

            # Boundary checks & collision response
            if not (
                WORLD_X_MIN <= pos[0] <= WORLD_X_MAX
                and WORLD_Y_MIN <= pos[1] <= WORLD_Y_MAX
                and WORLD_Z_MIN <= pos[2] <= WORLD_Z_MAX
            ):
                boundary_violations.add(agent_id)
                # Boundary collision response: damp velocity and correct position
                drone = self.drones[agent_id]
                drone.position[0] = np.clip(drone.position[0], WORLD_X_MIN, WORLD_X_MAX)
                drone.position[1] = np.clip(drone.position[1], WORLD_Y_MIN, WORLD_Y_MAX)
                drone.position[2] = np.clip(drone.position[2], WORLD_Z_MIN, WORLD_Z_MAX)
                drone.velocity *= 0.1

            # Obstacle checks
            for obs in self.obstacles:
                if float(np.linalg.norm(pos - obs.position)) < (obs.radius + 1.0):
                    obstacle_collisions.add(agent_id)
                    break

            # Symmetric aerial target discovery (horizontal x-z ground footprint <= 3.0m)
            for target in self.targets:
                if not target.found:
                    horiz_dist = float(np.hypot(pos[0] - target.position[0], pos[2] - target.position[2]))
                    if horiz_dist <= 3.0 and 0.0 <= pos[1] <= 20.0:
                        targets_found_by_agent.add(agent_id)
                        if target not in newly_discovered_targets:
                            newly_discovered_targets.append(target)

        for target in newly_discovered_targets:
            target.found = True

        team_target_found_this_step = len(newly_discovered_targets) > 0
        all_targets_found = all(t.found for t in self.targets)

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
            has_found_target = agent_id in targets_found_by_agent
            agent_min_dist = min_neighbor_dists.get(agent_id)

            total_reward, details = calculate_reward(
                agent_id=agent_id,
                new_cells=agent_new_cells.get(agent_id, 0),
                previously_explored=(agent_new_cells.get(agent_id, 0) == 0),
                target_found=has_found_target,
                drone_collision=has_drone_coll,
                obstacle_collision=has_obs_coll,
                boundary_violation=has_bound_viol,
                config=self.reward_config,
                team_cells=total_team_cells,
                team_target_found=team_target_found_this_step,
                min_neighbor_dist=agent_min_dist,
            )

            # Expose raw diagnostic counters alongside weighted reward breakdown
            details["team_cells"] = int(total_team_cells)
            details["min_neighbor_dist"] = agent_min_dist
            details["team_target_found_flag"] = bool(team_target_found_this_step)

            rewards[agent_id] = float(total_reward)
            infos[agent_id] = {
                "reward_breakdown": details,
                "event_flags": {
                    "drone_collision": has_drone_coll,
                    "obstacle_collision": has_obs_coll,
                    "target_found": has_found_target,
                    "boundary_violation": has_bound_viol,
                    "team_cells": int(total_team_cells),
                    "team_target_found": bool(team_target_found_this_step),
                    "min_neighbor_dist": agent_min_dist,
                },
            }

            is_dead = has_drone_coll or has_obs_coll or (has_bound_viol if self.terminate_on_boundary else False)
            if is_dead:
                self.drones[agent_id].alive = False

            terminations[agent_id] = bool(is_dead or all_targets_found)
            truncations[agent_id] = bool(is_truncated)

        global_state = self.state() if self.include_global_state else None
        batch_obs = self._compute_observations_batch(
            active_agents,
            pos_matrix=pos_matrix,
            dist_matrix=dist_matrix,
        )
        observations = {}
        for i, agent in enumerate(active_agents):
            local_obs = batch_obs[i]
            if self.include_global_state:
                observations[agent] = {"obs": local_obs, "state": global_state}
            else:
                observations[agent] = local_obs

        # Update remaining active agents
        self.agents = [
            a for a in self.agents
            if self.drones[a].alive and not is_truncated and not all_targets_found
        ]

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
