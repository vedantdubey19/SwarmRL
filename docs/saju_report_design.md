# Saju Telemetry Report Design

## Owner

Saju

## Day 20 objective

Combine the completed telemetry session summary and event-log summary
into one report suitable for audit evidence, dashboard handoff, and
training-run review.

## Main components

```python
TelemetryReport
TelemetryReportError
build_telemetry_report()
export_telemetry_report()
build_and_export_telemetry_report()
```

## Data flow

```text
metrics.jsonl ────────┐
                      ├── build_telemetry_report()
events.jsonl ─────────┘
                              ↓
                       TelemetryReport
                              ↓
                         report.json
```

## Report contents

The report includes:

- UTC generation timestamp.
- Source metrics JSON-lines path.
- Source event JSON-lines path.
- Session summary:
  - Total records.
  - First and last step.
  - Exploration start, final value, and gain.
  - Cumulative and mean reward.
  - Exploration, collision, target, and boundary totals.
- Event summary:
  - Total events.
  - Counts grouped by event.
  - Counts grouped by level.

## Usage

```python
report = build_and_export_telemetry_report(
    "output/metrics.jsonl",
    "output/events.jsonl",
    "output/report.json",
)
```

The builder returns a `TelemetryReport`, while the exporter writes a
readable JSON file.

## Validation

The report builder validates:

- Both source files use the `.jsonl` suffix.
- Both source files exist.
- Metrics input follows the session-summary schema.
- Events input follows the event-reader schema.
- The report clock returns a timezone-aware datetime.
- The output path uses a `.json` suffix.
- The export object is a `TelemetryReport`.

## Responsibility boundary

This module does not:

- Record live telemetry.
- Read from the async stream.
- Start services or WebSocket connections.
- Modify source JSON-lines files.
- Run simulation or training.
- Replace the detailed audit-report module.

It combines already-produced telemetry artifacts into one report.

## Test coverage

Tests cover:

- Combining metrics and event summaries.
- Report serialization.
- Nested output creation.
- Combined build-and-export flow.
- Missing and invalid source files.
- Invalid timestamps from the report clock.
- Export type and suffix validation.