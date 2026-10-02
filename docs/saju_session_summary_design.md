# Saju Telemetry Session Summary Design

## Owner

Saju

## Day 17 objective

Create a compact, reproducible summary from a completed telemetry
JSON-lines session.

The summary supports dashboard displays, training-run comparisons, and
audit evidence without requiring callers to manually aggregate every
telemetry record.

## Main components

```python
TelemetrySessionSummary
TelemetrySummaryError
summarize_telemetry_session()
export_session_summary()
summarize_and_export_session()
```

## Data flow

```text
TelemetryRecorder
        ↓
metrics.jsonl
        ↓
summarize_telemetry_session()
        ↓
TelemetrySessionSummary
        ↓
export_session_summary()
        ↓
summary.json
```

## Aggregated metrics

The session summary includes:

- Total record count.
- First and last simulation step.
- Start and final explored-map fraction.
- Exploration gain.
- Cumulative and mean total reward.
- Cumulative newly explored cells.
- Drone-collision count.
- Obstacle-collision count.
- Target-found count.
- Boundary-violation count.

## Usage

```python
from sensors.session_summary import (
    summarize_and_export_session,
)

summary = summarize_and_export_session(
    "output/metrics.jsonl",
    "output/summary.json",
)
```

The returned `TelemetrySessionSummary` can be used immediately in
Python, while `summary.json` is suitable for dashboards, reports, and
audit records.

## Input validation

The JSON-lines input must:

- Have a `.jsonl` suffix.
- Exist and contain at least one nonblank record.
- Contain one JSON object per nonblank line.
- Use `"type": "swarm_metrics"`.
- Include a metrics object.
- Include an integer, non-boolean `metrics["step"]`.
- Use numeric values for aggregated numeric metrics.

Invalid input raises `TelemetrySummaryError` with the affected line
number where applicable.

## Export safety

The summary writer:

1. Creates the output parent directory when needed.
2. Writes complete JSON to a temporary file in the output directory.
3. Flushes and synchronizes the temporary file.
4. Replaces the target `.json` file only after the complete write
   succeeds.

This approach avoids leaving a partially written summary at the final
output path.

## Responsibility boundary

This module does not:

- Start a server or WebSocket connection.
- Subscribe to the live stream.
- Generate telemetry.
- Modify recorded telemetry.
- Run training or simulation.
- Replace the existing detailed audit-report module.

It reads completed JSON-lines telemetry and produces a concise session
summary.

## Test coverage

Tests cover:

- Multi-record aggregation.
- Blank-line handling.
- Summary serialization.
- JSON export and replacement behavior.
- Combined summarize-and-export workflow.
- File and suffix validation.
- Empty input handling.
- Invalid JSON and message schemas.
- Invalid step and metric values.
- Export argument validation.