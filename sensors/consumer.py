from collections.abc import Awaitable, Callable
from inspect import iscoroutinefunction
from typing import Any

from sensors.stream import SwarmPayloadStream


TelemetryHandler = Callable[
    [dict[str, Any]],
    Awaitable[None],
]


class TelemetryMessageError(ValueError):
    """Raised when a stream message is not valid telemetry."""


class TelemetryConsumer:
    """Consume validated swarm-metrics telemetry messages."""

    def __init__(
        self,
        stream: SwarmPayloadStream,
        handler: TelemetryHandler,
    ) -> None:
        if not isinstance(stream, SwarmPayloadStream):
            raise TypeError(
                "stream must be a SwarmPayloadStream instance."
            )

        if not iscoroutinefunction(handler):
            raise TypeError(
                "handler must be an async callable."
            )

        self.stream = stream
        self.handler = handler

    @staticmethod
    def validate_message(
        message: dict[str, Any],
    ) -> None:
        """Validate the expected swarm-metrics telemetry schema."""
        if not isinstance(message, dict):
            raise TelemetryMessageError(
                "Telemetry message must be a dictionary."
            )

        if message.get("type") != "swarm_metrics":
            raise TelemetryMessageError(
                "Telemetry message type must be 'swarm_metrics'."
            )

        metrics = message.get("metrics")

        if not isinstance(metrics, dict):
            raise TelemetryMessageError(
                "Telemetry message metrics must be a dictionary."
            )

        step = metrics.get("step")

        if isinstance(step, bool) or not isinstance(step, int):
            raise TelemetryMessageError(
                "Telemetry metrics step must be an integer."
            )

    async def consume(
        self,
        *,
        max_messages: int | None = None,
    ) -> int:
        """Handle stream messages until closed or the limit is reached."""
        if max_messages is not None and max_messages <= 0:
            raise ValueError(
                "max_messages must be positive when provided."
            )

        handled = 0

        async for message in self.stream.subscribe():
            self.validate_message(message)
            await self.handler(message)

            handled += 1

            if (
                max_messages is not None
                and handled >= max_messages
            ):
                break

        return handled