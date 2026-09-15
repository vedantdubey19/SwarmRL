import numpy as np

from sensors.sensors import ConeSensor, SensorConfig


def test_sensor_detects_object_in_front():
    sensor = ConeSensor(
        SensorConfig(
            range=10.0,
            field_of_view=np.pi / 2,
        )
    )

    objects = [
        {
            "id": "target_1",
            "type": "target",
            "position": np.array([5.0, 0.0, 0.0]),
        }
    ]

    detections = sensor.detect(
        position=np.array([0.0, 0.0, 0.0]),
        heading=0.0,
        objects=objects,
    )

    assert len(detections) == 1
    assert detections[0]["id"] == "target_1"


def test_sensor_ignores_object_outside_range():
    sensor = ConeSensor(SensorConfig(range=5.0))

    objects = [
        {
            "id": "target_1",
            "type": "target",
            "position": np.array([10.0, 0.0, 0.0]),
        }
    ]

    detections = sensor.detect(
        position=np.zeros(3),
        heading=0.0,
        objects=objects,
    )

    assert detections == []


def test_sensor_vector_has_fixed_size():
    sensor = ConeSensor(SensorConfig(max_objects=8))

    vector = sensor.vectorize([])

    assert vector.shape == (24,)
    assert vector.dtype == np.float32