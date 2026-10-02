# Saju Telemetry Publishing Design

## Owner

Saju

## Day 13 objective

Connect the existing metric-conversion, metric-tracking, and asynchronous
streaming layers without introducing a web-server dependency.

## Main class

```python
TelemetryPublisher
```

## Data flow

```text
Swarm simulation payload
        ↓
metrics_from_payload()
        ↓
SwarmMetrics
        ↓
MetricsTracker.record()
        ↓
SwarmPayloadStream.publish()
        ↓
Dashboard or WebSocket adapter
```

## Published message format

```json
{
  "type": "swarm_metrics",
  "metrics": {
    "step": 7,
    "episode": 0,
    "active_agents": 2,
    "explored_fraction": 0.35
  }
}
```

The complete `SwarmMetrics.to_dict()` result is published under `metrics`.

## Usage

```python
tracker = MetricsTracker()
stream = SwarmPayloadStream()

publisher = TelemetryPublisher(
    tracker=tracker,
    stream=stream,
)

metrics, delivered = await publisher.publish_payload(
    simulation_payload,
    episode=0,
)
```

`metrics` is the recorded `SwarmMetrics` object. `delivered` is the
number of active stream subscribers that received the message.

## Responsibility boundary

The telemetry publisher:

- Converts a simulation payload into metrics.
- Stores metrics in `MetricsTracker`.
- Publishes a JSON-compatible metrics message.
- Uses `SwarmPayloadStream` for asynchronous fan-out.

The telemetry publisher does not:

- Start FastAPI or a WebSocket server.
- Build or modify the original simulation payload.
- Persist exported metric files.
- Run the reinforcement-learning environment.
- Authenticate dashboard users.

A future backend layer can subscribe to the stream and forward each
message through WebSockets.

## Validation and failure behavior

- Invalid payloads use the validation rules of `metrics_from_payload`.
- A closed stream raises `StreamClosedError`.
- The metric record is stored before broadcast is attempted.
- Constructor arguments must be `MetricsTracker` and
  `SwarmPayloadStream` instances.

## Test coverage

Tests verify:

- Payload conversion to `SwarmMetrics`.
- Tracking of the recorded metric step.
- Delivery to one subscriber.
- Delivery to multiple subscribers.
- JSON serialization of published telemetry.
- Invalid-payload handling.
- Closed-stream behavior.
- Constructor type validation.