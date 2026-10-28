# SwarmRL Environment Specification

## Overview
SwarmRL is a multi-agent reinforcement learning environment simulating a swarm of 50 homogeneous drones performing collaborative Search-and-Rescue (SAR) in a bounded 3D airspace. It implements the PettingZoo `ParallelEnv` interface and supports Centralized Training with Decentralized Execution (CTDE) for MAPPO.

## World Constants
- **Horizontal Bounds (X and Z):** `[-50.0, 50.0]` meters (width = 100 m, depth = 100 m).
- **Altitude Bounds (Y):** `[0.0, 20.0]` meters (height = 20 m).
- **Coordinate System:** Right-handed coordinate system where:
  - Heading `0.0` rad points along `+X` in the X-Z plane.
  - `+Y` is pointing vertically up.
  - `+Z` is orthogonal to `+X` in the horizontal ground plane (heading `pi/2` points along `+Z`).
- **Kinematics:** Fixed simulation time step `dt = 0.1` s. Point-mass kinematics with velocity scaling.
- **Velocity Limits:**
  - Horizontal velocity: `[-10.0, 10.0]` m/s (`vx`, `vz`).
  - Vertical velocity: `[-3.0, 3.0]` m/s (`vy`).
  - Yaw rate: `[-pi, pi]` rad/s.
- **Boundary Violation Handling:** Drone position is clipped to world boundaries; velocity is damped by 90% (multiplied by 0.1); `boundary_violation` event flag is raised.

## Agents
- **Count:** 50 agents named `drone_0` through `drone_49`.
- **Liveness:** All agents stay active for the entirety of each episode. Collisions are penalized through rewards, but agents are not removed.
- **Episode Termination & Truncation:**
  - Truncated when `step >= max_steps` (default `500` steps = 50 seconds real-time).
  - Terminated when all targets in the scenario have been discovered.
  - No `"__all__"` key in `terminations` or `truncations` dicts (per PettingZoo ParallelEnv spec).

## Action Space
Continuous action space for each agent: `gym.spaces.Box(low=-1.0, high=1.0, shape=(4,), dtype=np.float32)`.
Out-of-range action values are clipped to `[-1.0, 1.0]`.
Actions map to physical velocity commands:
- `action[0]`: `vx = action[0] * 10.0` m/s
- `action[1]`: `vy = action[1] * 3.0` m/s
- `action[2]`: `vz = action[2] * 10.0` m/s
- `action[3]`: `yaw_rate = action[3] * pi` rad/s

## Observation Space
Decentralized observation per agent: `gym.spaces.Box(low=-np.inf, high=np.inf, shape=(81,), dtype=np.float32)`.
Consisting of 4 concatenated sub-vectors:
1. **Self State (9 dimensions):**
   - Normalized position `(x / 50.0, (y - 10.0) / 10.0, z / 50.0)` (3)
   - Normalized velocity `(vx / 10.0, vy / 3.0, vz / 10.0)` (3)
   - Heading representation `(sin(heading), cos(heading))` (2)
   - Liveness status `1.0` (1)
2. **K-Nearest Neighbors (30 dimensions):**
   - 10 nearest neighboring drones.
   - For each neighbor: relative displacement `(dx / 100.0, dy / 20.0, dz / 100.0)` normalized by world spans (3).
   - Zero-padded if fewer than 10 neighbors exist.
3. **Cone Sensor Detections (32 dimensions):**
   - Up to 8 detected objects ordered by increasing Euclidean distance.
   - For each detection: `(norm_distance, bearing_x, bearing_y, type_code)` (4).
     - `norm_distance = distance / 15.0`
     - `bearing_x = rel_x / distance`
     - `bearing_y = rel_z / distance`
     - `type_code`: `1.0` = target, `2.0` = obstacle, `3.0` = drone, `0.0` = padded
4. **Exploration Patch (10 dimensions):**
   - 3x3 binary occupancy patch of cells around the drone's current cell in the 50x50 exploration grid (9).
   - Global explored fraction of the arena `[0.0, 1.0]` (1).

Total: `9 + 30 + 32 + 10 = 81` dimensions.

## Centralized Critic State Space
Global state for MAPPO critic: `gym.spaces.Box(low=-np.inf, high=np.inf, shape=(471,), dtype=np.float32)`.
Fixed size before reset, after reset, and throughout the episode:
- 50 agents * 9 features (normalized position 3, velocity 3, sin/cos heading 2, status 1) = 450
- 5 fixed target slots * 4 features (norm_x, norm_y, norm_z, active_flag) = 20
- Global explored fraction = 1
Total: `450 + 20 + 1 = 471` dimensions.

## Exploration Grid
- Grid resolution: 50x50 cells covering the 100x100 m ground plane (2.0 m per cell).
- `ExplorationMap.mark_explored_per_agent` is evaluated once per environment step with all agent positions simultaneously. Credit assignment is strictly symmetric, preventing order starvation.

## Sensors & Events
- **Cone Sensor:** Range `15.0` m, half-angle `30` degrees (`pi/6` rad). Detects targets, obstacles, and peer drones.
- **Collision Thresholds:**
  - Drone-to-drone collision: center-to-center distance `< 2.0` m.
  - Obstacle collision: distance to obstacle boundary `< 1.0` m (`distance < radius + 1.0`).
  - Target detection / found: distance `< 3.0` m.
  - Boundary violation: outside world bounding box.
- All pairwise distances computed via vectorized NumPy broadcasting matrix operations without nested Python loops.

## Wind Model
- Horizontal base vector + per-step random gust scaled by `wind_strength`.
- Seeded random number generator.
- When `wind_strength == 0.0`, wind vector is identically zero and trajectories are fully deterministic and repeatable across seeds.

## Difficulty Levels (0-4)
Configured via `sensors/scenario.py`:
- **Level 0:** 0 obstacles, `wind_strength = 0.0`, 3 targets.
- **Level 1:** 5 obstacles, `wind_strength = 0.0`, 3 targets.
- **Level 2:** 10 obstacles, `wind_strength = 0.5`, 4 targets.
- **Level 3:** 15 obstacles, `wind_strength = 1.0`, 4 targets.
- **Level 4:** 20 obstacles, `wind_strength = 1.5`, 5 targets.
Obstacles are placed strictly outside the drone spawn clearance zone (minimum 4 m from any drone spawn point).

## Reward Structure
Returns `(total_reward: float, breakdown: dict[str, float])` via `calculate_reward`:
- `new_area`: `1.0` per newly discovered cell
- `team_new_area`: `0.05` per newly discovered cell by any teammate
- `target_found`: `10.0` for finding a target
- `team_target_found`: `0.2` when any teammate finds a target
- `drone_collision`: `-5.0`
- `obstacle_collision`: `-5.0`
- `boundary_violation`: `-5.0`
- `repeated_area`: `0.0`
- `proximity_penalty`: `-0.5` per meter inside 3.0 m neighbor distance
- `step_cost`: `-0.01` per step
