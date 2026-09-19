# Saju Reward Design

## Owner

Saju

## Day 4 objective

Provide a transparent reward calculation for each drone. The total reward
must be accompanied by separate components so that the training team can
understand why an agent received a positive or negative result.

## Calibrated reward values (Anti-Freeze & Swarm Coordination)

| Event | Value | Rationale |
|---|---:|---|
| Newly explored cell (individual) | +1.0 | Primary ego-incentive for discovering frontier cells |
| Team explored cell (swarm-wide) | +0.05 | Shared credit ($\Delta \text{SwarmCells} \times 0.05$) to align decentralized agents |
| Rescue target found (finder) | +10.0 | High reward for locating survivor |
| Rescue target found (team) | +0.2 | Shared reward across swarm (+10.0 / 50 agents) |
| Drone collision | -5.0 | Rescaled from -100 to eliminate policy entropy collapse / zero-velocity freeze |
| Obstacle collision | -5.0 | Rescaled from -50 to keep balanced with exploration budget |
| Boundary violation | -5.0 | Penalty for leaving active arena |
| Proximity penalty weight | -0.5 | Soft repulsive penalty per meter within 3.0m safety threshold |
| Repeated explored area | 0.0 | Disabled by default to prevent penalizing trailing formation followers |
| Normal step cost | -0.01 | Minor continuous time pressure |

## Reward equation

```text
total =
    new_area
  + team_new_area
  + target_found
  + team_target_found
  + drone_collision
  + obstacle_collision
  + boundary_violation
  + repeated_area
  + proximity_penalty
  + step_cost
```

Penalty values are zero or negative. Proximity penalty is computed as:
```text
proximity_penalty = config.proximity_penalty * (config.proximity_threshold - min_neighbor_dist)
```
when `min_neighbor_dist < config.proximity_threshold`, and `0.0` otherwise.

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
- `team_new_area`
- `target_found`
- `team_target_found`
- `drone_collision`
- `obstacle_collision`
- `boundary_violation`
- `repeated_area`
- `proximity_penalty`
- `step_cost`
- `total`

## Validation rules

- `new_cells` and `team_cells` must be non-negative integers.
- `min_neighbor_dist` must be a non-negative number if provided.
- Agent ID must not be empty.
- Negative exploration or target values in `RewardConfig` are rejected.
- Positive collision, boundary, repeated-area, proximity, and step-cost values in `RewardConfig` are rejected.
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
    config=config,
    team_cells=team_cells,
    team_target_found=team_target_found,
    min_neighbor_dist=min_neighbor_dist,
)
```

The returned `reward` can be passed to the RL algorithm. The returned
`info` dictionary can be stored in the environment info output and used
for debugging, dashboards, and experiment analysis.

## Tuning policy

Changes should be evaluated with:

- Collision counts and distance distributions.
- Percentage of map explored over episode steps.
- Number of targets found across 50 drones.
- MAPPO value function stability (critic loss and policy entropy).