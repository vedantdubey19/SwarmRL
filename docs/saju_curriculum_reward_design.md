# Saju Curriculum Reward Tuning

## Day 24 objective

Support reward tuning across curriculum stages by scaling the obstacle
collision penalty according to normalized training progress.

## Scope

This component adjusts the obstacle-collision reward weight only. It
does not place obstacles, change environment difficulty, or alter the
training loop. The training or environment integration can ask the tuner
for a reward configuration at a given progress value.

## Stages

The default schedule has three stages:

| Stage | Progress interval | Obstacle penalty scale |
| --- | --- | ---: |
| Easy | 0.00 to less than 0.34 | 0.25 |
| Moderate | 0.34 to less than 0.67 | 0.60 |
| Full | 0.67 to 1.00 | 1.00 |

The selected scale multiplies the configured `obstacle_collision`
weight. Since that weight is negative, a smaller scale produces a
smaller-magnitude penalty in earlier stages.

## Example

```python
tuner = CurriculumRewardTuner(
    base_config=RewardConfig()
)

profile = tuner.resolve(progress=0.5)
stage_name = profile.stage_name
reward_config = profile.reward_config
```

Pass `reward_config` to the existing reward calculation. Other reward
weights are preserved.

## Validation

The tuner rejects:

- Progress outside the inclusive range from 0 to 1.
- Empty stage lists.
- Duplicate stage names.
- Scales outside the range from 0 to 1.
- Stage schedules whose scales decrease.

## Limitations

This is a deterministic stage-based schedule, not an adaptive learner.
The progress value must be supplied by the caller. Reward schedules
should be evaluated in the actual training environment before being
used for a training run.