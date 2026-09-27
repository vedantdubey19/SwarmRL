# Saju Reward Design

## Owner

Saju

## Day 4 objective

Provide a transparent reward calculation for each drone. The total reward
must be accompanied by separate components so that the training team can
understand why an agent received a positive or negative result.

## Calibrated reward values (Anti-Freeze & Swarm Coordination)

| Event | Value |
|---|---:|
| Newly explored cell | +1.0 |
| Rescue target found | +20.0 |
| Drone collision | -100.0 |
| Obstacle collision | -50.0 |
| Boundary violation | -10.0 |
| Repeated explored area | -0.1 |
| Normal step cost | -0.01 |

## Reward equation

```text
total =
    new_area
  + target_found
  + drone_collision
  + obstacle_collision
  + boundary_violation
  + repeated_area
  + step_cost
```

Penalty values are already negative.

## Reward output

The reward module provides:

- `RewardConfig`
- `RewardBreakdown`
- `calculate_reward_breakdown()`
- `calculate_reward()`

The compatibility function returns:

```text
(total_reward, reward_details)
```

The details dictionary contains:

- `new_area`
- `target_found`
- `drone_collision`
- `obstacle_collision`
- `boundary_violation`
- `repeated_area`
- `step_cost`
- `total`

## Validation rules

- `new_cells` must be a non-negative integer.
- Agent ID must not be empty.
- Positive exploration or target values are rejected.
- Positive collision, boundary, repeated-area, and step-cost values are
  rejected.
- Reward details must contain ordinary JSON-compatible numbers.

## Integration usage

The environment can call:

```python
reward, info = calculate_reward(
    agent_id=agent_id,
    new_cells=new_cells,
    previously_explored=previously_explored,
    target_found=target_found,
    drone_collision=drone_collision,
    obstacle_collision=obstacle_collision,
    boundary_violation=boundary_violation,
)
```

The returned `reward` can be passed to the RL algorithm. The returned
`info` dictionary can be stored in the environment info output and used
for debugging, dashboards, and experiment analysis.

## Tuning policy

These are initial values, not final scientifically validated values.
Changes should be evaluated with:

- Random-policy tests.
- Independent PPO.
- Shared-policy PPO.
- MAPPO.
- Collision counts.
- Percentage of map explored.
- Number of targets found.
