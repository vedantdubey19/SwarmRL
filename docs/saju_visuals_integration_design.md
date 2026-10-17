# Saju Visuals Integration Readiness

## Day 28 objective

Validate that a curriculum-tuned reward configuration and reward-tuning
comparison are ready for full visuals integration testing.

## Scope

This module performs readiness checks only. It does not place obstacles,
modify the environment, start training, or render visuals.

## Public API

```python
validate_visuals_integration(...)
export_visuals_integration_check(...)
```

The check returns a `VisualsIntegrationCheck` value object with:

```python
check.ready
check.issues
check.to_dict()
check.to_json()
```

## Validation

The validator reports an issue when:

- The comparison has no changed fields.
- The comparison does not change `obstacle_collision`.
- The tuned obstacle-collision penalty is positive.
- A supplied difficulty profile has a different reward configuration.

## Example

```python
check = validate_visuals_integration(
    reward_config=profile.reward_config,
    comparison=comparison,
)

check.ready
check.issues
```

## Responsibility boundary

This module does not:

- Generate obstacles.
- Modify reward configurations.
- Start training.
- Render visuals.
- Replace reward tuning or curriculum difficulty scaling.

It validates readiness for integration testing.