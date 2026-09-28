# Saju Scenario and Curriculum Design

## Owner

Saju

## Day 11 objective

Provide repeatable scenario presets for swarm simulation, curriculum
training, obstacle testing, wind testing, and 50-agent stress testing.

## Scenario levels

| Level | Agents | Targets | Obstacles | Wind |
|---|---:|---:|---:|---:|
| Baseline | 5 | 1 | 0 | 0.0 |
| Easy | 10 | 3 | 5 | 0.0 |
| Medium | 20 | 5 | 12 | 0.5 |
| Hard | 35 | 8 | 20 | 1.0 |
| Stress | 50 | 10 | 30 | 1.5 |

## Main classes and functions

```python
ScenarioLevel
ScenarioConfig
scenario_preset()
curriculum_scenarios()
scenario_layout()
```

## Deterministic generation

A scenario has a seed. The same configuration and seed generate the
same:

- Agent starting positions.
- Obstacle positions.
- Obstacle radii.
- Target positions.

This makes testing and PPO/MAPPO comparisons reproducible.

## Scenario layout

```python
layout = scenario_layout(config)
```

Returns:

```text
scenario
agents
obstacles
targets
```

The output is JSON compatible and can be passed to the environment or
saved as an experiment configuration.

## Curriculum order

```text
Baseline → Easy → Medium → Hard → Stress
```

Venkatesh can use these stages for curriculum training. Humera can use
the generated objects when resetting the environment.

## Responsibility boundary

This module provides configurations and deterministic layouts. It does
not move drones, apply wind forces, run training, or render objects.
Those responsibilities remain with the environment, training, and
frontend modules.