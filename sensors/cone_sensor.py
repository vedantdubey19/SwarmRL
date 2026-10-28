from dataclasses import dataclass
import numpy as np


@dataclass
class ConeSensorConfig:
    range: float = 15.0
    half_angle: float = np.pi / 6.0  # 30 degrees
    max_objects: int = 8


class ConeSensor:
    def __init__(self, config: ConeSensorConfig | None = None):
        self.config = config or ConeSensorConfig()

    def detect(self, position: np.ndarray, heading: float, objects: list[dict]) -> list[dict]:
        """Detect visible objects within range and half-angle, sorted by distance."""
        pos = np.asarray(position, dtype=np.float32)
        forward = np.array([np.cos(heading), 0.0, np.sin(heading)], dtype=np.float32)
        detections = []

        type_map = {"target": 1.0, "obstacle": 2.0, "drone": 3.0}

        for obj in objects:
            obj_pos = np.asarray(obj["position"], dtype=np.float32)
            rel = obj_pos - pos
            dist = float(np.linalg.norm(rel))
            if dist <= 1e-6 or dist > self.config.range:
                continue

            horiz_dist = float(np.hypot(rel[0], rel[2]))
            if horiz_dist <= 1e-6:
                angle = 0.0
            else:
                cos_val = np.clip((forward[0] * rel[0] + forward[2] * rel[2]) / horiz_dist, -1.0, 1.0)
                angle = float(np.arccos(cos_val))

            if angle <= self.config.half_angle:
                bearing_x = rel[0] / dist
                bearing_y = rel[2] / dist
                obj_type = type_map.get(obj.get("type", ""), 0.0)
                detections.append({
                    "id": obj.get("id", ""),
                    "type": obj.get("type", ""),
                    "type_code": obj_type,
                    "distance": dist,
                    "bearing_x": float(bearing_x),
                    "bearing_y": float(bearing_y),
                    "angle": angle,
                })

        detections.sort(key=lambda d: d["distance"])
        return detections[:self.config.max_objects]

    def detect_batch(
        self,
        drone_positions: np.ndarray,  # (N, 3)
        drone_headings: np.ndarray,   # (N,)
        object_positions: np.ndarray, # (M, 3)
        object_types: np.ndarray,     # (M,) float32 codes: 1=target, 2=obstacle, 3=drone
    ) -> np.ndarray:
        """Vectorized detection of objects for N drones returning (N, 32) observations."""
        num_drones = drone_positions.shape[0]
        max_k = self.config.max_objects
        features_per_obj = 4
        output = np.zeros((num_drones, max_k * features_per_obj), dtype=np.float32)

        num_objects = object_positions.shape[0]
        if num_drones == 0 or num_objects == 0:
            return output

        # (N, M, 3)
        rel = object_positions[None, :, :] - drone_positions[:, None, :]
        dists = np.linalg.norm(rel, axis=2)  # (N, M)

        horiz_dists = np.hypot(rel[:, :, 0], rel[:, :, 2])
        safe_horiz = np.where(horiz_dists > 1e-6, horiz_dists, 1.0)

        fwd_x = np.cos(drone_headings)[:, None]  # (N, 1)
        fwd_z = np.sin(drone_headings)[:, None]  # (N, 1)

        dots = (fwd_x * rel[:, :, 0] + fwd_z * rel[:, :, 2]) / safe_horiz
        angles = np.where(horiz_dists > 1e-6, np.arccos(np.clip(dots, -1.0, 1.0)), 0.0)

        valid = (dists > 1e-5) & (dists <= self.config.range) & (angles <= self.config.half_angle)
        masked_dists = np.where(valid, dists, np.inf)

        k = min(max_k, num_objects)
        if num_objects > k:
            part_idx = np.argpartition(masked_dists, kth=k - 1, axis=1)[:, :k]
            part_dists = np.take_along_axis(masked_dists, part_idx, axis=1)
            order = np.argsort(part_dists, axis=1)
            sorted_idx = np.take_along_axis(part_idx, order, axis=1)
        else:
            sorted_idx = np.argsort(masked_dists, axis=1)[:, :k]

        top_dists = np.take_along_axis(masked_dists, sorted_idx, axis=1)
        top_valid = np.isfinite(top_dists)

        for slot in range(k):
            v = top_valid[:, slot]
            obj_idx = sorted_idx[:, slot]

            dist_val = np.where(v, top_dists[:, slot] / self.config.range, 0.0)
            chosen_rel = np.take_along_axis(rel, obj_idx[:, None, None], axis=1)[:, 0, :]
            safe_d = np.where(top_dists[:, slot:slot+1] > 1e-6, top_dists[:, slot:slot+1], 1.0)
            norm_rel = chosen_rel / safe_d

            bx = np.where(v, norm_rel[:, 0], 0.0)
            by = np.where(v, norm_rel[:, 2], 0.0)
            t_code = np.where(v, object_types[obj_idx], 0.0)

            base = slot * features_per_obj
            output[:, base] = dist_val
            output[:, base + 1] = bx
            output[:, base + 2] = by
            output[:, base + 3] = t_code

        return output
