from dataclasses import dataclass, field
from typing import Any, Optional
import functools

import gymnasium as gym
from gymnasium.spaces import Box
import numpy as np
from pettingzoo import ParallelEnv

from sensors.cone_sensor import ConeSensor, ConeSensorConfig
from sensors.exploration import ExplorationMap, ExplorationConfig
from sensors.rewards import RewardConfig, calculate_reward
from sensors.scenario import (
    ScenarioConfig,
    scenario_preset,
    get_difficulty_config,
    generate_spawn_positions,
)
from sensors.events import (
    EventConfig,
    detect_drone_collisions_vectorized,
    detect_obstacle_collisions_vectorized,
    detect_target_found_vectorized,
)

# World constants
WORLD_X_MIN: float = -50.0
WORLD_X_MAX: float = 50.0
WORLD_Y_MIN: float = 0.0
WORLD_Y_MAX: float = 20.0
WORLD_Z_MIN: float = -50.0
WORLD_Z_MAX: float = 50.0

WORLD_X_SPAN: float = WORLD_X_MAX - WORLD_X_MIN  # 100.0
WORLD_Y_SPAN: float = WORLD_Y_MAX - WORLD_Y_MIN  # 20.0
WORLD_Z_SPAN: float = WORLD_Z_MAX - WORLD_Z_MIN  # 100.0

EXPLORATION_CELL_SIZE: float = 2.0
DEFAULT_NUM_AGENTS: int = 50
DEFAULT_MAX_STEPS: int = 500
DT: float = 0.1

MAX_HORIZ_VEL: float = 10.0
MAX_VERT_VEL: float = 3.0
MAX_YAW_RATE: float = np.pi


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
    height: float = 20.0
    found: bool = False


class DroneProxy:
    def __init__(self, env: "SwarmRLParallelEnv", idx: int):
        self._env = env
        self._idx = idx

    @property
    def position(self) -> np.ndarray:
        return self._env.positions[self._idx]

    @position.setter
    def position(self, val: Any) -> None:
        self._env.positions[self._idx] = np.asarray(val, dtype=np.float32)

    @property
    def velocity(self) -> np.ndarray:
        return self._env.velocities[self._idx]

    @velocity.setter
    def velocity(self, val: Any) -> None:
        self._env.velocities[self._idx] = np.asarray(val, dtype=np.float32)

    @property
    def heading(self) -> float:
        return float(self._env.headings[self._idx])

    @heading.setter
    def heading(self, val: float) -> None:
        self._env.headings[self._idx] = float(val)

    @property
    def alive(self) -> bool:
        return bool(self._env.alive[self._idx] > 0.5)

    @alive.setter
    def alive(self, val: bool) -> None:
        self._env.alive[self._idx] = 1.0 if val else 0.0


