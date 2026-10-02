# Saju Training Audit Design

## Owner

Saju

## Day 12 objective

Analyze recorded swarm metrics and provide repeatable reports for the
training audit, baseline comparison, MAPPO comparison, and project
review milestones.

## Main class

```python
AuditReport
```

An audit report contains:

- Total simulation steps.
- Starting exploration fraction.
- Final exploration fraction.
- Exploration gain.
- Mean total reward.
- Reward standard deviation.
- Cumulative reward.
- Newly explored cells.
- Drone collisions.
- Obstacle collisions.
- Targets found.
- Boundary violations.
- Average sensor visibility counts.

## Main functions

```python
build_audit_report()
compare_audit_reports()
export_audit_report()
export_audit_comparison()
```

## Audit workflow

```text
MetricsTracker history
        ↓
build_audit_report()
        ↓
AuditReport JSON
        ↓
compare baseline and candidate runs
```

## Comparison use

Venkatesh can compare a baseline PPO run against a MAPPO run using:

- Exploration gain delta.
- Final explored-fraction delta.
- Mean-reward delta.
- Cumulative-reward delta.
- New-cells delta.
- Collision deltas.
- Target-found delta.
- Boundary-violation delta.

Positive reward, exploration, new-cell, and target deltas may indicate
improvement. Negative collision and boundary-violation deltas may also
indicate improvement.

## Important interpretation rule

A single audit does not prove that one algorithm is better. Experiments
should use the same scenario, seed policy, episode length, and evaluation
criteria before making a comparison claim.

## Export

Audit reports and comparisons are exported as JSON:

```python
export_audit_report(report, "output/audit.json")
export_audit_comparison(comparison, "output/comparison.json")
```

## Responsibility boundary

This module summarizes recorded metrics. It does not train models, run
the environment, or select the best checkpoint automatically.