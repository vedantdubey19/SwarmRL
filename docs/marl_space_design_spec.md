# SwarmRL MARL Action & Observation Space Specification

## Overview
This specification details the mathematical definitions, tensor shapes, normalization bounds, and implementation blueprints for the 50-agent Multi-Agent Reinforcement Learning (MARL) environment using PettingZoo `ParallelEnv` and Ray RLlib MAPPO.

---

## 1. Action Space Specification

### Decision & Rationale
* **Space Type:** Continuous 4-DoF bounded vector `Box(low=-1.0, high=1.0, shape=(4,), dtype=np.float32)`.
* **Coupled Kinematics Fix:** Drones do not directly output pitch or roll. Pitch and roll are physically coupled to linear acceleration and computed procedurally for rendering.
* **Yaw Handling:** Angular control is specified via **yaw rate** ($\dot{\psi}$), avoiding $[-\pi, \pi]$ boundary jump discontinuities.

### Semantic Mapping
| Action Index | Symbol | Physical Meaning | Normalization Range | Physical Scale |
|---|---|---|---|---|
| `action[0]` | $v_x$ | Forward / Longitudinal Velocity | $[-1.0, 1.0]$ | $[-10.0, 10.0]\text{ m/s}$ |
| `action[1]` | $v_y$ | Lateral / Transverse Velocity | $[-1.0, 1.0]$ | $[-10.0, 10.0]\text{ m/s}$ |
| `action[2]` | $v_z$ | Vertical / Heave Velocity | $[-1.0, 1.0]$ | $[-3.0, 3.0]\text{ m/s}$ |
| `action[3]` | $\dot{\psi}$ | Yaw Angular Velocity | $[-1.0, 1.0]$ | $[-\pi, \pi]\text{ rad/s}$ |

### Implementation Blueprint
```python
import gymnasium as gym
import numpy as np

MAX_HORIZ_VEL = 10.0   # m/s
MAX_VERT_VEL  = 3.0    # m/s
MAX_YAW_RATE  = np.pi  # rad/s

def apply_drone_action(drone, action: np.ndarray, dt: float = 0.05):
    """Integrate continuous action into drone kinematics."""
    v_x = float(action[0]) * MAX_HORIZ_VEL
    v_y = float(action[1]) * MAX_HORIZ_VEL
    v_z = float(action[2]) * MAX_VERT_VEL
    yaw_rate = float(action[3]) * MAX_YAW_RATE

    drone.heading = (drone.heading + yaw_rate * dt) % (2 * np.pi)
    drone.velocity = np.array([v_x, v_y, v_z], dtype=np.float32)
    drone.position += drone.velocity * dt
```

---

## 2. Observation Space Specification

### Dimension Breakdown (Total: 81 Floats)
| Component | Dimensions | Representation & Normalization | Description |
|---|---|---|---|
| **Self State** | 8 | `[x/50, y/20, z/50, vx/10, vy/3, vz/10, cos(yaw), sin(yaw)]` | Ego position, velocity, and continuous heading unit vector. |
| **K-Nearest Neighbors** | 24 | 6 neighbors $\times$ 4 features: `[rel_dx/30, rel_dy/30, rel_dz/30, dist/30]` | Top-6 closest drones sorted strictly by Euclidean distance. Masked with `[0,0,0,1]` if out of 30m comm radius. |
| **Sensor Detections** | 24 | 8 objects $\times$ 3 features: `[type_id, dist/20, angle/pi]` | Output of Saju's `ConeSensor.vectorize()`. Types: `target: 1.0, obstacle: 2.0, drone: 3.0, empty: 0.0`. |
| **Local Coverage Patch** | 25 | $5 \times 5$ local grid patch centered on agent (values $0.0$ or $1.0$) | Local slice extracted from `ExplorationMap.grid` indicating explored status of surrounding cells. |

### Implementation Blueprint
```python
import gymnasium as gym
import numpy as np

OBS_DIM = 81

def get_agent_observation(agent_id: str, env) -> np.ndarray:
    drone = env.drones[agent_id]

    # 1. Self Kinematics (8)
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

    # 2. K-Nearest Neighbors (24)
    COMM_RADIUS = 30.0
    neighbors = [d for a_id, d in env.drones.items() if a_id != agent_id and d.alive]
    neighbors.sort(key=lambda d: np.linalg.norm(d.position - drone.position))

    knn_feat = []
    for neighbor in neighbors[:6]:
        rel_pos = neighbor.position - drone.position
        dist = float(np.linalg.norm(rel_pos))
        if dist <= COMM_RADIUS:
            knn_feat.extend([
                rel_pos[0] / COMM_RADIUS,
                rel_pos[1] / COMM_RADIUS,
                rel_pos[2] / COMM_RADIUS,
                dist / COMM_RADIUS,
            ])
        else:
            knn_feat.extend([0.0, 0.0, 0.0, 1.0])

    while len(knn_feat) < 24:
        knn_feat.extend([0.0, 0.0, 0.0, 1.0])

    # 3. Sensor Cone Vector (24)
    detections = env.cone_sensor.detect(drone.position, drone.heading, env.get_objects())
    sensor_feat = env.cone_sensor.vectorize(detections).tolist()

    # 4. Local Exploration Patch (25)
    local_patch = env.exploration_map.get_local_patch(drone.position, radius_cells=2)
    grid_feat = local_patch.flatten().tolist()

    obs = np.asarray(self_feat + knn_feat + sensor_feat + grid_feat, dtype=np.float32)
    return obs
```

---

## 3. RLlib MAPPO Centralized State Contract

### `env.state()` Implementation
MAPPO's centralized value function $V(S)$ requires a consistent, canonical environment state tensor:
```python
def state(self) -> np.ndarray:
    """Canonical global state for MAPPO centralized critic."""
    state_vector = []
    
    # Deterministically sorted drone states: drone_0 to drone_49
    for agent_id in self.possible_agents:
        if agent_id in self.drones and self.drones[agent_id].alive:
            d = self.drones[agent_id]
            state_vector.extend([
                d.position[0] / 50.0, d.position[1] / 20.0, d.position[2] / 50.0,
                d.velocity[0] / 10.0, d.velocity[1] / 3.0, d.velocity[2] / 10.0,
                np.cos(d.heading), np.sin(d.heading),
                1.0  # alive mask
            ])
        else:
            # Zero-mask dead drones preserving static shape
            state_vector.extend([0.0] * 8 + [0.0])
            
    # Target discovery status
    for target in self.targets:
        state_vector.extend([
            target.position[0] / 50.0,
            target.position[1] / 20.0,
            target.position[2] / 50.0,
            1.0 if target.found else 0.0
        ])
        
    # Global coverage metric
    state_vector.append(self.exploration_map.explored_fraction)

    return np.asarray(state_vector, dtype=np.float32)
```
