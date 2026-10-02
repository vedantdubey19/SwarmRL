from typing import Any

from sensors.metrics import (
    MetricsTracker,
    SwarmMetrics,
    metrics_from_payload,
)
from sensors.stream import SwarmPayloadStream


class TelemetryPublisher:
    """Record swarm metrics and publish them to stream subscribers."""

    def __init__(
        self,
        tracker: MetricsTracker,
        stream: SwarmPayloadStream,
    ) -> None:
        if not isinstance(tracker, MetricsTracker):
            raise TypeError(
                "tracker must be a MetricsTracker instance."
            )

        if not isinstance(stream, SwarmPayloadStream):
            raise TypeError(
                "stream must be a SwarmPayloadStream instance."
            )

        self.tracker = tracker
        self.stream = stream

    async def publish_payload(
        self,
        payload: dict[str, Any],
        *,
        episode: int = 0,
    ) -> tuple[SwarmMetrics, int]:
        """Convert, record, and broadcast metrics from a swarm payload."""
        metrics = metrics_from_payload(
            payload,
            episode=episode,
        )

        self.tracker.record(
            step=metrics.step,
            episode=metrics.episode,
            explored_fraction=metrics.explored_fraction,
            agent_metrics=metrics.agent_metrics,
        )

        message = {
            "type": "swarm_metrics",
            "metrics": metrics.to_dict(),
        }

        delivered = await self.stream.publish(message)

        return metrics, delivered