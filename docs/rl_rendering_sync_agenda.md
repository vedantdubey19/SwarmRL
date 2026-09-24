# SwarmRL RL Training & Rendering Sync: Technical Interface & Alignment Agenda

## Overview & Context
This document serves as the technical alignment brief for the synchronization between the **RL Training Team** (Venkatesh, Humera, Vedant, Saju) and the **Rendering Team** (Dhruv, Arya).

* **RL Training Status:** Running independent-learning baselines; integrating PettingZoo `ParallelEnv`, Saju's `ConeSensor`, and multi-agent reward attribution.
* **Rendering Status:** Three.js / React-Three-Fiber (R3F) viewport showing dummy drones (topographical grid + spheres) with randomized positions. Sensor visuals (cone-of-vision, ground-painting exploration heatmap) are ready for implementation.

---

## 1. Interface Data Formats: Current State

### A. Training & Reward Side Output

#### 1. PettingZoo `ParallelEnv.step(actions)` Signature
```python
obs, rewards, terminations, truncations, infos = env.step(actions)
```
* **`obs`**: `dict[str, np.ndarray]` where each agent vector is `Box(low=-inf, high=inf, shape=(81,), dtype=np.float32)`:
  * `[0:8]` Ego Kinematics: `[x/50, y/20, z/50, vx/10, vy/3, vz/10, cos(yaw), sin(yaw)]`
  * `[8:32]` K-Nearest Neighbors ($6 \times 4$): `[rel_dx/30, rel_dy/30, rel_dz/30, dist/30]`
  * `[32:56]` Sensor Cone Detections ($8 \times 3$): `[type_id, dist/20, angle/pi]` (`target: 1.0, obstacle: 2.0, drone: 3.0, empty: 0.0`)
  * `[56:81]` Local Exploration Patch: $5 \times 5$ local flattened grid slice (`0.0` or `1.0`)
* **`rewards`**: `dict[str, float]` — per-agent scalar step reward.
* **`terminations`**: `dict[str, bool]` — per-agent death flags plus `"__all__": bool`.
* **`truncations`**: `dict[str, bool]` — episode timeout flag.

#### 2. Reward Breakdown (`sensors/rewards.py`)
```python
total_reward, components = calculate_reward(...)
# components dict:
{
    "new_area": float,            # newly uncovered cells * 1.0
    "target_found": float,        # +20.0
    "drone_collision": float,     # -100.0
    "obstacle_collision": float,  # -50.0
    "boundary_violation": float,  # -10.0
    "repeated_area": float,       # -0.1
    "step_cost": float            # -0.01
}
```

#### 3. Per-Drone Telemetry Observation (`SensorObservation.to_dict()`)
```python
{
    "agent_id": "drone_000",
    "position": {"x": 12.4, "y": 5.0, "z": -8.2},
    "heading": 1.5708,             # Radians (0.0 = +X axis)
    "explored_fraction": 0.642,
    "detections": [
        {"id": "target_1", "type": "target", "distance": 8.4, "angle": 0.12}
    ],
    "visible_targets": 1,
    "visible_obstacles": 0,
    "visible_drones": 0
}
```

#### 4. Swarm Exploration Map (`sensors/exploration.py`)
* $100\text{m} \times 100\text{m}$ world, $2.0\text{m}$ cell size $\to$ **$50 \times 50$ boolean array** (`ExplorationMap.grid`).

---

### B. Rendering Side Input

#### 1. WebSocket Schema (`schema.js`)
```javascript
{
  id: "drone-1",               // string or number
  x: 0.0,                      // 3D position coordinates
  y: 0.0,
  z: 0.0,
  timestamp: 1726501234567
}
```

#### 2. Three.js / React-Three-Fiber Dummy State Pattern (`frontend/src/App.jsx`)
```jsx
// Viewport grid setup
<Grid
  position={[0, -0.01, 0]}
  args={[100, 100]}
  cellSize={2}
  sectionSize={10}
/>

// Dummy state consumed by R3F component:
// drones = [{ id: "drone_0", position: [x, y, z] }, ...]
{drones.map((drone) => (
  <mesh key={drone.id} position={drone.position}>
    <sphereGeometry args={[0.5, 16, 16]} />
    <meshStandardMaterial color="#38bdf8" />
  </mesh>
))}
```

---

## 2. Key Technical Divergences & Integration Risks

1. **Missing Heading / Orientation in Stream**:
   * *Problem:* Dummy drones are unoriented spheres. A 3D cone-of-vision **cannot be rendered** without orientation.
   * *Risk:* Saju's sensor model defines heading in the horizontal X-Z plane (`forward = [cos(h), 0, sin(h)]`), whereas Three.js meshes orient along negative Z by default. Without a locked transform (`rotation.y = -heading` or quaternion `[qx, qy, qz, qw]`), sensor cones will point $90^\circ$ perpendicular to velocity.

2. **Message Batching Mismatch (Atomic Swarm Frame vs. Single Message)**:
   * *Problem:* `schema.js` validates single-drone packets (`{ id, x, y, z }`).
   * *Risk:* At 50 drones $\times$ 25 Hz, the server must process **1,250 individual WebSocket messages/sec**. This saturates Node's event loop and forces R3F to re-render partial swarm states. Training outputs all 50 drones synchronously in a single simulation step.

