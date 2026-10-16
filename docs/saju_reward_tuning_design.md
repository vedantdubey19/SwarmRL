# Saju Reward Tuning Comparison

## Day 27 objective

Support continued reward tuning alongside curriculum retraining by
comparing a baseline reward configuration with a curriculum-tuned reward
configuration.

## Scope

This module compares reward configurations only. It does not modify
obstacle placement, environment difficulty, training loops, or telemetry
artifacts.

## Public API

```python
compare_reward_configs(...)
export_reward_tuning_comparison(...)
```

The comparison returns a `RewardTuningComparison` value object with:

```python
comparison.changed_fields
comparison.changed_field_names
comparison.unchanged_fields
comparison.to_dict()
comparison.to_json()
```

## Field comparison

For every field in `RewardConfig`, the comparison records:

- Baseline value.
- Tuned value.
- Absolute change.
- Percentage change.

Percentage change is `None` when the baseline value is zero.

## Example

```python
comparison = compare_reward_configs(
    baseline_config=RewardConfig(),
    tuned_config=profile.reward_config,
)

comparison.changed_field_names
```

## Validation

The comparison rejects non-`RewardConfig` inputs. Export requires a
`.json` output suffix and creates parent directories when needed.

## Responsibility boundary

This module does not:

- Change reward weights.
- Place obstacles.
- Modify the environment.
- Start training.
- Replace curriculum reward tuning.

It records and exports the difference between reward configurations.