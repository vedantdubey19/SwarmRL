# Saju Event Detection Design

## Owner

Saju

## Day 5 objective

Provide reusable event-detection functions for the environment and
reward modules.

## Supported events

- Drone-to-drone collision.
- Drone-to-obstacle collision.
- Target discovery.
- Boundary violation.

## Coordinate convention

All positions use:

```text
[x, y, z]
```

The event functions currently treat all three coordinates as part of
distance and boundary checks. The final environment owner must confirm
whether collision checks should use three-dimensional distance or only
the ground-plane x-z distance.

## Event thresholds

| Event | Default threshold |
|---|---:|
| Drone collision | 2.0 units |
| Obstacle collision distance | 1.0 unit |
| Target detection distance | 3.0 units |
| Boundary tolerance | 0.0 units |

Obstacle radius is added to the obstacle collision distance.

## Event flag output

For one agent, `build_event_flags()` returns:

```python
{
    "drone_collision": bool,
    "obstacle_collision": bool,
    "target_found": bool,
    "boundary_violation": bool,
}
```

These flags can be passed directly into `calculate_reward()`.

## Integration example

```python
flags = build_event_flags(
    agent_id=agent_id,
    drone_positions=drone_positions,
    obstacles=obstacles,
    targets=targets,
    world_min=world_min,
    world_max=world_max,
)

reward, info = calculate_reward(
    agent_id=agent_id,
    new_cells=new_cells,
    previously_explored=previously_explored,
    target_found=flags["target_found"],
    drone_collision=flags["drone_collision"],
    obstacle_collision=flags["obstacle_collision"],
    boundary_violation=flags["boundary_violation"],
)
```

## Validation

The module rejects:

- Invalid position shapes.
- Non-finite position values.
- Invalid world bounds.
- Non-positive event distances.
- Negative boundary tolerance.
- Negative obstacle radii.