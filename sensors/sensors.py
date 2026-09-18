from dataclasses import dataclass

import numpy as np


@dataclass
class SensorConfig:
    range: float = 20.0
    field_of_view: float = np.pi / 2
    max_objects: int = 8

    def __post_init__(self) -> None:
        if self.range <= 0:
            raise ValueError("Sensor range must be positive.")

        if not 0 < self.field_of_view <= 2 * np.pi:
            raise ValueError(
                "Field of view must be between 0 and 2*pi."
            )

        if self.max_objects <= 0:
            raise ValueError(
                "Maximum object count must be positive."
            )


class ConeSensor:
    """Detect objects inside a drone's field of view."""

    def __init__(self, config: SensorConfig | None = None):
        self.config = config or SensorConfig()

    def detect(
        self,
        position: np.ndarray,
        heading: float,
        objects: list[dict],
    ) -> list[dict]:
        """Return visible objects sorted by increasing distance."""
        position = np.asarray(position, dtype=np.float32)

        if position.shape != (3,):
            raise ValueError(
                "Position must contain exactly three values: x, y, z."
            )

        forward = np.array(
            [np.cos(heading), 0.0, np.sin(heading)],
            dtype=np.float32,
        )

        detections = []

        for obj in objects:
            if "id" not in obj or "position" not in obj:
                raise ValueError(
                    "Each object must contain id and position."
                )

            object_position = np.asarray(
                obj["position"],
                dtype=np.float32,
            )

            if object_position.shape != (3,):
                raise ValueError(
                    "Object position must contain x, y, z."
                )

            relative = object_position - position
            distance = float(np.linalg.norm(relative))

            if distance <= 1e-8:
                continue

            if distance > self.config.range:
                continue

            direction = relative / distance
            cosine = float(
                np.clip(np.dot(forward, direction), -1.0, 1.0)
            )
            angle = float(np.arccos(cosine))

            if angle <= self.config.field_of_view / 2:
                detections.append(
                    {
                        "id": obj["id"],
                        "type": obj.get("type", "unknown"),
                        "distance": distance,
                        "angle": angle,
                    }
                )

        detections.sort(key=lambda item: item["distance"])

        return detections[: self.config.max_objects]

    def vectorize(self, detections: list[dict]) -> np.ndarray:
        """Convert detections into a fixed-size float vector."""
        object_types = {
            "target": 1.0,
            "obstacle": 2.0,
            "drone": 3.0,
            "unknown": 0.0,
        }

        values = []

        for detection in detections[: self.config.max_objects]:
            distance = float(detection["distance"])
            angle = float(detection["angle"])

            normalized_distance = float(
                np.clip(
                    distance / self.config.range,
                    0.0,
                    1.0,
                )
            )

            normalized_angle = float(
                np.clip(angle / np.pi, -1.0, 1.0)
            )

            values.extend(
                [
                    object_types.get(
                        detection.get("type", "unknown"),
                        0.0,
                    ),
                    normalized_distance,
                    normalized_angle,
                ]
            )

        output_size = self.config.max_objects * 3

        if len(values) < output_size:
            values.extend([0.0] * (output_size - len(values)))

        return np.asarray(
            values[:output_size],
            dtype=np.float32,
        )