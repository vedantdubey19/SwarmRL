# SwarmRL PettingZoo Environment Specification (`env.py`)

## 1. High-Level Architecture & Contracts

`SwarmRLParallelEnv` is an executable multi-agent drone simulation compliant with the PettingZoo `ParallelEnv` interface. It provides simultaneous stepping across 50 autonomous search-and-rescue quadcopters operating in a bounded 3D continuous arena, supporting Centralized Training with Decentralized Execution (CTDE) for MAPPO in Ray RLlib and native PyTorch.

* **Agent Count:** Locked at exactly 50 agents (`drone_0` through `drone_49`).
* **Simulation Step Time ($\Delta t$):** $0.05\text{ s}$ ($20\text{ Hz}$).
* **Coordinate Convention:** Right-handed Cartesian:
  * $X \in [-50.0, 50.0]\text{ m}$ (East-West horizontal axis)
  * $Y \in [0.0, 20.0]\text{ m}$ (Vertical altitude / height axis)
  * $Z \in [-50.0, 50.0]\text{ m}$ (North-South horizontal axis)
  * Heading $\psi \in [0, 2\pi)\text{ rad}$ ($0\text{ rad} = +X$, counter-clockwise in X-Z plane)

---

## 2. Action Space Specification

Each agent receives a continuous 4-DoF action vector defined via `gymnasium.spaces.Box(low=-1.0, high=1.0, shape=(4,), dtype=np.float32)`.

Actions represent normalized control commands and are clipped to $[-1.0, 1.0]$:

| Index | Symbol | Dimension | Physical Meaning | Normalization Range | Physical Scaling |
| :---: | :---: | :---: | :--- | :---: | :---: |
| `0` | $a_{vx}$ | Velocity | Longitudinal velocity command ($v_x$) | $[-1.0, 1.0]$ | $[-10.0, 10.0]\text{ m/s}$ |
| `1` | $a_{vy}$ | Velocity | Vertical heave velocity command ($v_y$) | $[-1.0, 1.0]$ | $[-3.0, 3.0]\text{ m/s}$ |
| `2` | $a_{vz}$ | Velocity | Lateral velocity command ($v_z$) | $[-1.0, 1.0]$ | $[-10.0, 10.0]\text{ m/s}$ |
| `3` | $a_{\dot{\psi}}$ | Yaw Rate | Heading angular velocity command ($\dot{\psi}$) | $[-1.0, 1.0]$ | $[-\pi, \pi]\text{ rad/s}$ |

### Kinematic Integration
Point-mass 4-DoF kinematics are integrated every step ($\Delta t = 0.05\text{ s}$):
$$\psi_{t+1} = (\psi_t + \dot{\psi} \cdot \Delta t) \pmod{2\pi}$$
$$\mathbf{p}_{t+1} = \mathbf{p}_t + \mathbf{v}_{t+1} \cdot \Delta t$$
where $\mathbf{v}_{t+1} = [v_x, v_y, v_z]^T$. Pitch and roll angles are physically coupled to linear acceleration and computed procedurally downstream for visual rendering.

---

## 3. Observation Space Specification: (81,) Float32

Every agent receives an 81-dimensional observation vector `Box(low=-np.inf, high=np.inf, shape=(81,), dtype=np.float32)`.

```
Index Slices:
[ 0 :  8]  Ego Kinematics (8 floats)
[ 8 : 32]  K-Nearest Neighbors (24 floats = 6 neighbors * 4 features)
[32 : 56]  ConeSensor Detections (24 floats = 8 objects * 3 features)
[56 : 81]  Local Exploration Patch (25 floats = 5x5 grid cells)
```

### Detailed Index Mapping

#### 1. Self State (Indices 0–7)
| Index | Feature | Range | Normalization | Description |
| :---: | :--- | :---: | :---: | :--- |
| `0` | `pos_x` | $[-1.0, 1.0]$ | $p_x / 50.0$ | Normalized arena X position |
| `1` | `pos_y` | $[0.0, 1.0]$ | $p_y / 20.0$ | Normalized altitude |
| `2` | `pos_z` | $[-1.0, 1.0]$ | $p_z / 50.0$ | Normalized arena Z position |
| `3` | `vel_x` | $[-1.0, 1.0]$ | $v_x / 10.0$ | Normalized X velocity |
| `4` | `vel_y` | $[-1.0, 1.0]$ | $v_y / 3.0$ | Normalized Y vertical climb rate |
| `5` | `vel_z` | $[-1.0, 1.0]$ | $v_z / 10.0$ | Normalized Z velocity |
| `6` | `heading_cos` | $[-1.0, 1.0]$ | $\cos(\psi)$ | Unit heading vector X component |
| `7` | `heading_sin` | $[-1.0, 1.0]$ | $\sin(\psi)$ | Unit heading vector Z component |

