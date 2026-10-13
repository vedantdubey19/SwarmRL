# Saju Dynamic Obstacle Reward Tests

## Day 25 objective

Validate the existing reward function under dynamic-obstacle conditions
and curriculum reward profiles.

## Scope

These tests do not change the reward algorithm, obstacle placement,
environment difficulty, or training loop.

They verify that obstacle-collision penalties and curriculum reward
profiles behave consistently.

## Covered behavior

- No obstacle collision produces zero obstacle penalty.
- An obstacle collision applies the configured negative penalty.
- Obstacle penalties combine correctly with new-area reward and step cost.
- Reward breakdown values include obstacle collision and total reward.
- Curriculum stages scale the obstacle-collision penalty.
- The `easy`, `moderate`, and `full` stages resolve as expected.
- Invalid curriculum progress is rejected.
- Positive obstacle-collision penalties are rejected.
- Reward details remain JSON-serializable.

## Curriculum scaling

The default curriculum schedule scales only `obstacle_collision`:

| Stage | Scale | Default penalty |
| --- | ---: | ---: |
| Easy | 0.25 | -1.25 |
| Moderate | 0.60 | -3.00 |
| Full | 1.00 | -5.00 |

The tests pass the curriculum profile’s `reward_config` directly to the
existing `calculate_reward` function.

## Run

```powershell
python -m pytest tests\test_dynamic_obstacle_rewards.py -q
python -m pytest -q
```

## Commit

```powershell
git add tests\test_dynamic_obstacle_rewards.py docs\saju_dynamic_obstacle_reward_tests.md
git commit -m "Test reward function with dynamic obstacles"
git push origin Saju
```