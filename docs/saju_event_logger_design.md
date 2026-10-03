# Saju Telemetry Event Logger Design

## Owner

Saju

## Day 18 objective

Provide a small, dependency-free event logger for telemetry lifecycle and
operational events.

The logger writes one structured JSON record per line, making it easy to
append during a run and inspect or process later.

## Main class

```python
TelemetryEventLogger
```

## Data flow

```text
TelemetryPublisher / TelemetryConsumer / TelemetryService
        ↓
TelemetryEventLogger
        ↓
telemetry_events.jsonl
```

## Event record schema

Each event is written as one JSON-lines record:

```json
{
  "timestamp": "2026-10-02T12:30:45+00:00",
  "event": "service_started",
  "level": "info",
  "details": {
    "session_id": "demo-001",
    "step": 4
  }
}
```

### Fields

- `timestamp`: timezone-aware UTC ISO-8601 timestamp.
- `event`: non-empty event name.
- `level`: one of `debug`, `info`, `warning`, or `error`.
- `details`: JSON-serializable contextual metadata.

## Usage

```python
from sensors.event_logger import TelemetryEventLogger

with TelemetryEventLogger(
    "output/telemetry_events.jsonl"
) as logger:
    logger.log(
        "service_started",
        details={"session_id": "run-001"},
    )

    logger.log(
        "message_recorded",
        details={"step": 42},
    )
```

## Lifecycle behavior

- `open()` creates parent directories and opens the event log in append mode.
- `log()` requires an open logger and flushes each written record.
- `close()` is safe to call more than once.
- The context manager opens and closes the file automatically.

## Validation

The logger rejects:

- Non-`.jsonl` output paths.
- Empty or non-string event names.
- Unsupported levels.
- Non-mapping details.
- Details that cannot be serialized as JSON.
- Clocks returning non-datetime or timezone-naive values.

## Responsibility boundary

This module does not:

- Configure Python's global logging system.
- Replace exception handling.
- Start services or streams.
- Subscribe to telemetry.
- Persist per-step metric CSV output.
- Generate session summaries.

It adds a compact operational event trail alongside the telemetry data
pipeline.

## Test coverage

Tests cover:

- JSON-lines output.
- Append behavior.
- Directory creation.
- Case-normalized levels.
- Open/close lifecycle behavior.
- Context manager cleanup.
- Input validation.
- JSON serialization checks.
- Clock validation.