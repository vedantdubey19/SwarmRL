# Saju Telemetry Health Check Design

## Owner

Saju

## Day 21 objective

Validate the consistency of a completed telemetry artifact bundle before
it is submitted for review or used in a dashboard or audit workflow.

## Main components

```python
TelemetryHealthChecker
TelemetryHealthResult
TelemetryHealthError
```

## Input bundle

```text
metrics.jsonl
events.jsonl
report.json
```

The checker validates the relationship between these three artifacts.

## Checks

The health checker verifies:

- Required file suffixes.
- File existence.
- Metrics JSON-lines validity.
- Event JSON-lines validity.
- Non-empty metrics input.
- Strictly increasing metric steps.
- Report JSON validity.
- Presence of `session_summary`.
- Presence of `event_summary`.
- Equality between report metrics and source metrics.
- Equality between report events and source events.
- Matching report source paths.
- Timezone-aware check timestamp.

## Result schema

```json
{
  "healthy": true,
  "checked_at": "2026-10-06T12:05:00+00:00",
  "metrics_records": 3,
  "event_records": 2,
  "metric_steps_ordered": true,
  "report_matches_metrics": true,
  "report_matches_events": true,
  "issues": []
}
```

When validation fails, `healthy` is `false` and `issues` contains
human-readable explanations.

## Usage

```python
checker = TelemetryHealthChecker(
    "output/metrics.jsonl",
    "output/events.jsonl",
    "output/report.json",
)

result = checker.check()

checker.check_and_export(
    "output/health.json"
)
```

## Responsibility boundary

This module does not:

- Generate telemetry.
- Modify source artifacts.
- Start a service or WebSocket.
- Run simulation or training.
- Replace the session summary or combined report.
- Automatically repair invalid files.

It only validates and reports the condition of completed artifacts.

## Test coverage

Tests cover:

- Healthy artifact bundles.
- JSON serialization.
- Missing files.
- Invalid suffixes.
- Unordered metric steps.
- Malformed reports.
- Missing report sections.
- Mismatched report counts.
- Mismatched source paths.
- Invalid clocks.
- Health-result JSON export.