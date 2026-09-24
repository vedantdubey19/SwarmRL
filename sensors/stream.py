import asyncio
from collections.abc import AsyncIterator
from typing import Any


class StreamClosedError(RuntimeError):
    """Raised when operating on a closed stream."""


class SwarmPayloadStream:
    """Broadcast JSON-compatible swarm payloads to subscribers."""

    def __init__(self, max_queue_size: int = 10):
        if max_queue_size <= 0:
            raise ValueError(
                "Maximum queue size must be positive."
            )

        self.max_queue_size = max_queue_size
        self._subscribers: set[
            asyncio.Queue[dict[str, Any] | None]
        ] = set()
        self._closed = False
        self._lock = asyncio.Lock()

    @property
    def subscriber_count(self) -> int:
        """Return the number of active subscribers."""
        return len(self._subscribers)

    @property
    def is_closed(self) -> bool:
        """Return whether the stream is closed."""
        return self._closed

    async def subscribe(self) -> AsyncIterator[dict[str, Any]]:
        """Yield published payloads until unsubscribed or closed."""
        if self._closed:
            raise StreamClosedError(
                "Cannot subscribe to a closed stream."
            )

        queue: asyncio.Queue[dict[str, Any] | None] = (
            asyncio.Queue(
                maxsize=self.max_queue_size
            )
        )

        async with self._lock:
            if self._closed:
                raise StreamClosedError(
                    "Cannot subscribe to a closed stream."
                )

            self._subscribers.add(queue)

        try:
            while True:
                payload = await queue.get()

                if payload is None:
                    break

                yield payload
        finally:
            async with self._lock:
                self._subscribers.discard(queue)

    async def publish(
        self,
        payload: dict[str, Any],
    ) -> int:
        """Publish a payload and return delivered subscriber count."""
        if self._closed:
            raise StreamClosedError(
                "Cannot publish to a closed stream."
            )

        if not isinstance(payload, dict):
            raise TypeError("Payload must be a dictionary.")

        async with self._lock:
            subscribers = list(self._subscribers)

        delivered = 0

        for queue in subscribers:
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass

            try:
                queue.put_nowait(payload)
                delivered += 1
            except asyncio.QueueFull:
                continue

        return delivered

    async def close(self) -> None:
        """Close the stream and stop all subscribers."""
        if self._closed:
            return

        self._closed = True

        async with self._lock:
            subscribers = list(self._subscribers)
            self._subscribers.clear()

        for queue in subscribers:
            while not queue.empty():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

            try:
                queue.put_nowait(None)
            except asyncio.QueueFull:
                pass

    async def __aenter__(self):
        if self._closed:
            raise StreamClosedError(
                "Cannot enter a closed stream."
            )

        return self

    async def __aexit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        await self.close()