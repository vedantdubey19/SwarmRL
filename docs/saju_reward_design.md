# Saju Reward Design

## Owner

Saju

## Objective

Encourage exploration and target discovery while discouraging collisions,
obstacle contact, boundary violations, and repeated search.

## Initial reward values

| Event | Reward |
|---|---:|
| Newly explored cell | +1.0 |
| Target found | +20.0 |
| Drone collision | -100.0 |
| Obstacle collision | -50.0 |
| Boundary violation | -10.0 |
| Repeated explored area | -0.1 |
| Step cost | -0.01 |

## Output

The reward function returns the total reward and individual reward
components for debugging and training analysis.