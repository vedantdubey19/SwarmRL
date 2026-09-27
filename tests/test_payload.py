import json

import numpy as np
import pytest

from sensors.observation import (
    SensorObservation,
    build_sensor_observation,
)
from sensors.payload import (
    build_sensor_payload,
    build_swarm_payload,
    ensure_json_serializable,
    validate_event_flags,
)
from sensors.sensors import ConeSensor, SensorConfig


def make_observation(
    agent_id: str = "drone_000",
) -> SensorObservation:
    sensor = ConeSensor(
        SensorConfig(
            range=20.0,
            field_of_view=np.pi / 2,
            max_objects=4,
        )
    )

    objects = [
        {
            "id": "target_000",
            "type": "target",
            "position": np.array([5.0, 0.0, 0.0]),
        }
    ]

    return build_sensor_observation(
        agent_id=agent_id,
        position=np.array([1.0, 2.0, 3.0]),
        heading=0.0,
        objects=objects,
        sensor=sensor,
        explored_fraction=0.25,
    )


def test_validate_event_flags_returns_required_flags():
    flags = validate_event_flags(
        {
            "drone_collision": True,
            "obstacle_collision": False,
            "target_found": True,
            "boundary_violation": False,
        }
    )

    assert flags == {
        "boundary_violation": False,
        "drone_collision": True,
        "obstacle_collision": False,
        "target_found": True,
    }


def test_validate_event_flags_rejects_missing_flag():
    with pytest.raises(ValueError):
        validate_event_flags(
            {
                "drone_collision": False,
                "target_found": False,
                "boundary_violation": False,
            }
        )


def test_build_sensor_payload_contains_expected_fields():
    payload = build_sensor_payload(
        observation=make_observation(),
        reward=1.5,
        reward_components={
            "new_area": np.float32(2.0),
            "step_cost": -0.01,
        },
        event_flags={
            "drone_collision": False,
            "obstacle_collision": False,
            "target_found": True,
            "boundary_violation": False,
        },
        step=7,
        timestamp="2026-09-21T12:00:00+00:00",
    )

    assert payload["version"] == 1
    assert payload["agent_id"] == "drone_000"
    assert payload["step"] == 7
    assert payload["reward"] == pytest.approx(1.5)
    assert payload["visible_targets"] == 1
    assert payload["event_flags"]["target_found"] is True
    assert payload["timestamp"] == (
        "2026-09-21T12:00:00+00:00"
    )


def test_sensor_payload_is_json_serializable():
    payload = build_sensor_payload(
        observation=make_observation(),
        reward=np.float32(0.75),
        reward_components={
            "new_area": np.float32(1.0),
        },
        step=2,
    )

    encoded = ensure_json_serializable(payload)

    assert isinstance(encoded, str)
    assert json.loads(encoded)["agent_id"] == "drone_000"


def test_build_swarm_payload_contains_all_agents():
    observations = {
        "drone_000": make_observation("drone_000"),
        "drone_001": make_observation("drone_001"),
    }

    payload = build_swarm_payload(
        observations=observations,
        rewards={
            "drone_000": 1.0,
            "drone_001": -2.0,
        },
        reward_components={
            "drone_000": {"new_area": 1.0},
            "drone_001": {"collision": -100.0},
        },
        event_flags={
            "drone_000": {
                "drone_collision": False,
                "obstacle_collision": False,
                "target_found": True,
                "boundary_violation": False,
            },
            "drone_001": {
                "drone_collision": True,
                "obstacle_collision": False,
                "target_found": False,
                "boundary_violation": False,
            },
        },
        step=10,
        timestamp="2026-09-21T12:00:00+00:00",
        explored_fraction=0.4,
        explored_grid=np.array(
            [
                [1, 0],
                [0, 1],
            ],
            dtype=np.int8,
        ),
    )

    assert payload["version"] == 1
    assert payload["step"] == 10
    assert len(payload["agents"]) == 2
    assert payload["map"]["explored_fraction"] == 0.4
    assert payload["map"]["grid"] == [
        [1, 0],
        [0, 1],
    ]


def test_swarm_payload_is_json_serializable():
    observations = {
        "drone_000": make_observation("drone_000"),
    }

    payload = build_swarm_payload(
        observations=observations,
        explored_fraction=0.1,
    )

    encoded = ensure_json_serializable(payload)

    assert isinstance(encoded, str)
    assert len(json.loads(encoded)["agents"]) == 1


def test_negative_step_is_rejected():
    with pytest.raises(ValueError):
        build_sensor_payload(
            observation=make_observation(),
            step=-1,
        )


def test_invalid_explored_fraction_is_rejected():
    with pytest.raises(ValueError):
        build_swarm_payload(
            observations={
                "drone_000": make_observation(),
            },
            explored_fraction=1.1,
        )