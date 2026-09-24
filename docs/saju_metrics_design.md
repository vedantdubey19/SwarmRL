# Saju Metrics and Audit Design

## Owner

Saju

## Day 9 objective

Collect consistent per-agent and swarm-level metrics for training,
debugging, WebSocket streaming, dashboard charts, and final audit logs.

## Per-agent metrics

Each agent record contains:

- Reward.
- Newly explored cells.
- Visible targets.
- Visible obstacles.
- Visible drones.
- Drone collision flag.
- Obstacle collision flag.
- Target-found flag.
- Boundary-violation flag.

## Swarm metrics

Each simulation-step record contains:

- Step number.
- Episode number.
- Active agent count.
- Explored-map fraction.
- Total reward.
- Mean reward.
- Newly explored cells.
- Drone-collision count.
- Obstacle-collision count.
- Target-found count.
- Boundary-violation count.
- Visibility totals.

## Main classes

```python
AgentMetrics
SwarmMetrics
MetricsTracker
```

## Main functions

```python
build_agent_metrics()
metrics_from_payload()
```

## Data flow

```text
Sensor observation + reward + event flags
        ↓
AgentMetrics
        ↓
SwarmMetrics
        ↓
MetricsTracker
        ↓
Training logs / dashboard / audit records
```

## Dashboard uses

Dhruv can display:

- Percentage of map explored.
- Total collisions.
- Targets found.
- Reward trend.
- Mean reward.
- Number of active drones.

## Training uses

Venkatesh can inspect:

- Reward trend by step.
- Exploration improvement.
- Collision rate.
- Target detection rate.
- Episode summaries.

## JSON output

Both metric records and tracker summaries are JSON serializable. Use:

```python
metrics.to_json()
tracker.summary_json()
```

## Logging

`MetricsTracker.record()` emits an INFO log entry. The application can
configure Python logging handlers to write these records to the terminal,
file, or experiment-monitoring system.