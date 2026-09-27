import asyncio
import json

import pytest

from sensors.metrics import MetricsTracker, SwarmMetrics
from sensors.stream import (
    StreamClosedError,
    SwarmPayloadStream,
)
from sensors.telemetry import TelemetryPublisher


def make_payload() -> dict:
    return {
        "step": 7,
        "map": {
            "explored_fraction": 0.35,
        },
        "agents": [
            {
                "agent_id": "drone_000",
                "reward": 2.5,
                "visible_targets": 1,
                "visible_obstacles": 2,
                "visible_drones": 1,
                "reward_components": {
                    "new_area": 3,
                },
                "event_flags": {
                    "target_found": True,
                },
            },
            {
                "agent_id": "drone_001",
                "reward": -1.0,
                "visible_targets": 0,
                "visible_obstacles": 1,
                "visible_drones": 1,
                "reward_components": {
                    "new_area": 1,
                },
                "event_flags": {
                    "drone_collision": True,
                },
            },
        ],
    }


async def receive_one(
    stream: SwarmPayloadStream,
    received: list[dict],
) -> None:
    async for message in stream.subscribe():
        received.append(message)
        break


def test_publish_payload_records_metrics_and_notifies_subscriber():
    async def scenario():
        tracker = MetricsTracker()
        stream = SwarmPayloadStream()
        publisher = TelemetryPublisher(
            tracker,
            stream,
        )
        received = []

        subscriber_task = asyncio.create_task(
            receive_one(stream, received)
        )

        await asyncio.sleep(0)

        metrics, delivered = await publisher.publish_payload(
            make_payload(),
            episode=2,
        )

        await subscriber_task
        await asyncio.sleep(0)

        assert isinstance(metrics, SwarmMetrics)
        assert metrics.step == 7
        assert metrics.episode == 2
        assert delivered == 1
        assert tracker.total_steps == 1
        assert tracker.latest == metrics
        assert received == [
            {
                "type": "swarm_metrics",
                "metrics": metrics.to_dict(),
            }
        ]

    asyncio.run(scenario())


def test_publish_payload_notifies_multiple_subscribers():
    async def scenario():
        tracker = MetricsTracker()
        stream = SwarmPayloadStream()
        publisher = TelemetryPublisher(
            tracker,
            stream,
        )

        first_received = []
        second_received = []

        first_task = asyncio.create_task(
            receive_one(stream, first_received)
        )
        second_task = asyncio.create_task(
            receive_one(stream, second_received)
        )

        await asyncio.sleep(0)

        metrics, delivered = await publisher.publish_payload(
            make_payload()
        )

        await asyncio.gather(
            first_task,
            second_task,
        )

        expected = {
            "type": "swarm_metrics",
            "metrics": metrics.to_dict(),
        }

        assert delivered == 2
        assert first_received == [expected]
        assert second_received == [expected]

    asyncio.run(scenario())


def test_telemetry_message_is_json_serializable():
    async def scenario():
        tracker = MetricsTracker()
        stream = SwarmPayloadStream()
        publisher = TelemetryPublisher(
            tracker,
            stream,
        )
        received = []

        subscriber_task = asyncio.create_task(
            receive_one(stream, received)
        )

        await asyncio.sleep(0)

        await publisher.publish_payload(make_payload())

        await subscriber_task

        encoded = json.dumps(received[0])
        decoded = json.loads(encoded)

        assert decoded["type"] == "swarm_metrics"
        assert decoded["metrics"]["step"] == 7
        assert decoded["metrics"]["active_agents"] == 2

    asyncio.run(scenario())


def test_invalid_payload_missing_step_is_rejected():
    async def scenario():
        publisher = TelemetryPublisher(
            MetricsTracker(),
            SwarmPayloadStream(),
        )

        with pytest.raises(ValueError):
            await publisher.publish_payload(
                {
                    "agents": [],
                }
            )

    asyncio.run(scenario())


def test_closed_stream_raises_error_after_metrics_conversion():
    async def scenario():
        tracker = MetricsTracker()
        stream = SwarmPayloadStream()
        publisher = TelemetryPublisher(
            tracker,
            stream,
        )

        await stream.close()

        with pytest.raises(StreamClosedError):
            await publisher.publish_payload(make_payload())

        assert tracker.total_steps == 1

    asyncio.run(scenario())


def test_rejects_invalid_tracker_type():
    with pytest.raises(TypeError):
        TelemetryPublisher(
            tracker=object(),
            stream=SwarmPayloadStream(),
        )


def test_rejects_invalid_stream_type():
    with pytest.raises(TypeError):
        TelemetryPublisher(
            tracker=MetricsTracker(),
            stream=object(),
        )