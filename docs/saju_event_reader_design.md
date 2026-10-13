# Saju Telemetry Event Reader Design

## Owner

Saju

## Day 19 objective

Provide a reader for the JSON-lines files written by
`TelemetryEventLogger`.

The reader validates event records, supports focused filtering during
debugging, and generates simple event-frequency summaries for audits and
operational review.

## Main components

```python
TelemetryEventReader
TelemetryEventReadError
```

## Data flow

```text
TelemetryEventLogger
        ↓
telemetry_events.jsonl
        ↓
TelemetryEventReader
        ↓
Validated records, filters, and event summary
```

## Event record schema

The reader accepts records in this form:

```json
{
  "timestamp": "2026-10-03T10:00:00+00:00",
  "event": "service_started",
  "level": "info",
  "details": {
    "session_id": "run-001"
  }
}
```

## Validation

Each nonblank line must contain a JSON object with:

- A non-empty ISO-8601 timestamp including timezone information.
- A non-empty event string.
- One supported level: `debug`, `info`, `warning`, or `error`.
- A details object.

Timestamps are normalized to UTC in returned records.

Malformed input raises `TelemetryEventReadError` with a line number.

## Reading events

```python
reader = TelemetryEventReader(
    "output/telemetry_events.jsonl"
)

events = reader.read()
```

Events are returned in their original file order. Blank lines are
ignored.

## Filtering events

```python
errors = reader.filter(level="error")

recording_events = reader.filter(
    event="message_recorded",
)

recent_events = reader.filter(
    start=start_time,
    end=end_time,
)
```

Filters can be combined. Time filters must be timezone-aware datetimes,
and `start` cannot be later than `end`.

## Summary output

```python
summary = reader.summary()
```

Example result:

```python
{
  "total_events": 4,
  "by_event": {
    "message_recorded": 2,
    "service_started": 1,
    "message_failed": 1
  },
  "by_level": {
    "info": 2,
    "warning": 1,
    "error": 1
  }
}
```

## Responsibility boundary

This module does not:

- Write events.
- Start services or streams.
- Subscribe to telemetry.
- Modify event-log files.
- Configure global Python logging.
- Create dashboards.

It reads and analyzes completed event-log files.

## Test coverage

Tests cover:

- Ordered reading and UTC timestamp normalization.
- Blank-line handling.
- Event, level, and time-range filtering.
- Combined filters.
- Frequency summary generation.
- Path and missing-file validation.
- Malformed JSON and invalid schema handling.
- Invalid event/level/details fields.
- Invalid filter values and time ranges.