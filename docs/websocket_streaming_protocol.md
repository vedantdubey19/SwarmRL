# SwarmRL WebSocket Streaming Protocol Specification

## Overview
This document specifies the wire protocol, message envelope, serialization formats, and synchronization semantics connecting the Python RL simulation/rollout engine, the Node.js WebSocket broker (`server.js`), and the React-Three-Fiber (R3F) 3D frontend.

---

## 1. Connection Roles & Handshake

Upon opening a WebSocket connection to `ws://localhost:8080`, every client must register its role:

### Registration Message
```json
{
  "type": "register",
  "role": "publisher"
}
```
* `"role": "publisher"`: The Python simulation engine (sources simulation frames).
* `"role": "subscriber"`: The R3F 3D visualization frontend (consumes frames).

### Server Acknowledgment
```json
{
  "type": "registered",
  "role": "subscriber",
  "status": "ready"
}
```

---

## 2. Telemetry Frame Packet (Publisher $\to$ Subscriber)

Dispatched synchronously by the simulation engine at the end of each physical step ($20\text{--}30\text{ Hz}$).

### JSON Schema
```json
{
  "type": "frame",
  "step": 1420,
  "timestamp": 1726501234.567,
  "sim_time": 71.0,
  "metrics": {
    "explored_fraction": 0.642,
    "active_drones": 48,
    "targets_found": 3,
    "total_targets": 5,
    "step_reward_sum": 12.4
  },
  "drones": [
    {
      "id": 0,
      "agent_id": "drone_0",
      "pos": [12.4, 5.0, -8.2],
      "vel": [1.2, 0.0, -2.1],
      "heading": 1.5708,
      "rot": [0.0, 0.7071, 0.0, 0.7071],
      "status": "active",
      "detections": [
        { "id": "target_1", "type": "target", "dist": 8.4, "angle": 0.12 }
      ]
    }
  ],
  "targets": [
    {
      "id": 0,
      "pos": [25.0, 0.5, 18.0],
      "found": true,
      "discovered_by": "drone_0"
    }
  ]
}
```

### Drone `status` Enum
* `"active"`: Normal flight.
* `"collided_drone"`: Drone collision event (trigger crash particle FX in R3F).
* `"collided_obstacle"`: Hit static obstacle.
* `"out_of_bounds"`: Violated arena boundaries.

---

## 3. Exploration Grid Streaming Protocol

To prevent transmitting $50 \times 50 = 2,500$ floats every frame ($75\text{ KB/s}$ uncompressed JSON):

### Option A: Sparse Delta Stream (Recommended during exploration)
Only newly explored cells are transmitted per frame:
```json
{
  "type": "grid_delta",
  "step": 1420,
  "new_cells": [
    [14, 22],
    [14, 23],
    [15, 22]
  ]
}
```

### Option B: Snapshot Bitmask (Sent on client connect or reset)
A binary bitmask of 2,500 bits ($313\text{ bytes}$) encoded in base64:
```json
{
  "type": "grid_snapshot",
  "step": 1420,
  "resolution": [50, 50],
  "cell_size": 2.0,
  "data_base64": "AP8A/wAA...=="
}
```

---

## 4. Simulation Control Uplink (Frontend $\to$ Simulation)

Sent by user controls in R3F (Play, Pause, Step, Speed, Reset):

```json
{
  "type": "control",
  "action": "pause"
}
```

### Supported Actions
| Action | Parameters | Expected Behavior |
|---|---|---|
| `"play"` | `{}` | Resume simulation stepping loop. |
| `"pause"` | `{}` | Pause simulation stepping loop. |
| `"step"` | `{}` | Execute a single simulation step ($\Delta t$). |
| `"reset"` | `{ "seed": 42 }` | Reset environment and randomize agent/target positions. |
| `"set_rate"` | `{ "multiplier": 2.0 }` | Scale simulation speed relative to wall-clock time. |

### Confirmation Response
```json
{
  "type": "control_ack",
  "action": "reset",
  "status": "ok"
}
```
