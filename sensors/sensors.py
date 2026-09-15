from dataclasses import dataclass

import numpy as np


@dataclass
class SensorConfig:
    range: float = 20.0
    field_of_view: float = np.pi / 2
    max_objects: int = 8


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
        position = np.asarray(position, dtype=np.float32)

        forward = np.array(
            [np.cos(heading), 0.0, np.sin(heading)],
            dtype=np.float32,
        )

        detections = []

        for obj in objects:
            object_position = np.asarray(
                obj["position"],
                dtype=np.float32,
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
        object_types = {
            "target": 1.0,
            "obstacle": 2.0,
            "drone": 3.0,
            "unknown": 0.0,
        }

        values = []

        for detection in detections:
            values.extend(
                [
                    object_types.get(detection["type"], 0.0),
                    detection["distance"] / self.config.range,
                    detection["angle"] / np.pi,
                ]
            )

        output_size = self.config.max_objects * 3

        if len(values) < output_size:
            values.extend([0.0] * (output_size - len(values)))

        return np.asarray(values[:output_size], dtype=np.float32)