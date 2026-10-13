# SwarmRL Environment Specification (`env.py`)

This is the reference for `SwarmRLParallelEnv`. If this document and `env.py` disagree, one of them is a bug — fix it rather than working around it. The numbers below are the locked spec as of 2026-10-02.

`SwarmRLParallelEnv` is the team's single training environment. It is a PettingZoo `ParallelEnv`, and `rllib_config.py` wraps it with RLlib's `ParallelPettingZooEnv`. See [Retired environments](#9-retired-environments) for the env on the `Venkatesh` branch.

---

## 1. Constructor

```python
SwarmRLParallelEnv(
    num_agents=50,               # DEFAULT_NUM_AGENTS
    max_steps=1000,              # truncation horizon
    dt=0.05,                     # 20 Hz
    reward_config=None,          # sensors.rewards.RewardConfig()
    sensor_config=None,          # SensorConfig(range=20.0, field_of_view=pi/2)
    include_global_state=False,  # wrap obs as Dict(obs, state) for a centralized critic
    terminate_on_boundary=False,
)
```

The world is **fixed-size**. There is no `world_size` argument; bounds, grid resolution and normalization divisors all come from the module constants in section 2. Passing `world_size=` raises `TypeError`.

`num_agents` is configurable (tests use 3–50), but training and every spec number below assume the default of 50.

---

## 2. World

All values are module constants in `env.py`.

| Constant | Value | Meaning |
| :--- | :---: | :--- |
| `WORLD_X_MIN`, `WORLD_X_MAX` | −50.0, 50.0 m | East–west extent |
| `WORLD_Y_MIN`, `WORLD_Y_MAX` | 0.0, 20.0 m | Altitude band |
| `WORLD_Z_MIN`, `WORLD_Z_MAX` | −50.0, 50.0 m | North–south extent |
| `EXPLORATION_CELL_SIZE` | 2.0 m | Exploration grid cell edge |
| `MAX_HORIZ_VEL` | 10.0 m/s | Scale for `vx`, `vz` |
| `MAX_VERT_VEL` | 3.0 m/s | Scale for `vy` |
| `MAX_YAW_RATE` | π rad/s | Scale for yaw rate |
| `COMM_RADIUS` | 30.0 m | Neighbor observation range |

* World is 100 × 100 m on the ground plane, centered on the origin, with a 0–20 m altitude band.
* Coordinates are right-handed, Y-up: X and Z are horizontal, Y is altitude.
* Heading ψ ∈ [0, 2π), with 0 = +X, increasing counter-clockwise in the X-Z plane.
* Exploration grid: 50 × 50 cells at 2 m each (`ExplorationMap`, centered on the origin, exploration radius 2.0 m).

### Spawn layout (`reset`)
* Drones: 10-column grid at 5 m spacing centered on the origin, altitude 5.0 m, ±0.5 m jitter in X/Z, random heading.
* Targets: 5, uniform in X, Z ∈ [−40, 40], at y = 0.5, radius 1.5 m.
* Obstacles: 8 spheres of radius 2.0 m, X, Z ∈ [−35, 35], y ∈ [2, 8], rejection-sampled to keep ≥ 5.5 m from drones and targets (best effort, 50 tries).

---

## 3. Action space

`Box(low=-1.0, high=1.0, shape=(4,), dtype=float32)` per agent. Actions are clipped to [−1, 1] then scaled:

| Index | Command | Physical range |
| :---: | :--- | :---: |
| 0 | `vx` — X velocity | ±10.0 m/s |
| 1 | `vy` — vertical velocity | ±3.0 m/s |
| 2 | `vz` — Z velocity | ±10.0 m/s |
| 3 | yaw rate | ±π rad/s |

Velocities are world-frame and set directly each step (no acceleration model). There is **no pitch control**; pitch and roll are derived from motion on the frontend for rendering only.

Integration per step:

$$\psi_{t+1} = (\psi_t + \dot\psi\,\Delta t) \bmod 2\pi \qquad \mathbf{p}_{t+1} = \mathbf{p}_t + \mathbf{v}_{t+1}\,\Delta t$$

---

## 4. Observation space: (81,) float32

`Box(-inf, inf, (81,), float32)`.

```
[ 0 :  8]  ego kinematics           8
[ 8 : 32]  6 nearest neighbors      6 × 4
[32 : 56]  cone sensor detections   8 × 3
[56 : 81]  local exploration patch  5 × 5
```

### 4.1 Ego kinematics (0–7)
| Index | Feature | Normalization |
| :---: | :--- | :--- |
| 0 | x | `x / WORLD_X_MAX` |
| 1 | y | `y / WORLD_Y_MAX` |
| 2 | z | `z / WORLD_Z_MAX` |
| 3 | vx | `vx / MAX_HORIZ_VEL` |
| 4 | vy | `vy / MAX_VERT_VEL` |
| 5 | vz | `vz / MAX_HORIZ_VEL` |
| 6 | cos ψ | — |
| 7 | sin ψ | — |

### 4.2 Nearest neighbors (8–31)
The 6 nearest alive drones by 3D distance. For slot k, base index = 8 + 4k:

| Offset | Feature | Value |
| :---: | :--- | :--- |
| +0..+2 | relative dx, dy, dz | `(p_nbr − p_ego) / COMM_RADIUS` |
| +3 | distance | `‖p_nbr − p_ego‖ / COMM_RADIUS` |

Neighbors beyond `COMM_RADIUS`, and empty slots, read `[0, 0, 0, 1]`.

### 4.3 Cone sensor (32–55)
`ConeSensor` with 20 m range and 90° field of view. Up to 8 objects (unfound targets, obstacles, other alive drones), nearest first. For slot j, base index = 32 + 3j:

| Offset | Feature | Value |
| :---: | :--- | :--- |
| +0 | type | 1 = target, 2 = obstacle, 3 = drone, 0 = empty |
| +1 | distance | 3D distance / 20, in [0, 1] |
| +2 | angle | **unsigned** horizontal angle off heading / π, in [0, 0.25] within the cone |

The FoV test uses the horizontal (X-Z) angle only, so altitude does not narrow the cone. The angle is `arccos`-based and does not encode left vs. right.

### 4.4 Local exploration patch (56–80)
5 × 5 cells of the exploration grid centered on the agent's cell, flattened row-major. 1.0 = explored, 0.0 = unexplored or outside the grid.

---

## 5. Centralized critic state

`env.state()` returns float32 of length `num_agents × 9 + 5 × 4 + 1` (471 for 50 agents):

* per drone, in `possible_agents` order: `[x, y, z, vx, vy, vz]` normalized as in 4.1, then `cos ψ, sin ψ, alive`. Dead drones are all zeros.
* per target: `[x / WORLD_X_MAX, y / WORLD_Y_MAX, z / WORLD_Z_MAX, found]`.
* swarm explored fraction.

With `include_global_state=True`, each agent's observation becomes `Dict({"obs": Box(81,), "state": Box(471,)})`.

> Known gap: the centralized-critic model in `rllib_config.py` is a legacy `ModelV2` custom model. RLlib's new API stack (the default in Ray 2.58) ignores it, so `build_training_config(include_global_state=True)` fails to build. `train.py` trains with `include_global_state=False` until the critic is ported to an `RLModule`.

---

## 6. Events and collision handling

Checked each step after integration, in this order:

* **Drone–drone collision:** any pair closer than **2.0 m**. Both drones are flagged and die.
* **Boundary violation:** any coordinate outside the world bounds. The drone is flagged `boundary_violation`, its position is clipped back into bounds, and its velocity is multiplied by 0.1. It only dies if `terminate_on_boundary=True`.
* **Obstacle collision:** `‖p − p_obs‖ < r_obs + 1.0`. The drone is flagged and dies.
* **Target discovery:** horizontal distance to an unfound target ≤ 3.0 m with altitude inside the band. Every drone in range gets credit; the target is marked found.

Exploration cells are marked from post-integration positions before the boundary clip.

---

## 7. Rewards and infos

Rewards come from `sensors.rewards.calculate_reward`, with default weights from `RewardConfig`:

| Component | Weight |
| :--- | :---: |
| new cells explored (per agent) | +1.0 per cell |
| new cells explored by the whole swarm this step | +0.05 per cell |
| target found (individual) | +10.0 |
| target found by anyone this step | +0.2 |
| drone collision | −5.0 |
| obstacle collision | −5.0 |
| boundary violation | −5.0 |
| proximity, when nearest neighbor < 3.0 m | −0.5 × (3.0 − d) |
| step cost | −0.01 |

`rewards[agent]` is a plain `float`. Per-agent `infos[agent]` contains:

* `reward_breakdown`: each weighted component, plus `total`, `team_cells`, `min_neighbor_dist` and `team_target_found_flag`.
* `event_flags`: `drone_collision`, `obstacle_collision`, `target_found`, `boundary_violation`, `team_cells`, `team_target_found` and `min_neighbor_dist`.

---

## 8. Episode lifecycle

`step()` returns `(observations, rewards, terminations, truncations, infos)`. Each dict is keyed **only** by the agents that were active at the start of the step. The env does not emit `__all__`; RLlib's `ParallelPettingZooEnv` adds it.

* An agent **terminates** when it dies (section 6) or when all 5 targets are found.
* All agents **truncate** at `max_steps`.
* Terminated or truncated agents are removed from `env.agents`. The episode is over when `env.agents` is empty. Raw-env loops should check that, not `__all__`.

---

## 9. Retired environments

`environment/drone_env.py` (`SwarmSearchRescueEnv`) on the `Venkatesh` branch was **retired on 2026-10-02** and must not be merged. It is a separate design — `Discrete(5)` actions, a 20 × 20 grid, [0, 1] observations — that does not match this spec. Merging that branch also repoints `rllib_config.py` at it, silently replacing this env for training.

Its PPO hyperparameters, env-runner settings and the `train.py` checkpointing driver were ported to `main`. Its 50 separate policies were deliberately not ported: `main` uses one shared policy, which is the intended parameter-sharing setup for 50 identical drones.
