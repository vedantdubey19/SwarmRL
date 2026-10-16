# Saju Obstacle Difficulty Scaling

## Day 26 objective

Provide a deterministic obstacle difficulty schedule for curriculum
training.

The scaler maps normalized training progress to a difficulty level,
obstacle count, obstacle speed scale, and reward configuration.

## Scope

This module does not place obstacles, modify the environment, or run
training. It only resolves difficulty settings from a progress value
supplied by the caller.

## Difficulty levels

| Progress | Level | Obstacle count | Speed scale | Reward scale |
| --- | --- | ---: | ---: | ---: |
| 0.00 to less than 0.34 | Easy | 2 | 0.50 | 0.25 |
| 0.34 to less than 0.67 | Moderate | 4 | 0.75 | 0.60 |
| 0.67 to 1.00 | Hard | 6 | 1.00 | 1.00 |

## Public API

```python
ObstacleDifficultyScaler
ObstacleDifficultyProfile
DifficultyLevel
DifficultyScaleError
resolve_obstacle_difficulty
```

## Usage

```python
scaler = ObstacleDifficultyScaler()

profile = scaler.resolve(progress=0.5)

profile.level_name
profile.obstacle_count
profile.obstacle_speed_scale
profile.reward_profile.reward_config
```

## Validation

The scaler rejects:

- Progress outside the inclusive range from 0 to 1.
- Empty difficulty schedules.
- Duplicate level names.
- Decreasing obstacle counts.
- Decreasing speed scales.
- Decreasing reward scales.

## Responsibility boundary

This module does not:

- Generate obstacles.
- Modify source artifacts.
- Start training.
- Replace the curriculum reward tuner.
- Automatically adapt based on training results.

It provides a deterministic schedule that can be consumed by an
environment or training integration.