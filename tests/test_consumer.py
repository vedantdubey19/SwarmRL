import asyncio

import pytest

from sensors.consumer import (
    TelemetryConsumer,
    TelemetryMessageError,
)
from sensors.metrics import MetricsTracker
from sensors.stream import SwarmPayloadStream
from sensors.telemetry import TelemetryPublisher


def make_payload(step: int = 1) -> dict:
    return {
        "step": step,
        "map": {
            "explored_fraction": 0.25,
        },
        "agents": [
            {
                "agent_id": "drone_000",
                "reward": 1.5,
                "visible_targets": 1,
                "visible_obstacles": 2,
                "visible_drones": 1,
                "reward_components": {
                    "new_area": 2,
                },
                "event_flags": {
                    "target_found": True,
                },
            }
        ],
    }


async def wait_for_subscriber(
    stream: SwarmPayloadStream,
) -> None:
    for _ in range(20):
        if stream.subscriber_count > 0:
            return

        await asyncio.sleep(0)

    raise AssertionError("Consumer did not subscribe to stream.")


def test_consumer_handles_one_valid_message():
    async def scenario():
        tracker = MetricsTracker()
        stream = SwarmPayloadStream()
        publisher = TelemetryPublisher(tracker, stream)
        received = []

        async def handler(message):
            received.append(message)

        consumer = TelemetryConsumer(stream, handler)

        task = asyncio.create_task(
            consumer.consume(max_messages=1)
        )

        await wait_for_subscriber(stream)

        metrics, delivered = await publisher.publish_payload(
            make_payload(step=7),
            episode=2,
        )

        handled = await task

        assert delivered == 1
        assert handled == 1
        assert received == [
            {
                "type": "swarm_metrics",
                "metrics": metrics.to_dict(),
            }
        ]

    asyncio.run(scenario())


def test_consumer_handles_multiple_messages_in_order():
    async def scenario():
        tracker = MetricsTracker()
        stream = SwarmPayloadStream()
        publisher = TelemetryPublisher(tracker, stream)
        received_steps = []

        async def handler(message):
            received_steps.append(
                message["metrics"]["step"]
            )

        consumer = TelemetryConsumer(stream, handler)

        task = asyncio.create_task(
            consumer.consume(max_messages=2)
        )

        await wait_for_subscriber(stream)

        await publisher.publish_payload(make_payload(1))
        await publisher.publish_payload(make_payload(2))

        handled = await task

        assert handled == 2
        assert received_steps == [1, 2]

    asyncio.run(scenario())


def test_consumer_returns_zero_when_stream_closes():
    async def scenario():
        stream = SwarmPayloadStream()
        received = []

        async def handler(message):
            received.append(message)

        consumer = TelemetryConsumer(stream, handler)

        task = asyncio.create_task(consumer.consume())

        await wait_for_subscriber(stream)
        await stream.close()

        handled = await task

        assert handled == 0
        assert received == []

    asyncio.run(scenario())


def test_invalid_stream_is_rejected():
    async def handler(message):
        return None

    with pytest.raises(TypeError):
        TelemetryConsumer(object(), handler)


def test_non_async_handler_is_rejected():
    def handler(message):
        return None

    with pytest.raises(TypeError):
        TelemetryConsumer(
            SwarmPayloadStream(),
            handler,
        )


def test_zero_max_messages_is_rejected():
    async def scenario():
        async def handler(message):
            return None

        consumer = TelemetryConsumer(
            SwarmPayloadStream(),
            handler,
        )

        with pytest.raises(ValueError):
            await consumer.consume(max_messages=0)

    asyncio.run(scenario())


def test_negative_max_messages_is_rejected():
    async def scenario():
        async def handler(message):
            return None

        consumer = TelemetryConsumer(
            SwarmPayloadStream(),
            handler,
        )

        with pytest.raises(ValueError):
            await consumer.consume(max_messages=-1)

    asyncio.run(scenario())


def test_invalid_message_type_is_rejected():
    async def scenario():
        stream = SwarmPayloadStream()

        async def handler(message):
            return None

        consumer = TelemetryConsumer(stream, handler)

        task = asyncio.create_task(
            consumer.consume(max_messages=1)
        )

        await wait_for_subscriber(stream)

        await stream.publish(
            {
                "type": "other",
                "metrics": {
                    "step": 1,
                },
            }
        )

        with pytest.raises(TelemetryMessageError):
            await task

    asyncio.run(scenario())


def test_missing_metrics_is_rejected():
    async def scenario():
        stream = SwarmPayloadStream()

        async def handler(message):
            return None

        consumer = TelemetryConsumer(stream, handler)

        task = asyncio.create_task(
            consumer.consume(max_messages=1)
        )

        await wait_for_subscriber(stream)

        await stream.publish(
            {
                "type": "swarm_metrics",
            }
        )

        with pytest.raises(TelemetryMessageError):
            await task

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "step",
    [
        None,
        "1",
        True,
    ],
)
def test_invalid_metrics_step_is_rejected(step):
    async def scenario():
        stream = SwarmPayloadStream()

        async def handler(message):
            return None

        consumer = TelemetryConsumer(stream, handler)

        task = asyncio.create_task(
            consumer.consume(max_messages=1)
        )

        await wait_for_subscriber(stream)

        await stream.publish(
            {
                "type": "swarm_metrics",
                "metrics": {
                    "step": step,
                },
            }
        )

        with pytest.raises(TelemetryMessageError):
            await task

    asyncio.run(scenario())


def test_handler_error_propagates():
    async def scenario():
        stream = SwarmPayloadStream()

        async def handler(message):
            raise RuntimeError("Dashboard handler failed.")

        consumer = TelemetryConsumer(stream, handler)

        task = asyncio.create_task(
            consumer.consume(max_messages=1)
        )

        await wait_for_subscriber(stream)

        await stream.publish(
            {
                "type": "swarm_metrics",
                "metrics": {
                    "step": 1,
                },
            }
        )

        with pytest.raises(
            RuntimeError,
            match="Dashboard handler failed.",
        ):
            await task

    asyncio.run(scenario())