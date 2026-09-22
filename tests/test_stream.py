import asyncio

import pytest

from sensors.stream import (
    StreamClosedError,
    SwarmPayloadStream,
)


async def receive_one(stream, result):
    async for payload in stream.subscribe():
        result.append(payload)
        break


def test_stream_starts_empty():
    async def scenario():
        stream = SwarmPayloadStream()

        assert stream.subscriber_count == 0
        assert stream.is_closed is False

    asyncio.run(scenario())


def test_publish_delivers_payload_to_subscriber():
    async def scenario():
        stream = SwarmPayloadStream()
        received = []

        subscriber_task = asyncio.create_task(
            receive_one(stream, received)
        )

        await asyncio.sleep(0)
        assert stream.subscriber_count == 1

        payload = {
            "version": 1,
            "step": 1,
            "agents": [],
        }

        delivered = await stream.publish(payload)

        await subscriber_task
        await asyncio.sleep(0)

        assert delivered == 1
        assert received == [payload]
        assert stream.subscriber_count == 0

    asyncio.run(scenario())


def test_publish_supports_multiple_subscribers():
    async def scenario():
        stream = SwarmPayloadStream()
        first_received = []
        second_received = []

        first_task = asyncio.create_task(
            receive_one(stream, first_received)
        )
        second_task = asyncio.create_task(
            receive_one(stream, second_received)
        )

        await asyncio.sleep(0)
        assert stream.subscriber_count == 2

        payload = {
            "version": 1,
            "step": 5,
        }

        delivered = await stream.publish(payload)

        await asyncio.gather(
            first_task,
            second_task,
        )
        await asyncio.sleep(0)

        assert delivered == 2
        assert first_received == [payload]
        assert second_received == [payload]
        assert stream.subscriber_count == 0

    asyncio.run(scenario())


def test_latest_payload_replaces_oldest_when_queue_is_full():
    async def scenario():
        stream = SwarmPayloadStream(max_queue_size=1)
        received = []

        async def subscriber():
            async for payload in stream.subscribe():
                received.append(payload)
                if len(received) == 1:
                    break

        subscriber_task = asyncio.create_task(subscriber())

        await asyncio.sleep(0)
        assert stream.subscriber_count == 1

        first_payload = {"step": 1}
        second_payload = {"step": 2}

        await stream.publish(first_payload)
        await stream.publish(second_payload)

        await subscriber_task
        await asyncio.sleep(0)

        assert received == [second_payload]
        assert stream.subscriber_count == 0

    asyncio.run(scenario())


def test_close_stops_subscribers():
    async def scenario():
        stream = SwarmPayloadStream()
        received = []

        async def subscriber():
            async for payload in stream.subscribe():
                received.append(payload)

        subscriber_task = asyncio.create_task(subscriber())

        await asyncio.sleep(0)
        assert stream.subscriber_count == 1

        await stream.close()
        await subscriber_task
        await asyncio.sleep(0)

        assert stream.is_closed is True
        assert stream.subscriber_count == 0

    asyncio.run(scenario())


def test_publishing_after_close_raises_error():
    async def scenario():
        stream = SwarmPayloadStream()
        await stream.close()

        with pytest.raises(StreamClosedError):
            await stream.publish({"step": 1})

    asyncio.run(scenario())


def test_subscribing_after_close_raises_error():
    async def scenario():
        stream = SwarmPayloadStream()
        await stream.close()

        with pytest.raises(StreamClosedError):
            async for _ in stream.subscribe():
                pass

    asyncio.run(scenario())


def test_non_dictionary_payload_is_rejected():
    async def scenario():
        stream = SwarmPayloadStream()

        with pytest.raises(TypeError):
            await stream.publish(["invalid"])

    asyncio.run(scenario())


def test_invalid_queue_size_is_rejected():
    with pytest.raises(ValueError):
        SwarmPayloadStream(max_queue_size=0)


def test_context_manager_closes_stream():
    async def scenario():
        async with SwarmPayloadStream() as stream:
            assert stream.is_closed is False

        assert stream.is_closed is True

    asyncio.run(scenario())