#### 2. K-Nearest Neighbors (Indices 8–31)
Top-6 closest active drone neighbors sorted by Euclidean distance. Communication radius is $30.0\text{ m}$. If out of communication range or fewer than 6 drones are alive, masked default is `[0.0, 0.0, 0.0, 1.0]`. Pairwise distance computation is vectorized via `scipy.spatial.distance.cdist`.

For neighbor slot $k \in [0, 5]$, base index $= 8 + 4k$:
| Offset | Feature | Range | Description |
| :---: | :--- | :---: | :--- |
| `+0` | `rel_dx` | $[-1.0, 1.0]$ | $(p_{x, nbr} - p_{x, ego}) / 30.0$ (0.0 if masked) |
| `+1` | `rel_dy` | $[-1.0, 1.0]$ | $(p_{y, nbr} - p_{y, ego}) / 30.0$ (0.0 if masked) |
| `+2` | `rel_dz` | $[-1.0, 1.0]$ | $(p_{z, nbr} - p_{z, ego}) / 30.0$ (0.0 if masked) |
| `+3` | `norm_dist`| $[0.0, 1.0]$ | $\|\mathbf{p}_{nbr} - \mathbf{p}_{ego}\| / 30.0$ (1.0 if masked / out of range) |

#### 3. Sensor Cone Detections (Indices 32–55)
Outputs of forward 90° FoV, 20m range `ConeSensor`. Up to 8 detected objects sorted by increasing distance. Empty slots padded with `[0.0, 0.0, 0.0]`.

For detection slot $j \in [0, 7]$, base index $= 32 + 3j$:
| Offset | Feature | Range | Description |
| :---: | :--- | :---: | :--- |
| `+0` | `type_id` | $\{0.0, 1.0, 2.0, 3.0\}$ | `0.0`: Empty/Padding, `1.0`: Rescue Target, `2.0`: Static Obstacle, `3.0`: Peer Drone |
| `+1` | `norm_dist` | $[0.0, 1.0]$ | Euclidean distance $/ 20.0$ |
| `+2` | `norm_angle`| $[-1.0, 1.0]$ | Horizontal bearing angle $\theta / \pi$ relative to heading |

#### 4. Local Exploration Patch (Indices 56–80)
A $5 \times 5$ grid patch centered on the agent's current position (cell size $2.0\text{ m}$, 25 cells total in row-major order) extracted from `ExplorationMap.grid`:
* `1.0`: Cell has been visited/explored by the swarm
* `0.0`: Cell is unexplored

---

## 4. Centralized Critic Global State: (471,) Float32

For MAPPO Centralized Training with Decentralized Execution (`include_global_state=True`), each agent observation is wrapped in a `Dict({"obs": Box(81,), "state": Box(471,)})`.

The 471-dimensional global state vector $\mathbf{S} \in \mathbb{R}^{471}$ contains:
* **Drones (50 agents $\times$ 9 features = 450 floats):**
  For each possible agent `drone_0` to `drone_49`:
  `[x/50, y/20, z/50, vx/10, vy/3, vz/10, cos(yaw), sin(yaw), alive_flag]`
  (Dead or missing agents are zero-filled with `alive_flag = 0.0`).
* **Rescue Targets (5 targets $\times$ 4 features = 20 floats):**
  For each target: `[x/50, y/20, z/50, found_flag]` (`1.0` if found, `0.0` otherwise).
* **Swarm Coverage Fraction (1 float):**
  `ExplorationMap.explored_fraction` $\in [0.0, 1.0]$.

---

## 5. Physical World Bounds & Collision Responses

* **World Boundary Limits:**
  * $X \in [-50.0, 50.0]\text{ m}$
  * $Y \in [0.0, 20.0]\text{ m}$
  * $Z \in [-50.0, 50.0]\text{ m}$
* **Boundary Violation Response:**
  * Flagged in event dictionary (`boundary_violation: True`) for `calculate_reward` to apply boundary penalty ($-5.0$).
  * Position is corrected and clamped to the world bounds: $p_x = \text{clip}(p_x, -50, 50)$, etc.
  * Velocity is dampened ($v \leftarrow 0.1 \times v$).
  * Agents do not die on boundary collision unless `terminate_on_boundary=True`.
* **Drone-to-Drone Collisions:**
  * Distance threshold $< 2.0\text{ m}$.
  * Both drones flag `drone_collision: True`, receive collision penalty ($-5.0$), and terminate (`alive = False`).
* **Obstacle Collisions:**
  * Distance to obstacle surface $< 1.0\text{ m}$ ($\|\mathbf{p} - \mathbf{p}_{obs}\| < r_{obs} + 1.0$).
  * Flags `obstacle_collision: True`, penalty ($-5.0$), and terminates (`alive = False`).
* **Aerial Target Discovery:**
  * Ground projection horizontal footprint $\text{hypot}(\Delta x, \Delta z) \le 3.0\text{ m}$ and $y \in [0.0, 20.0]\text{ m}$.
  * Eliminates vertical cone blind spots. Flags `target_found: True` ($+10.0$ individual, $+0.2$ team).
