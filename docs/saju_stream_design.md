# Saju Payload Stream Design

## Owner

Saju

## Day 8 objective

Provide an asynchronous in-memory broadcaster for JSON-compatible swarm
payloads.

This module is a reusable data layer. It is not the final FastAPI
WebSocket server.

## Main class

```python
SwarmPayloadStream
```

## Behavior

- Multiple consumers can subscribe.
- One published payload is delivered to every active subscriber.
- Subscribers are asynchronous generators.
- A bounded queue prevents unlimited memory growth.
- If a subscriber queue is full, its oldest queued payload is removed.
- The latest payload is retained for a slow subscriber.
- Closing the stream stops all subscribers.
- Publishing after close raises `StreamClosedError`.

## Usage

```python
stream = SwarmPayloadStream(max_queue_size=10)

async def consumer():
    async for payload in stream.subscribe():
        process(payload)

await stream.publish(payload)
await stream.close()
```

## Integration

Arya can connect a WebSocket client to the stream:

```text
stream.subscribe()
        ↓
websocket.send_json(payload)
```

The existing `build_swarm_payload()` function should create the payload
before publishing it.

## Responsibility boundary

This module does not:

- Start a web server.
- Accept WebSocket connections.
- Authenticate users.
- Run the reinforcement-learning environment.
- Modify the payload format.

Those responsibilities belong to the backend and integration layers.

## Testing

Tests verify:

- Empty stream state.
- Single subscriber delivery.
- Multiple subscriber delivery.
- Queue overflow behavior.
- Closing behavior.
- Invalid payload rejection.
- Context-manager cleanup.