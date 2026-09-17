from dataclasses import dataclass, field

import numpy as np

from sensors.sensors import ConeSensor


@dataclass
class SensorObservation:
    """Combined sensor output for one drone."""

    agent_id: str
    position: np.ndarray
    heading: float
    detections: list[dict] = field(default_factory=list)
    explored_fraction: float = 0.0

    def __post_init__(self) -> None:
        self.position = np.asarray(
            self.position,
            dtype=np.float32,
        )

        if self.position.shape != (3,):
            raise ValueError(
                "Position must contain exactly three values: x, y, z."
            )

        if not self.agent_id:
            raise ValueError("Agent ID must not be empty.")

        if not 0.0 <= self.explored_fraction <= 1.0:
            raise ValueError(
                "Explored fraction must be between 0 and 1."
            )

    def to_vector(self, sensor: ConeSensor) -> np.ndarray:
        """Return the fixed-size RL sensor vector."""
        sensor_vector = sensor.vectorize(self.detections)

        own_state = np.asarray(
            [
                self.position[0] / 50.0,
                self.position[1] / 10.0,
                self.position[2] / 50.0,
                np.sin(self.heading),
                np.cos(self.heading),
                self.explored_fraction,
            ],
            dtype=np.float32,
        )

        return np.concatenate(
            [own_state, sensor_vector]
        ).astype(np.float32)

    def to_dict(self) -> dict:
        """Return a JSON-friendly sensor summary."""
        serialized_detections = []

        for detection in self.detections:
            serialized_detections.append(
                {
                    "id": str(detection["id"]),
                    "type": str(
                        detection.get("type", "unknown")
                    ),
                    "distance": float(
                        detection["distance"]
                    ),
                    "angle": float(
                        detection["angle"]
                    ),
                }
            )

        return {
            "agent_id": self.agent_id,
            "position": {
                "x": float(self.position[0]),
                "y": float(self.position[1]),
                "z": float(self.position[2]),
            },
            "heading": float(self.heading),
            "explored_fraction": float(
                self.explored_fraction
            ),
            "detections": serialized_detections,
            "visible_targets": sum(
                detection["type"] == "target"
                for detection in self.detections
            ),
            "visible_obstacles": sum(
                detection["type"] == "obstacle"
                for detection in self.detections
            ),
            "visible_drones": sum(
                detection["type"] == "drone"
                for detection in self.detections
            ),
        }


def build_sensor_observation(
    agent_id: str,
    position: np.ndarray,
    heading: float,
    objects: list[dict],
    sensor: ConeSensor,
    explored_fraction: float = 0.0,
) -> SensorObservation:
    """Detect objects and build a complete observation."""
    detections = sensor.detect(
        position=position,
        heading=heading,
        objects=objects,
    )

    return SensorObservation(
        agent_id=agent_id,
        position=position,
        heading=heading,
        detections=detections,
        explored_fraction=explored_fraction,
    )