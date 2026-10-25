import asyncio

from sensors.consumer import TelemetryConsumer


class TelemetryServiceError(RuntimeError):
    """Raised when telemetry service lifecycle rules are violated."""


class TelemetryService:
    """Manage a background telemetry consumer task."""

    def __init__(
        self,
        consumer: TelemetryConsumer,
    ) -> None:
        if not isinstance(consumer, TelemetryConsumer):
            raise TypeError(
                "consumer must be a TelemetryConsumer instance."
            )

        self.consumer = consumer
        self._task: asyncio.Task[int] | None = None

    @property
    def is_running(self) -> bool:
        """Return whether the consumer task is currently active."""
        return self._task is not None and not self._task.done()

    @property
    def handled_count(self) -> int | None:
        """Return the completed task result when available."""
        if self._task is None or not self._task.done():
            return None

        if self._task.cancelled():
            return None

        return self._task.result()

    def start(self) -> asyncio.Task[int]:
        """Start the background consumer task."""
        if self.is_running:
            raise TelemetryServiceError(
                "Telemetry service is already running."
            )

        if self.consumer.stream.is_closed:
            raise TelemetryServiceError(
                "Cannot start service with a closed stream."
            )

        self._task = asyncio.create_task(
            self.consumer.consume()
        )

        return self._task

    async def wait(self) -> int:
        """Wait for the background consumer to finish."""
        if self._task is None:
            raise TelemetryServiceError(
                "Telemetry service has not been started."
            )

        return await self._task

    async def stop(
        self,
        *,
        timeout: float | None = None,
    ) -> int:
        """Close the stream and wait for the consumer to stop."""
        if self._task is None:
            raise TelemetryServiceError(
                "Telemetry service has not been started."
            )

        if timeout is not None and timeout <= 0:
            raise ValueError(
                "timeout must be positive when provided."
            )

        await self.consumer.stream.close()

        if timeout is None:
            return await self._task

        try:
            return await asyncio.wait_for(
                asyncio.shield(self._task),
                timeout=timeout,
            )
        except TimeoutError:
            self._task.cancel()

            try:
                await self._task
            except asyncio.CancelledError:
                pass

            raise