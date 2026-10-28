# SwarmRL WebSocket Wire Protocol Specification

The SwarmRL telemetry system streams real-time physical simulation states from the Python multi-agent simulator across a Node.js WebSocket relay to the React-Three-Fiber WebGL frontend. All messages conform strictly to the single source of truth defined in [`server/schema.json`](file:///Users/vedantdubey_20/Downloads/SwarRL/server/schema.json).

---

## 1. Connection Lifecycle and Roles

Clients register with a role handshake immediately upon opening the WebSocket connection:

```json
{
  "type": "register",
  "role": "publisher" | "subscriber"
}
```

- **Publisher** (`sensors/ws_publisher.py`, `scripts/run_live_sim.py`): Pushes simulation frames, static world layouts, and grid updates.
- **Subscriber** (`frontend/src/hooks/useSwarmWebSocket.js`): Consumes telemetry streams.
- **Late Joiners**: The relay caches the latest `world` and `grid_snapshot` messages. When a new subscriber connects, it immediately receives both cached messages before live frame streaming begins.
- **Backpressure Handling**: If a subscriber's socket buffer exceeds 512 KB (`bufferedAmount > 524288`), incoming frames are dropped for that subscriber rather than queueing without limit.

---

## 2. Message Types

### 2.1 `world` (Static Environment Topology)
Broadcasted upon environment reset or scenario change.

```json
{
  "version": "1.0.0",
  "type": "world",
  "bounds": {
    "x_min": -50.0,
    "x_max": 50.0,
    "y_min": 0.0,
    "y_max": 20.0,
    "z_min": -50.0,
    "z_max": 50.0
  },
  "obstacles": [
    {
      "shape": "box",
      "position": [10.0, 5.0, -15.0],
      "size": [4.0, 10.0, 4.0]
    },
    {
      "shape": "cylinder",
      "position": [-20.0, 5.0, 25.0],
      "radius": 3.0,
      "height": 10.0
    }
  ],
  "targets": [
    {
      "id": 0,
      "position": [35.0, 1.0, -20.0],
      "radius": 1.0,
      "found": false
    }
  ]
}
```

### 2.2 `frame` (Dynamic 30 Hz Swarm Telemetry)
Transmitted at 30 Hz containing the full kinematic state of all 50 drones and global performance metrics.

```json
{
  "version": "1.0.0",
  "type": "frame",
  "step": 142,
  "timestamp": 1730107200123,
  "sim_time": 14.2,
  "drones": [
    {
      "id": 0,
      "agent_id": "drone_0",
      "position": [12.45, 4.12, -8.31],
      "velocity": [1.5, 0.0, -2.1],
      "heading": 0.7854,
      "quaternion": [0.0, 0.3827, 0.0, 0.9239],
      "status": "active",
      "detections": [
        {
          "id": "target_0",
          "type": "target",
          "distance": 8.42,
          "bearing_x": 0.12,
          "bearing_y": -0.05,
          "angle": 0.13
        }
      ]
    }
  ],
  "metrics": {
    "explored_fraction": 0.342,
    "collision_totals": {
      "drone": 0,
      "obstacle": 0,
      "boundary": 0,
      "total": 0
    },
    "targets_found": 1,
    "total_targets": 4,
    "active_agents": 50,
    "difficulty": 0,
    "step_reward_sum": 24.5
  }
}
```

- **Drone Status Values**: `"active"`, `"collided_drone"`, `"collided_obstacle"`, `"out_of_bounds"`.
- **Heading Convention**: Heading 0 rad points along $+X$ in the $X-Z$ plane; $+Y$ is vertical altitude. In Three.js coordinates: `rotation.y = -heading + Math.PI / 2`.

### 2.3 `grid_snapshot` (Full Exploration Bitmask)
Transmitted upon reset and periodically for client synchronization.

```json
{
  "version": "1.0.0",
  "type": "grid_snapshot",
  "step": 142,
  "width": 50,
  "height": 50,
  "bitmask": "base64_encoded_packed_bits=="
}
```

- **Bitmask Packing**: The 50x50 boolean grid is packed into bytes using NumPy's `np.packbits(grid.flatten())` with MSB-first ordering (bit 7 is index 0, bit 6 is index 1). Total size is $\lceil 2500 / 8 \rceil = 313$ bytes, base64-encoded to 420 characters.

### 2.4 `grid_delta` (Sparse Incremental Exploration Updates)
Transmitted per step when drones uncover new cells.

```json
{
  "version": "1.0.0",
  "type": "grid_delta",
  "step": 143,
  "new_cells": [1245, 1246, 1295]
}
```

- `new_cells`: List of flattened cell indices ($index = row \times 50 + col$).

---

## 3. Client Frame Ordering and Drop Rules

To handle network jitter and prevent temporal stuttering, the client rejects:
1. Any frame where `incoming.step < last_accepted.step`.
2. Any frame where `incoming.step == last_accepted.step` and `incoming.timestamp <= last_accepted.timestamp`.