3. **Wire Data Structures (Flat Arrays vs. Nested Objects)**:
   * *Problem:* `to_dict()` outputs nested `{position: {x, y, z}}`.
   * *Risk:* Three.js / R3F `InstancedMesh` matrix updates require contiguous flat arrays (`Float32Array`). Parsing 50 nested objects 25 times per second causes high JS garbage collection stutter.

4. **Exploration Grid Streaming Overhead**:
   * *Problem:* Dummy rendering does not ingest exploration data.
   * *Risk:* Transmitting the raw $50 \times 50$ grid (2,500 booleans/floats) every tick generates $\sim 75\text{ KB/s}$ of JSON payload, stalling the WebSocket pipe. Rendering requires a **sparse delta** stream (`new_cells: [[col, row], ...]`) to paint decals/textures incrementally.

---

## 3. Decision Matrix: Locked Now vs. Provisional

| Must Lock NOW (Blocks Sensor Visuals & Ground Painting) | Can Stay Provisional (Iterate Post-Sync) |
|---|---|
| **Coordinate & Heading Standard:** Lock 3D axes ($+Y$ up, $X$-$Z$ ground) and yaw convention ($0 = +X$ vs $-Z$, radians vs quaternion). | **3D Drone Assets:** Swapping spheres for glTF drone meshes, spinning rotors, and bank/pitch roll tilt. |
| **Atomic Step Telemetry Envelope:** Standardize `{ type: "frame", step, timestamp, drones: [...50], targets: [...] }`. | **Simulation Control Uplink:** Frontend Play/Pause/Reset buttons sending commands back to the Python runner. |
| **Sensor Cone Geometry & Detection Rays:** Range ($20\text{m}$), FoV ($90^\circ$), and detection payload format (`detections: [{id, type, dist, angle}]`) for dynamic highlight rays. | **HUD & RL Metric Graphs:** Displaying reward breakdowns, policy loss curves, and value baselines in UI overlays. |
| **Exploration Ground-Painting Wire Spec:** Sparse delta format `{ type: "grid_delta", new_cells: [[col, row], ...] }` and coordinate mapping: $\text{col} = \lfloor(x + 50)/2\rfloor$, $\text{row} = \lfloor(z + 50)/2\rfloor$. | **Binary Protocol Optimization:** Moving from JSON strings to binary ArrayBuffer, Protobuf, or FlatBuffers. |
| **Drone Status Enum:** Standardize strings (`"active"`, `"collided_drone"`, `"collided_obstacle"`, `"out_of_bounds"`) to control cone visibility and crash state. | **Obstacle / Terrain Models:** Procedural terrain heightmaps vs flat grid plane. |

---

## 4. Sync Agenda (Decisions Needed)

* **1. Spatial Coordinate Frame & Heading Transform Contract**
  * *Decision needed:* Agree on coordinate conversion between Saju's kinematics ($0\text{ rad} = +X$) and Three.js mesh forward. Decide between sending 2D yaw angle or 3D unit quaternion `rot: [qx, qy, qz, qw]`.
  * *Suggested Owner:* Saju / Venkatesh (Physics) & Dhruv (R3F)
  * *Target Deadline:* EOD Sync Day

* **2. Atomic Swarm Step Telemetry Envelope**
  * *Decision needed:* Formally replace `schema.js` single-drone messages with the unified step packet schema (`type: "frame"`) containing all 50 drones at 20–30 Hz.
  * *Suggested Owner:* Arya (WebSocket Broker) & Vedant (Python Bridge)
  * *Target Deadline:* Day 2, 12:00 PM

* **3. Sensor Cone-of-Vision Mesh & Highlight Ray Spec**
  * *Decision needed:* Lock cone parameters (Apex at drone center, Range: 20m, FoV: 90°) and verify `detections` array schema for rendering target intersection rays in Three.js.
  * *Suggested Owner:* Saju (Sensors) & Dhruv (R3F)
  * *Target Deadline:* Day 2, EOD

* **4. Ground-Painting Exploration Grid Protocol**
  * *Decision needed:* Approve sparse delta wire format (`new_cells: [[col, row], ...]`) and R3F texture update strategy (dynamic 2D canvas texture on ground plane vs instanced tile meshes).
  * *Suggested Owner:* Saju (Exploration) & Dhruv (R3F)
  * *Target Deadline:* Day 3, 12:00 PM

* **5. Drone Lifecycle & Collision State Machine**
  * *Decision needed:* Define visual handling when `status != "active"` (hide sensor cone, freeze velocity, render collision marker).
  * *Suggested Owner:* Humera (MARL) & Dhruv (R3F)
  * *Target Deadline:* Day 3, EOD

* **6. End-to-End Mock Integration Milestone**
  * *Decision needed:* Schedule date for training team to run a Python mock publisher streaming 50 animated drones + cones through Arya's WebSocket server into Dhruv's R3F canvas.
  * *Suggested Owners:* Arya (Relay), Vedant (Mock Publisher), Dhruv (Frontend)
  * *Target Deadline:* Joint Milestone Date
