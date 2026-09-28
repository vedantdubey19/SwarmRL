# Saju Telemetry Consumer Design

## Owner

Saju

## Day 14 objective

Provide an asynchronous consumer that receives telemetry messages from
`SwarmPayloadStream`, validates their schema, and forwards valid messages
to an async handler.

The consumer is a reusable bridge between sensor-layer telemetry and a
future dashboard or WebSocket adapter.

## Main components

```python
TelemetryConsumer
TelemetryMessageError
```

## Data flow

```text
Simulation payload
        ↓
TelemetryPublisher
        ↓
SwarmPayloadStream
        ↓
TelemetryConsumer
        ↓
Async handler
        ↓
Future WebSocket or dashboard adapter
```

## Input message schema

The consumer accepts only this message structure:

```json
{
  "type": "swarm_metrics",
  "metrics": {
    "step": 7
  }
}
```

The full metrics dictionary can include active-agent count, explored-map
fraction, reward, collision totals, target totals, and per-agent metrics.

## Validation rules

A valid message must:

- Be a dictionary.
- Include `"type": "swarm_metrics"`.
- Include a dictionary under `"metrics"`.
- Include an integer `metrics["step"]`.
- Reject booleans as steps even though Python treats `bool` as an `int`
  subtype.

Invalid messages raise `TelemetryMessageError`.

## Usage

```python
async def dashboard_handler(message):
    await websocket.send_json(message)

consumer = TelemetryConsumer(
    stream=stream,
    handler=dashboard_handler,
)

handled = await consumer.consume()
```

`consume()` returns the number of messages successfully passed to the
handler.

To consume a fixed number of messages:

```python
handled = await consumer.consume(max_messages=10)
```

## Shutdown behavior

The consumer stops naturally when `SwarmPayloadStream.close()` is called.
If no message was handled before closure, `consume()` returns `0`.

## Error behavior

- `max_messages=0` or negative values raise `ValueError`.
- A non-stream input raises `TypeError`.
- A non-async handler raises `TypeError`.
- Invalid telemetry raises `TelemetryMessageError`.
- Handler exceptions intentionally propagate to the caller so backend
  code can log, retry, or close a failed connection.

## Responsibility boundary

This module does not:

- Start a FastAPI server.
- Create a WebSocket connection.
- Authenticate a user.
- Generate telemetry messages.
- Modify metrics or simulation payloads.
- Persist data to JSON or CSV files.

It only validates and forwards telemetry already published to the stream.

## Test coverage

Tests verify:

- Single-message consumption.
- Ordered multi-message consumption.
- Stream-close shutdown.
- Stream and handler type validation.
- Message-limit validation.
- Invalid message schema handling.
- Strict step validation.
- Handler exception propagation.