import numpy as np
import pytest

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
    assert detections[0]["type"] == "target"


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


def test_sensor_ignores_object_behind_drone():
    sensor = ConeSensor(
        SensorConfig(
            range=10.0,
            field_of_view=np.pi / 2,
        )
    )

    objects = [
        {
            "id": "target_behind",
            "type": "target",
            "position": np.array([-5.0, 0.0, 0.0]),
        }
    ]

    detections = sensor.detect(
        position=np.zeros(3),
        heading=0.0,
        objects=objects,
    )

    assert detections == []


def test_sensor_ignores_object_outside_field_of_view():
    sensor = ConeSensor(
        SensorConfig(
            range=10.0,
            field_of_view=np.pi / 2,
        )
    )

    objects = [
        {
            "id": "target_side",
            "type": "target",
            "position": np.array([5.0, 0.0, 5.0]),
        }
    ]

    detections = sensor.detect(
        position=np.zeros(3),
        heading=0.0,
        objects=objects,
    )

    assert detections == []


def test_sensor_returns_nearest_objects_first():
    sensor = ConeSensor(
        SensorConfig(
            range=20.0,
            field_of_view=np.pi / 2,
            max_objects=3,
        )
    )

    objects = [
        {
            "id": "far",
            "type": "target",
            "position": np.array([10.0, 0.0, 0.0]),
        },
        {
            "id": "near",
            "type": "target",
            "position": np.array([2.0, 0.0, 0.0]),
        },
    ]

    detections = sensor.detect(
        position=np.zeros(3),
        heading=0.0,
        objects=objects,
    )

    assert [item["id"] for item in detections] == [
        "near",
        "far",
    ]


def test_sensor_limits_number_of_detections():
    sensor = ConeSensor(
        SensorConfig(
            range=20.0,
            field_of_view=np.pi / 2,
            max_objects=2,
        )
    )

    objects = [
        {
            "id": f"target_{index}",
            "type": "target",
            "position": np.array(
                [float(index + 1), 0.0, 0.0]
            ),
        }
        for index in range(5)
    ]

    detections = sensor.detect(
        position=np.zeros(3),
        heading=0.0,
        objects=objects,
    )

    assert len(detections) == 2
    assert [item["id"] for item in detections] == [
        "target_0",
        "target_1",
    ]


def test_sensor_vector_has_fixed_size():
    sensor = ConeSensor(SensorConfig(max_objects=8))

    vector = sensor.vectorize([])

    assert vector.shape == (24,)
    assert vector.dtype == np.float32
    assert np.all(vector == 0.0)


def test_sensor_vector_contains_normalized_values():
    sensor = ConeSensor(
        SensorConfig(
            range=10.0,
            max_objects=1,
        )
    )

    vector = sensor.vectorize(
        [
            {
                "id": "target_1",
                "type": "target",
                "distance": 5.0,
                "angle": np.pi / 2,
            }
        ]
    )

    assert vector.shape == (3,)
    assert vector[0] == pytest.approx(1.0)
    assert vector[1] == pytest.approx(0.5)
    assert vector[2] == pytest.approx(0.5)


def test_sensor_clips_out_of_range_vector_values():
    sensor = ConeSensor(
        SensorConfig(
            range=10.0,
            max_objects=1,
        )
    )

    vector = sensor.vectorize(
        [
            {
                "id": "target_1",
                "type": "target",
                "distance": 100.0,
                "angle": 10.0,
            }
        ]
    )

    assert vector[1] == pytest.approx(1.0)
    assert vector[2] == pytest.approx(1.0)


def test_invalid_sensor_range_raises_error():
    with pytest.raises(ValueError):
        SensorConfig(range=0.0)


def test_invalid_field_of_view_raises_error():
    with pytest.raises(ValueError):
        SensorConfig(field_of_view=0.0)


def test_invalid_max_objects_raises_error():
    with pytest.raises(ValueError):
        SensorConfig(max_objects=0)


def test_invalid_drone_position_raises_error():
    sensor = ConeSensor()

    with pytest.raises(ValueError):
        sensor.detect(
            position=np.array([0.0, 0.0]),
            heading=0.0,
            objects=[],
        )


def test_invalid_object_position_raises_error():
    sensor = ConeSensor()

    objects = [
        {
            "id": "bad_object",
            "type": "target",
            "position": np.array([1.0, 2.0]),
        }
    ]

    with pytest.raises(ValueError):
        sensor.detect(
            position=np.zeros(3),
            heading=0.0,
            objects=objects,
        )