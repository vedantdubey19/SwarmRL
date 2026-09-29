# Saju Telemetry Service Design

## Owner

Saju

## Day 15 objective

Provide a lifecycle manager for a background `TelemetryConsumer` task.

The service is a reusable boundary for a future backend. A dashboard or
WebSocket endpoint can start the service when it is ready to receive
telemetry and stop it during shutdown.

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
Future dashboard or WebSocket handler
```

## Main components

```python
TelemetryService
TelemetryServiceError
```

## Usage

```python
service = TelemetryService(consumer)

service.start()

# TelemetryPublisher publishes messages while the service runs.

handled = await service.stop()
```

`handled` is the number of telemetry messages successfully passed to the
consumer handler before shutdown.

## Lifecycle rules

- `start()` creates one background consumer task.
- Calling `start()` while the task is active raises
  `TelemetryServiceError`.
- `wait()` waits for the started task and returns its handled-message
  count.
- `stop()` closes the stream and waits for the consumer to finish.
- A closed stream cannot be used to start a service.
- `wait()` and `stop()` before `start()` raise
  `TelemetryServiceError`.

## Timeout behavior

```python
handled = await service.stop(timeout=5.0)
```

A timeout must be positive. If the consumer does not finish in time, the
service cancels its task, awaits cancellation cleanup, and raises
`TimeoutError`.

## Error behavior

Consumer validation failures and handler errors are not hidden. They
propagate through `wait()` and `stop()` so a backend can log them, retry
a connection, or notify the caller.

## Responsibility boundary

This service does not:

- Start FastAPI.
- Open or close real WebSocket connections.
- Authenticate users.
- Construct simulation payloads.
- Generate metrics.
- Persist telemetry records.

It only manages the lifecycle of the existing telemetry consumer task.

## Test coverage

Tests cover:

- Normal start, message handling, and stop.
- Waiting after the stream is closed.
- Duplicate start prevention.
- Invalid lifecycle calls.
- Closed stream rejection.
- Timeout validation.
- Consumer-handler failure propagation.