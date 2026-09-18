import json

import numpy as np
import pytest

from sensors.observation import (
    SensorObservation,
    build_sensor_observation,
)
from sensors.sensors import ConeSensor, SensorConfig


def test_observation_builds_from_visible_objects():
    sensor = ConeSensor(
        SensorConfig(
            range=20.0,
            field_of_view=np.pi / 2,
            max_objects=4,
        )
    )

    objects = [
        {
            "id": "target_001",
            "type": "target",
            "position": np.array([5.0, 0.0, 0.0]),
        },
        {
            "id": "obstacle_001",
            "type": "obstacle",
            "position": np.array([8.0, 0.0, 0.0]),
        },
    ]

    observation = build_sensor_observation(
        agent_id="drone_000",
        position=np.zeros(3),
        heading=0.0,
        objects=objects,
        sensor=sensor,
        explored_fraction=0.25,
    )

    assert observation.agent_id == "drone_000"
    assert len(observation.detections) == 2
    assert observation.explored_fraction == 0.25


def test_observation_vector_has_expected_size():
    sensor = ConeSensor(
        SensorConfig(
            max_objects=4,
        )
    )

    observation = SensorObservation(
        agent_id="drone_000",
        position=np.array([10.0, 2.0, -5.0]),
        heading=np.pi / 2,
        explored_fraction=0.5,
    )

    vector = observation.to_vector(sensor)

    expected_size = 6 + (4 * 3)

    assert vector.shape == (expected_size,)
    assert vector.dtype == np.float32


def test_observation_vector_contains_normalized_own_state():
    sensor = ConeSensor(
        SensorConfig(
            max_objects=1,
        )
    )

    observation = SensorObservation(
        agent_id="drone_000",
        position=np.array([25.0, 5.0, -25.0]),
        heading=0.0,
        explored_fraction=0.4,
    )

    vector = observation.to_vector(sensor)

    assert vector[0] == pytest.approx(0.5)
    assert vector[1] == pytest.approx(0.5)
    assert vector[2] == pytest.approx(-0.5)
    assert vector[3] == pytest.approx(0.0)
    assert vector[4] == pytest.approx(1.0)
    assert vector[5] == pytest.approx(0.4)


def test_observation_to_dict_is_json_serializable():
    sensor = ConeSensor(
        SensorConfig(
            max_objects=4,
        )
    )

    objects = [
        {
            "id": "target_001",
            "type": "target",
            "position": np.array([5.0, 0.0, 0.0]),
        }
    ]

    observation = build_sensor_observation(
        agent_id="drone_000",
        position=np.zeros(3),
        heading=0.0,
        objects=objects,
        sensor=sensor,
        explored_fraction=0.25,
    )

    payload = observation.to_dict()
    encoded = json.dumps(payload)

    assert isinstance(encoded, str)
    assert payload["agent_id"] == "drone_000"
    assert payload["visible_targets"] == 1
    assert payload["visible_obstacles"] == 0
    assert payload["visible_drones"] == 0


def test_observation_rejects_invalid_position():
    with pytest.raises(ValueError):
        SensorObservation(
            agent_id="drone_000",
            position=np.array([1.0, 2.0]),
            heading=0.0,
        )


def test_observation_rejects_invalid_explored_fraction():
    with pytest.raises(ValueError):
        SensorObservation(
            agent_id="drone_000",
            position=np.zeros(3),
            heading=0.0,
            explored_fraction=1.5,
        )


def test_observation_rejects_empty_agent_id():
    with pytest.raises(ValueError):
        SensorObservation(
            agent_id="",
            position=np.zeros(3),
            heading=0.0,
        )