class SwarmRLParallelEnv(ParallelEnv):
    metadata = {"render_modes": ["human"], "name": "swarmrl_v0"}

    def __init__(
        self,
        num_agents: int = DEFAULT_NUM_AGENTS,
        max_steps: int = DEFAULT_MAX_STEPS,
        dt: float = DT,
        difficulty: int = 0,
        reward_config: Optional[RewardConfig] = None,
        sensor_config: Optional[ConeSensorConfig] = None,
        include_global_state: bool = False,
        terminate_on_boundary: bool = False,
        render_mode: Optional[str] = None,
    ):
        super().__init__()
        self.swarm_size = num_agents
        self.max_steps = max_steps
        self.dt = dt
        self.difficulty = difficulty
        self.reward_config = reward_config or RewardConfig()
        self.sensor_config = sensor_config or ConeSensorConfig(range=15.0, half_angle=np.pi / 6.0, max_objects=8)
        self.include_global_state = include_global_state
        self.terminate_on_boundary = terminate_on_boundary
        self.render_mode = render_mode

        self.cone_sensor = ConeSensor(self.sensor_config)
        self.exploration_map = ExplorationMap(
            config=ExplorationConfig(
                world_size=(WORLD_X_SPAN, WORLD_Z_SPAN),
                cell_size=EXPLORATION_CELL_SIZE,
                exploration_radius=2.0,
            )
        )
        self.event_config = EventConfig(
            drone_collision_distance=2.0,
            obstacle_collision_distance=1.0,
            target_detection_distance=3.0,
            boundary_tolerance=0.0,
        )

        self.possible_agents = [f"drone_{i}" for i in range(self.swarm_size)]
        self.agents = self.possible_agents.copy()
        self.agent_to_idx = {agent: i for i, agent in enumerate(self.possible_agents)}

        # Spaces
        state_dim = 471
        self._action_spaces = {
            agent: Box(low=-1.0, high=1.0, shape=(4,), dtype=np.float32)
            for agent in self.possible_agents
        }
        self._observation_spaces: dict[str, gym.Space] = {}
        for agent in self.possible_agents:
            obs_box = Box(low=-np.inf, high=np.inf, shape=(81,), dtype=np.float32)
            if self.include_global_state:
                self._observation_spaces[agent] = gym.spaces.Dict({
                    "obs": obs_box,
                    "state": Box(low=-np.inf, high=np.inf, shape=(state_dim,), dtype=np.float32),
                })
            else:
                self._observation_spaces[agent] = obs_box

        self.state_space = Box(low=-np.inf, high=np.inf, shape=(state_dim,), dtype=np.float32)

        # Internal state matrices
        self.positions = generate_spawn_positions(self.swarm_size)
        self.velocities = np.zeros((self.swarm_size, 3), dtype=np.float32)
        self.headings = np.zeros(self.swarm_size, dtype=np.float32)
        self.alive = np.ones(self.swarm_size, dtype=np.float32)

        # Dict interfaces for backward/proxy compatibility
        self.drones: dict[str, DroneProxy] = {
            agent: DroneProxy(self, i) for i, agent in enumerate(self.possible_agents)
        }
        self.obstacles: list[ArenaObject] = []
        self.targets: list[ArenaObject] = []
        self.step_count = 0
        self.rng = np.random.default_rng(42)
        self.wind_rng = np.random.default_rng(42)
        self.wind_strength = 0.0
        self.base_wind = np.zeros(3, dtype=np.float32)

        self.collision_totals = {
            "drone": 0,
            "obstacle": 0,
            "boundary": 0,
            "total": 0,
        }
        self.targets_found_count = 0

    @functools.lru_cache(maxsize=None)
    def observation_space(self, agent: str) -> gym.Space:
        return self._observation_spaces[agent]

    @functools.lru_cache(maxsize=None)
    def action_space(self, agent: str) -> Box:
        return self._action_spaces[agent]

    def set_difficulty(self, difficulty: int) -> None:
        if difficulty not in range(5):
            raise ValueError(f"Difficulty must be 0-4, got {difficulty}")
        self.difficulty = difficulty

    def _init_world(self, seed: Optional[int] = None) -> None:
        rng = np.random.default_rng(seed)
        diff_cfg = get_difficulty_config(self.difficulty)
        self.wind_strength = diff_cfg.wind_strength
        if self.wind_strength > 0:
            angle = float(self.wind_rng.uniform(0, 2 * np.pi))
            self.base_wind = np.array([np.cos(angle), 0.0, np.sin(angle)], dtype=np.float32) * self.wind_strength
        else:
            self.base_wind = np.zeros(3, dtype=np.float32)

        self.positions = generate_spawn_positions(self.swarm_size)
        self.velocities = np.zeros((self.swarm_size, 3), dtype=np.float32)
        self.headings = np.zeros(self.swarm_size, dtype=np.float32)
        self.alive = np.ones(self.swarm_size, dtype=np.float32)

        self.obstacles.clear()
        self.targets.clear()

        # Generate obstacles strictly away from spawn points
        for i in range(diff_cfg.num_obstacles):
            radius = float(rng.uniform(1.5, 3.5))
            height = float(rng.uniform(6.0, 18.0))
            valid = False
            for _ in range(100):
                x = float(rng.uniform(-40.0, 40.0))
                z = float(rng.uniform(-40.0, 40.0))
                dists = np.hypot(self.positions[:, 0] - x, self.positions[:, 2] - z)
                if not np.any(dists < (radius + 4.0)):
                    valid = True
                    break
            if valid:
                pos = np.array([x, height / 2.0, z], dtype=np.float32)
                self.obstacles.append(ArenaObject(id=f"obstacle_{i}", type="obstacle", position=pos, radius=radius, height=height))

        # Generate targets
        for i in range(diff_cfg.num_targets):
            for _ in range(100):
                x = float(rng.uniform(-40.0, 40.0))
                z = float(rng.uniform(-40.0, 40.0))
                y = 0.5
                dists_spawns = np.hypot(self.positions[:, 0] - x, self.positions[:, 2] - z)
                if not np.any(dists_spawns < 6.0):
                    break
            pos = np.array([x, y, z], dtype=np.float32)
            self.targets.append(ArenaObject(id=f"target_{i}", type="target", position=pos, radius=1.0, height=1.0, found=False))

    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[dict[str, Any]] = None,
    ) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
        if seed is not None:
            self.rng = np.random.default_rng(seed)
            self.wind_rng = np.random.default_rng(seed)

        if options and "difficulty" in options:
            self.set_difficulty(int(options["difficulty"]))

        self.agents = self.possible_agents.copy()
        self.step_count = 0
        self.collision_totals = {"drone": 0, "obstacle": 0, "boundary": 0, "total": 0}
        self.targets_found_count = 0

        self._init_world(seed=seed)
        self.exploration_map.reset()

        # Initial symmetric exploration marking
        agent_pos_dict = {f"drone_{i}": self.positions[i] for i in range(self.swarm_size)}
        self.exploration_map.mark_explored_per_agent(agent_pos_dict)

        observations = self._build_all_observations()
        infos = {agent: {"reward_breakdown": {}, "event_flags": {}} for agent in self.agents}
        return observations, infos

    def step(
        self, actions: dict[str, np.ndarray]
    ) -> tuple[
        dict[str, Any],
        dict[str, float],
        dict[str, bool],
        dict[str, bool],
        dict[str, dict[str, Any]],
    ]:
        self.step_count += 1
        active_agents = [a for a in self.agents if self.drones[a].alive]

        if not active_agents:
            self.agents.clear()
            return {}, {}, {}, {}, {}

        # 1. Kinematics update
        action_mat = np.zeros((self.swarm_size, 4), dtype=np.float32)
        for i, agent in enumerate(self.possible_agents):
            if agent in actions and self.drones[agent].alive:
                action_mat[i] = np.clip(actions[agent], -1.0, 1.0)

        # Scale actions
        vx_cmd = action_mat[:, 0] * MAX_HORIZ_VEL
        vy_cmd = action_mat[:, 1] * MAX_VERT_VEL
        vz_cmd = action_mat[:, 2] * MAX_HORIZ_VEL
        yaw_rate_cmd = action_mat[:, 3] * MAX_YAW_RATE

        # Update headings (heading 0 rad points along +X, +Y up, +Z orthogonal)
        self.headings = (self.headings + yaw_rate_cmd * self.dt) % (2.0 * np.pi)

        # Wind calculation
        if self.wind_strength > 0:
            gust = self.wind_rng.normal(0, 0.2 * self.wind_strength, size=(self.swarm_size, 3)).astype(np.float32)
            gust[:, 1] = 0.0
            wind_vec = self.base_wind + gust
        else:
            wind_vec = np.zeros((self.swarm_size, 3), dtype=np.float32)

        self.velocities[:, 0] = vx_cmd + wind_vec[:, 0]
        self.velocities[:, 1] = vy_cmd
        self.velocities[:, 2] = vz_cmd + wind_vec[:, 2]

        new_positions = self.positions + self.velocities * self.dt

        # Boundary checks & clipping
        below_min = new_positions < [WORLD_X_MIN, WORLD_Y_MIN, WORLD_Z_MIN]
        above_max = new_positions > [WORLD_X_MAX, WORLD_Y_MAX, WORLD_Z_MAX]
        boundary_violations = np.any(below_min | above_max, axis=1)

        self.positions = np.clip(
            new_positions,
            [WORLD_X_MIN, WORLD_Y_MIN, WORLD_Z_MIN],
            [WORLD_X_MAX, WORLD_Y_MAX, WORLD_Z_MAX],
        )
        self.velocities[boundary_violations] *= 0.1

        # 2. Vectorized pairwise drone collisions & min neighbor distance
        diff = self.positions[:, None, :] - self.positions[None, :, :]
        dists = np.linalg.norm(diff, axis=2)
        np.fill_diagonal(dists, np.inf)

        # Mask dead drones out of distance checks
        alive_mask = self.alive > 0.5
        dists_masked = np.where(alive_mask[None, :] & alive_mask[:, None], dists, np.inf)

        drone_collisions = np.any(dists_masked < self.event_config.drone_collision_distance, axis=1) & alive_mask
        min_neighbor_dists = np.min(dists_masked, axis=1)
        min_neighbor_dists = np.where(np.isneginf(min_neighbor_dists) | np.isposinf(min_neighbor_dists), 30.0, min_neighbor_dists)

        # 3. Vectorized obstacle collisions
        if self.obstacles:
            obs_pos = np.array([obs.position for obs in self.obstacles], dtype=np.float32)
            obs_radii = np.array([obs.radius for obs in self.obstacles], dtype=np.float32)
            obs_heights = np.array([obs.height for obs in self.obstacles], dtype=np.float32)
            obstacle_collisions = detect_obstacle_collisions_vectorized(
                self.positions, obs_pos, obs_radii, obs_heights, self.event_config.obstacle_collision_distance
            ) & alive_mask
        else:
            obstacle_collisions = np.zeros(self.swarm_size, dtype=bool)

        # 4. Target detection & updates (checking horizontal proximity within 3.0 m)
        if self.targets:
            target_pos = np.array([t.position for t in self.targets], dtype=np.float32)
            active_targets = np.array([not t.found for t in self.targets], dtype=bool)
            # 2D horizontal distance for target discovery
            target_diff_xz = self.positions[:, None, [0, 2]] - target_pos[None, :, [0, 2]]
            target_dists_xz = np.linalg.norm(target_diff_xz, axis=2)  # (N, M)
            valid_targets = (target_dists_xz < self.event_config.target_detection_distance) & active_targets[None, :] & alive_mask[:, None]

            drone_target_found = np.any(valid_targets, axis=1)
            newly_found_targets = np.any(valid_targets, axis=0)
            for idx, newly_found in enumerate(newly_found_targets):
                if newly_found:
                    self.targets[idx].found = True
                    self.targets_found_count += 1
            team_target_found = bool(np.any(newly_found_targets))
        else:
            drone_target_found = np.zeros(self.swarm_size, dtype=bool)
            team_target_found = False

        # 5. Symmetric exploration map update
        agent_pos_dict = {f"drone_{i}": self.positions[i] for i in range(self.swarm_size) if alive_mask[i]}
        new_cells_per_agent, team_new_cells = self.exploration_map.mark_explored_per_agent(agent_pos_dict)

        # Update collision totals
        num_drone_cols = int(np.sum(drone_collisions))
        num_obs_cols = int(np.sum(obstacle_collisions))
        num_b_cols = int(np.sum(boundary_violations & alive_mask))
        self.collision_totals["drone"] += num_drone_cols
        self.collision_totals["obstacle"] += num_obs_cols
        self.collision_totals["boundary"] += num_b_cols
        self.collision_totals["total"] += (num_drone_cols + num_obs_cols + num_b_cols)

        # 6. Calculate rewards
        rewards: dict[str, float] = {}
        infos: dict[str, dict[str, Any]] = {}
        for i, agent in enumerate(self.possible_agents):
            if agent in active_agents:
                tot_rew, details = calculate_reward(
                    agent_id=agent,
                    new_cells=int(new_cells_per_agent.get(agent, 0)),
                    previously_explored=bool(new_cells_per_agent.get(agent, 0) == 0),
                    target_found=bool(drone_target_found[i]),
                    drone_collision=bool(drone_collisions[i]),
                    obstacle_collision=bool(obstacle_collisions[i]),
                    boundary_violation=bool(boundary_violations[i]),
                    config=self.reward_config,
                    team_cells=int(team_new_cells),
                    team_target_found=team_target_found,
                    min_neighbor_dist=float(min_neighbor_dists[i]),
                )
                rewards[agent] = float(tot_rew)
                details["team_target_found_flag"] = team_target_found
                details["min_neighbor_dist"] = float(min_neighbor_dists[i])
                details["team_cells"] = int(team_new_cells)
                event_flags = {
                    "drone_collision": bool(drone_collisions[i]),
                    "obstacle_collision": bool(obstacle_collisions[i]),
                    "target_found": bool(drone_target_found[i]),
                    "boundary_violation": bool(boundary_violations[i]),
                    "team_target_found": team_target_found,
                }
                infos[agent] = {
                    "reward_breakdown": details,
                    "event_flags": event_flags,
                }

        # 7. Check terminations and truncations
        all_targets_found = bool(len(self.targets) > 0 and all(t.found for t in self.targets))
        truncated = bool(self.step_count >= self.max_steps)

        terminations = {}
        for agent in active_agents:
            idx = self.agent_to_idx[agent]
            term = all_targets_found
            if self.terminate_on_boundary and boundary_violations[idx]:
                self.alive[idx] = 0.0
                term = True
            terminations[agent] = term

        truncations = {agent: truncated for agent in active_agents}

        observations = self._build_all_observations()

        if all_targets_found or truncated:
            self.agents.clear()
        else:
            self.agents = [a for a in self.agents if not (terminations[a] or truncations[a])]

        return observations, rewards, terminations, truncations, infos

    def state(self) -> np.ndarray:
        """Centralized critic state: (471,) float32."""
        state_vec = np.zeros(471, dtype=np.float32)

        # 50 drones * 9 = 450
        norm_pos = np.zeros_like(self.positions)
        norm_pos[:, 0] = self.positions[:, 0] / WORLD_X_MAX
        norm_pos[:, 1] = self.positions[:, 1] / WORLD_Y_MAX
        norm_pos[:, 2] = self.positions[:, 2] / WORLD_Z_MAX

        norm_vel = np.zeros_like(self.velocities)
        norm_vel[:, 0] = self.velocities[:, 0] / MAX_HORIZ_VEL
        norm_vel[:, 1] = self.velocities[:, 1] / MAX_VERT_VEL
        norm_vel[:, 2] = self.velocities[:, 2] / MAX_HORIZ_VEL

        sin_h = np.sin(self.headings)
        cos_h = np.cos(self.headings)

        for i in range(self.swarm_size):
            base = i * 9
            state_vec[base : base + 3] = norm_pos[i]
            state_vec[base + 3 : base + 6] = norm_vel[i]
            state_vec[base + 6] = sin_h[i]
            state_vec[base + 7] = cos_h[i]
            state_vec[base + 8] = self.alive[i]

        # 5 target slots * 4 = 20
        base_targets = self.swarm_size * 9  # 450
        for slot in range(5):
            t_base = base_targets + slot * 4
            if slot < len(self.targets):
                t = self.targets[slot]
                state_vec[t_base] = t.position[0] / WORLD_X_MAX
                state_vec[t_base + 1] = t.position[1] / WORLD_Y_MAX
                state_vec[t_base + 2] = t.position[2] / WORLD_Z_MAX
                state_vec[t_base + 3] = 0.0 if t.found else 1.0
            else:
                state_vec[t_base : t_base + 4] = 0.0

        # Global explored fraction = 1
        state_vec[470] = float(self.exploration_map.explored_fraction)

        return state_vec

    def _get_observation(self, agent_id: str) -> np.ndarray:
        all_obs = self._build_all_observations()
        if agent_id in all_obs:
            raw = all_obs[agent_id]
            if isinstance(raw, dict):
                return raw["obs"]
            return raw
        # Default zero observation
        return np.zeros(81, dtype=np.float32)

    def _build_all_observations(self) -> dict[str, Any]:
        # 1. Self states: (N, 9)
        norm_pos = np.zeros((self.swarm_size, 3), dtype=np.float32)
        norm_pos[:, 0] = self.positions[:, 0] / WORLD_X_MAX
        norm_pos[:, 1] = self.positions[:, 1] / WORLD_Y_MAX
        norm_pos[:, 2] = self.positions[:, 2] / WORLD_Z_MAX

        norm_vel = np.zeros((self.swarm_size, 3), dtype=np.float32)
        norm_vel[:, 0] = self.velocities[:, 0] / MAX_HORIZ_VEL
        norm_vel[:, 1] = self.velocities[:, 1] / MAX_VERT_VEL
        norm_vel[:, 2] = self.velocities[:, 2] / MAX_HORIZ_VEL

        sin_h = np.sin(self.headings)[:, None]
        cos_h = np.cos(self.headings)[:, None]
        status = self.alive[:, None]
        self_features = np.hstack([norm_pos, norm_vel, sin_h, cos_h, status])  # (N, 9)

        # 2. 10 nearest neighbours: (N, 30)
        diff = self.positions[None, :, :] - self.positions[:, None, :]  # (N, N, 3)
        dists = np.linalg.norm(diff, axis=2)
        np.fill_diagonal(dists, np.inf)

        k_neighbors = min(10, self.swarm_size - 1)
        knn_features = np.zeros((self.swarm_size, 30), dtype=np.float32)
        if k_neighbors > 0:
            part_idx = np.argpartition(dists, kth=k_neighbors - 1, axis=1)[:, :k_neighbors]
            part_dists = np.take_along_axis(dists, part_idx, axis=1)
            order = np.argsort(part_dists, axis=1)
            sorted_idx = np.take_along_axis(part_idx, order, axis=1)

            chosen_diff = np.take_along_axis(diff, sorted_idx[:, :, None], axis=1)  # (N, k, 3)
            norm_factor = np.array([WORLD_X_SPAN, WORLD_Y_SPAN, WORLD_Z_SPAN], dtype=np.float32)
            norm_diff = chosen_diff / norm_factor
            knn_features[:, : k_neighbors * 3] = norm_diff.reshape(self.swarm_size, k_neighbors * 3)

        # 3. Cone sensor detections: (N, 32)
        candidate_positions = []
        candidate_types = []

        for t in self.targets:
            if not t.found:
                candidate_positions.append(t.position)
                candidate_types.append(1.0)
        for obs in self.obstacles:
            candidate_positions.append(obs.position)
            candidate_types.append(2.0)
        for i in range(self.swarm_size):
            if self.alive[i] > 0.5:
                candidate_positions.append(self.positions[i])
                candidate_types.append(3.0)

        if candidate_positions:
            c_pos = np.array(candidate_positions, dtype=np.float32)
            c_type = np.array(candidate_types, dtype=np.float32)
            cone_features = self.cone_sensor.detect_batch(
                self.positions, self.headings, c_pos, c_type
            )
        else:
            cone_features = np.zeros((self.swarm_size, 32), dtype=np.float32)

        # 4. Exploration patch & global fraction: (N, 10)
        explored_fraction = float(self.exploration_map.explored_fraction)
        expl_features = np.zeros((self.swarm_size, 10), dtype=np.float32)
        for i in range(self.swarm_size):
            patch = self.exploration_map.get_local_patch(self.positions[i], radius_cells=1).flatten()
            expl_features[i, :9] = patch
            expl_features[i, 9] = explored_fraction

        # Concatenate 9 + 30 + 32 + 10 = 81
        all_obs = np.hstack([self_features, knn_features, cone_features, expl_features])

        result = {}
        global_state = self.state() if self.include_global_state else None
        for i, agent in enumerate(self.possible_agents):
            if agent in self.agents:
                local_obs = all_obs[i]
                if self.include_global_state:
                    result[agent] = {"obs": local_obs, "state": global_state}
                else:
                    result[agent] = local_obs

        return result
