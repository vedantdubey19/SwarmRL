# Saju Metrics Export Design

## Owner

Saju

## Day 10 objective

Export swarm metrics collected by `MetricsTracker` into files for model
training analysis, dashboard charts, project reviews, and final audit
evidence.

## Export formats

### JSON history export

```python
export_metrics_json(tracker, "output/metrics.json")
```

Creates a JSON file with:

- `records`: one metric record per simulation step.
- `summary`: aggregate statistics across all recorded steps.

The export can include per-agent metrics or only swarm-level metrics.

### CSV export

```python
export_metrics_csv(tracker, "output/metrics.csv")
```

Creates one tabular row per simulation step.

CSV fields:

- Step
- Episode
- Active agents
- Explored fraction
- Total reward
- Mean reward
- Newly explored cells
- Drone collisions
- Obstacle collisions
- Targets found
- Boundary violations
- Visible targets
- Visible obstacles
- Visible drones

### Summary JSON export

```python
export_summary_json(tracker, "output/summary.json")
```

Creates only the aggregate summary.

## Intended users

### Venkatesh

Use CSV and JSON metrics to compare:

- Baseline PPO.
- Shared-policy PPO.
- MAPPO.
- Training iterations.
- Exploration and collision behavior.

### Dhruv

Use CSV data to build dashboard charts:

- Percentage of map explored.
- Total collisions.
- Reward trend.
- Targets found.

### Vedant

Use JSON summaries as milestone and audit evidence.

## File handling

- Parent directories are created automatically.
- JSON exporters require a `.json` suffix.
- CSV exporter requires a `.csv` suffix.
- Tests use temporary directories, so project source folders remain
  clean.

## Responsibility boundary

This module exports existing metrics. It does not run training, create
dashboard charts, or start a WebSocket server.