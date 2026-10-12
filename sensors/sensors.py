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

            horiz_dist = float(np.hypot(relative[0], relative[2]))
            if horiz_dist <= 1e-8:
                angle = 0.0
            else:
                cosine = float(
                    np.clip(
                        (forward[0] * relative[0] + forward[2] * relative[2])
                        / horiz_dist,
                        -1.0,
                        1.0,
                    )
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

    def detect_and_vectorize_batch(
        self,
        agent_positions: np.ndarray,
        agent_headings: np.ndarray,
        object_positions: np.ndarray,
        object_type_codes: np.ndarray,
    ) -> np.ndarray:
        """Vectorized ConeSensor detection and feature encoding for N agents against M objects.

        Args:
            agent_positions: (N, 3) float32 array of active agent positions.
            agent_headings: (N,) float32 array of active agent headings in radians.
            object_positions: (M, 3) float32 array of candidate object positions.
            object_type_codes: (M,) float32 array of encoded object types (1=target, 2=obstacle, 3=drone).

        Returns:
            (N, max_objects * 3) float32 array of normalized sensor observations.
        """
        num_agents = agent_positions.shape[0]
        max_k = self.config.max_objects
        output = np.zeros((num_agents, max_k * 3), dtype=np.float32)

        if num_agents == 0 or object_positions.shape[0] == 0:
            return output

        # relative: (N, M, 3)
        relative = object_positions[None, :, :] - agent_positions[:, None, :]
        distances = np.linalg.norm(relative, axis=2)  # (N, M)

        # Horizontal bearing angle in x-z plane
        horiz_dists = np.hypot(relative[:, :, 0], relative[:, :, 2])  # (N, M)
        forward_x = np.cos(agent_headings)[:, None]  # (N, 1)
        forward_z = np.sin(agent_headings)[:, None]  # (N, 1)

        safe_horiz = np.where(horiz_dists > 1e-8, horiz_dists, 1.0)
        dots = (forward_x * relative[:, :, 0] + forward_z * relative[:, :, 2]) / safe_horiz
        cosines = np.clip(dots, -1.0, 1.0)
        angles = np.where(horiz_dists > 1e-8, np.arccos(cosines), 0.0)

        half_fov = self.config.field_of_view / 2.0
        valid_mask = (distances > 1e-8) & (distances <= self.config.range) & (angles <= half_fov)

        # Mask out invalid detections with +inf so sorting places valid nearest objects first
        masked_distances = np.where(valid_mask, distances, np.inf)
        num_objects = object_positions.shape[0]
        k = min(max_k, num_objects)

        if num_objects > k:
            part_idx = np.argpartition(masked_distances, kth=k - 1, axis=1)[:, :k]
            part_dists = np.take_along_axis(masked_distances, part_idx, axis=1)
            order = np.argsort(part_dists, axis=1)
            sorted_idx = np.take_along_axis(part_idx, order, axis=1)
        else:
            sorted_idx = np.argsort(masked_distances, axis=1)[:, :k]

        top_dists = np.take_along_axis(masked_distances, sorted_idx, axis=1)
        top_valid = np.isfinite(top_dists)
        top_angles = np.take_along_axis(angles, sorted_idx, axis=1)
        top_types = object_type_codes[sorted_idx]

        norm_dists = np.clip(top_dists / self.config.range, 0.0, 1.0)
        norm_angles = np.clip(top_angles / np.pi, -1.0, 1.0)

        for slot in range(k):
            v = top_valid[:, slot]
            base = slot * 3
            output[:, base] = np.where(v, top_types[:, slot], 0.0)
            output[:, base + 1] = np.where(v, norm_dists[:, slot], 0.0)
            output[:, base + 2] = np.where(v, norm_angles[:, slot], 0.0)

        return output

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