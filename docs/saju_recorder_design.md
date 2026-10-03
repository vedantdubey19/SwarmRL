# Saju Telemetry Recorder Design

## Owner

Saju

## Day 16 objective

Provide a reusable async handler that persists validated telemetry
messages to disk for offline analysis, training logs, and audit evidence.

The recorder is intended to be used as the handler for
`TelemetryConsumer` or `TelemetryService`.

## Main class

```python
TelemetryRecorder
```

## Data flow

```text
TelemetryPublisher
        ↓
SwarmPayloadStream
        ↓
TelemetryConsumer
        ↓
TelemetryService
        ↓
TelemetryRecorder
        ↓
JSON-lines and CSV files
```

## Output formats

### JSON-lines

Each telemetry message is written as one compact JSON object followed by
a newline:

```json
{"type":"swarm_metrics","metrics":{"step":1}}
```

This format is easy to stream, append to, and parse incrementally.

### CSV

When a CSV path is provided, the recorder writes one row per message
using a fixed schema:

- step
- episode
- active_agents
- explored_fraction
- total_reward
- mean_reward
- newly_explored_cells
- drone_collisions
- obstacle_collisions
- targets_found
- boundary_violations
- visible_targets
- visible_obstacles
- visible_drones

The header is written once when the file is first created.

## Usage

```python
from pathlib import Path
from sensors.recorder import TelemetryRecorder

recorder = TelemetryRecorder(
    Path("output/metrics.jsonl"),
    csv_path=Path("output/metrics.csv"),
)

recorder.open()

recorder.record(telemetry_message)

recorder.close()
```

Or with a context manager:

```python
with TelemetryRecorder("output/metrics.jsonl") as recorder:
    recorder.record(telemetry_message)
```

## Integration

A typical integration looks like:

```python
recorder = TelemetryRecorder("output/metrics.jsonl")
recorder.open()

consumer = TelemetryConsumer(
    stream=stream,
    handler=recorder.record,
)

service = TelemetryService(consumer)

service.start()
# ... simulation runs ...
await service.stop()

recorder.close()
```

## Validation and error behavior

The recorder validates messages defensively:

- Message must be a mapping.
- `type` must be `"swarm_metrics"`.
- `metrics` must be a mapping.
- `metrics["step"]` must be an integer, not a boolean.

Invalid messages raise `TelemetryMessageError`.

The recorder must be opened before recording. Using it unopened or
double-opening raises `RuntimeError`.

## Responsibility boundary

This module does not:

- Start FastAPI or any web server.
- Create WebSocket connections.
- Authenticate users.
- Modify simulation payloads.
- Generate metrics.
- Run the reinforcement-learning environment.

It only persists telemetry messages that are already validated by the
consumer or service layer.

## Test coverage

Tests verify:

- JSON-lines output.
- Appending to existing files.
- CSV output with correct schema.
- Parent directory creation.
- Suffix validation for JSON and CSV paths.
- Message validation rules.
- Open/close lifecycle rules.
- Context-manager usage.
- CSV header written only once.