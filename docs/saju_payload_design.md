# Saju Sensor Payload Design

## Owner

Saju

## Day 7 objective

Create one stable, JSON-compatible format for sending sensor,
exploration, reward, and event information to the WebSocket and frontend
layers.

## Single-agent payload

The payload contains:

- Protocol version.
- Simulation step.
- Timestamp.
- Agent ID.
- Position.
- Heading.
- Explored fraction.
- Visible detections.
- Visible target count.
- Visible obstacle count.
- Visible drone count.
- Reward.
- Reward components.
- Event flags.

Example:

```json
{
  "version": 1,
  "step": 12,
  "timestamp": "2026-09-21T12:00:00+00:00",
  "agent_id": "drone_000",
  "position": {
    "x": 10.0,
    "y": 4.0,
    "z": 5.0
  },
  "heading": 1.57,
  "explored_fraction": 0.25,
  "visible_targets": 1,
  "visible_obstacles": 0,
  "visible_drones": 2,
  "reward": 0.99,
  "reward_components": {
    "new_area": 1.0,
    "step_cost": -0.01
  },
  "event_flags": {
    "drone_collision": false,
    "obstacle_collision": false,
    "target_found": true,
    "boundary_violation": false
  }
}
```

## Swarm payload

The swarm payload contains:

- Protocol version.
- Simulation step.
- Timestamp.
- List of agent payloads.
- Explored-map fraction.
- Explored-map grid.

## JSON compatibility

NumPy arrays and scalar types are converted into ordinary Python lists,
integers, floats, and booleans before serialization.

Use:

```python
ensure_json_serializable(payload)
```

during tests to verify that the payload can be encoded as JSON.

## Integration

Arya can send the result of `build_swarm_payload()` through WebSocket.

Dhruv can use:

- `agents` for drone rendering.
- `position` for placement.
- `heading` for orientation.
- `detections` for sensor visuals.
- `event_flags` for warnings.
- `map.grid` for explored-area rendering.

Venkatesh can use the existing observation vector separately for RL
training. The JSON payload is intended for streaming and visualization,
not as the direct training input.