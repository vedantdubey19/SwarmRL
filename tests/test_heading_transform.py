import numpy as np
import pytest

from sensors.sensors import ConeSensor, SensorConfig


def heading_to_three_rotation_y(heading: float) -> float:
    return -heading + (np.pi / 2.0)


def compute_three_forward(rotation_y: float) -> np.ndarray:
    return np.array([np.sin(rotation_y), 0.0, np.cos(rotation_y)], dtype=np.float32)


def test_heading_transform_matches_cone_sensor_detections():
    sensor = ConeSensor(SensorConfig(range=20.0, field_of_view=np.pi / 2.0))
    drone_pos = np.array([0.0, 5.0, 0.0], dtype=np.float32)

    test_angles = [0.0, np.pi / 4, np.pi / 2, (3 * np.pi) / 4, np.pi, -np.pi / 2, -np.pi / 4]

    for heading in test_angles:
        # Sensor forward vector in horizontal X-Z plane
        sensor_dir = np.array([np.cos(heading), 0.0, np.sin(heading)], dtype=np.float32)

        # Three.js render forward vector after rotation.y = -heading + pi/2
        rot_y = heading_to_three_rotation_y(heading)
        render_forward = compute_three_forward(rot_y)

        # Assert identical direction
        np.testing.assert_allclose(
            sensor_dir,
            render_forward,
            atol=1e-6,
            err_msg=f"Direction mismatch at heading {heading}",
        )

        # Place target directly along forward vector at 10m
        target_pos = drone_pos + sensor_dir * 10.0
        detections = sensor.detect(
            drone_pos,
            heading,
            [{"id": "t1", "type": "target", "position": target_pos}],
        )

        assert len(detections) == 1
        assert detections[0]["id"] == "t1"
        assert detections[0]["distance"] == pytest.approx(10.0, abs=1e-3)
        assert detections[0]["angle"] == pytest.approx(0.0, abs=1e-3)

