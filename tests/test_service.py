import asyncio

import pytest

from sensors.consumer import TelemetryConsumer
from sensors.metrics import MetricsTracker
from sensors.service import (
    TelemetryService,
    TelemetryServiceError,
)
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

    raise AssertionError("Service did not subscribe to stream.")


def make_service(received: list[dict]) -> tuple[
    TelemetryService,
    TelemetryPublisher,
]:
    stream = SwarmPayloadStream()
    tracker = MetricsTracker()

    async def handler(message):
        received.append(message)

    consumer = TelemetryConsumer(stream, handler)
    publisher = TelemetryPublisher(tracker, stream)
    service = TelemetryService(consumer)

    return service, publisher


def test_service_starts_and_stops_cleanly():
    async def scenario():
        received = []
        service, publisher = make_service(received)

        task = service.start()

        assert task is not None
        assert service.is_running is True
        assert service.handled_count is None

        await wait_for_subscriber(service.consumer.stream)

        await publisher.publish_payload(make_payload(4))

        handled = await service.stop()

        assert handled == 1
        assert service.is_running is False
        assert service.handled_count == 1
        assert received[0]["metrics"]["step"] == 4

    asyncio.run(scenario())


def test_wait_returns_consumer_result_after_stream_close():
    async def scenario():
        received = []
        service, publisher = make_service(received)

        service.start()

        await wait_for_subscriber(service.consumer.stream)

        await publisher.publish_payload(make_payload(1))
        await publisher.publish_payload(make_payload(2))
        await service.consumer.stream.close()

        handled = await service.wait()

        assert handled == 2
        assert [message["metrics"]["step"] for message in received] == [
            1,
            2,
        ]

    asyncio.run(scenario())


def test_starting_twice_is_rejected():
    async def scenario():
        received = []
        service, _ = make_service(received)

        service.start()

        with pytest.raises(
            TelemetryServiceError,
            match="already running",
        ):
            service.start()

        await service.stop()

    asyncio.run(scenario())


def test_stop_before_start_is_rejected():
    async def scenario():
        received = []
        service, _ = make_service(received)

        with pytest.raises(
            TelemetryServiceError,
            match="has not been started",
        ):
            await service.stop()

    asyncio.run(scenario())


def test_wait_before_start_is_rejected():
    async def scenario():
        received = []
        service, _ = make_service(received)

        with pytest.raises(
            TelemetryServiceError,
            match="has not been started",
        ):
            await service.wait()

    asyncio.run(scenario())


def test_closed_stream_cannot_be_started():
    async def scenario():
        received = []
        service, _ = make_service(received)

        await service.consumer.stream.close()

        with pytest.raises(
            TelemetryServiceError,
            match="closed stream",
        ):
            service.start()

    asyncio.run(scenario())


def test_invalid_consumer_type_is_rejected():
    with pytest.raises(TypeError):
        TelemetryService(object())


def test_invalid_stop_timeout_is_rejected():
    async def scenario():
        received = []
        service, _ = make_service(received)

        service.start()

        with pytest.raises(ValueError):
            await service.stop(timeout=0)

        await service.stop()

    asyncio.run(scenario())


def test_handler_failure_propagates_from_wait():
    async def scenario():
        stream = SwarmPayloadStream()
        tracker = MetricsTracker()

        async def handler(message):
            raise RuntimeError("Dashboard delivery failed.")

        consumer = TelemetryConsumer(stream, handler)
        publisher = TelemetryPublisher(tracker, stream)
        service = TelemetryService(consumer)

        service.start()

        await wait_for_subscriber(stream)
        await publisher.publish_payload(make_payload())

        with pytest.raises(
            RuntimeError,
            match="Dashboard delivery failed.",
        ):
            await service.wait()

        assert service.is_running is False

    asyncio.run(scenario())


def test_handler_failure_propagates_from_stop():
    async def scenario():
        stream = SwarmPayloadStream()
        tracker = MetricsTracker()

        async def handler(message):
            raise RuntimeError("Dashboard delivery failed.")

        consumer = TelemetryConsumer(stream, handler)
        publisher = TelemetryPublisher(tracker, stream)
        service = TelemetryService(consumer)

        service.start()

        await wait_for_subscriber(stream)
        await publisher.publish_payload(make_payload())

        await asyncio.sleep(0)

        with pytest.raises(
            RuntimeError,
            match="Dashboard delivery failed.",
        ):
            await service.stop()

    asyncio.run(scenario())