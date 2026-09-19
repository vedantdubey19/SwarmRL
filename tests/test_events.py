import numpy as np
import pytest

from sensors.events import (
    EventConfig,
    build_event_flags,
    detect_boundary_violations,
    detect_drone_collisions,
    detect_obstacle_collisions,
    detect_targets_found,
    distance_between,
)


def test_distance_between_positions():
    first = np.array([0.0, 0.0, 0.0])
    second = np.array([3.0, 4.0, 0.0])

    assert distance_between(first, second) == pytest.approx(5.0)


def test_drone_collision_returns_both_agents():
    positions = {
        "drone_000": np.array([0.0, 0.0, 0.0]),
        "drone_001": np.array([1.0, 0.0, 0.0]),
        "drone_002": np.array([10.0, 0.0, 0.0]),
    }

    collisions = detect_drone_collisions(
        positions,
        collision_distance=2.0,
    )

    assert collisions == {"drone_000", "drone_001"}


def test_drone_at_threshold_is_not_collision():
    positions = {
        "drone_000": np.array([0.0, 0.0, 0.0]),
        "drone_001": np.array([2.0, 0.0, 0.0]),
    }

    collisions = detect_drone_collisions(
        positions,
        collision_distance=2.0,
    )

    assert collisions == set()


def test_obstacle_collision_includes_obstacle_radius():
    drone_positions = {
        "drone_000": np.array([2.5, 0.0, 0.0]),
        "drone_001": np.array([10.0, 0.0, 0.0]),
    }

    obstacles = [
        {
            "id": "obstacle_000",
            "position": np.array([0.0, 0.0, 0.0]),
            "radius": 2.0,
        }
    ]

    collisions = detect_obstacle_collisions(
        drone_positions=drone_positions,
        obstacles=obstacles,
        collision_distance=1.0,
    )

    assert collisions == {"drone_000"}


def test_target_detection_returns_drone_id():
    drone_positions = {
        "drone_000": np.array([2.0, 0.0, 0.0]),
        "drone_001": np.array([20.0, 0.0, 0.0]),
    }

    targets = [
        {
            "id": "target_000",
            "position": np.array([0.0, 0.0, 0.0]),
        }
    ]

    found = detect_targets_found(
        drone_positions=drone_positions,
        targets=targets,
        detection_distance=3.0,
    )

    assert found == {"drone_000"}


def test_boundary_violation_detected():
    positions = {
        "drone_inside": np.array([0.0, 0.0, 0.0]),
        "drone_outside": np.array([11.0, 0.0, 0.0]),
    }

    violations = detect_boundary_violations(
        positions=positions,
        world_min=np.array([-10.0, -10.0, -10.0]),
        world_max=np.array([10.0, 10.0, 10.0]),
    )

    assert violations == {"drone_outside"}


def test_boundary_minimum_and_maximum_are_inclusive():
    positions = {
        "drone_min": np.array([-10.0, -10.0, -10.0]),
        "drone_max": np.array([10.0, 10.0, 10.0]),
    }

    violations = detect_boundary_violations(
        positions=positions,
        world_min=np.array([-10.0, -10.0, -10.0]),
        world_max=np.array([10.0, 10.0, 10.0]),
    )

    assert violations == set()


def test_build_event_flags_for_one_drone():
    positions = {
        "drone_000": np.array([0.5, 0.0, 0.0]),
        "drone_001": np.array([1.0, 0.0, 0.0]),
    }

    obstacles = [
        {
            "id": "obstacle_000",
            "position": np.array([0.0, 0.0, 0.0]),
            "radius": 0.0,
        }
    ]

    targets = [
        {
            "id": "target_000",
            "position": np.array([0.5, 0.0, 0.0]),
        }
    ]

    flags = build_event_flags(
        agent_id="drone_000",
        drone_positions=positions,
        obstacles=obstacles,
        targets=targets,
        world_min=np.array([-10.0, -10.0, -10.0]),
        world_max=np.array([10.0, 10.0, 10.0]),
    )

    assert flags == {
        "drone_collision": True,
        "obstacle_collision": True,
        "target_found": True,
        "boundary_violation": False,
    }


def test_event_config_rejects_invalid_collision_distance():
    with pytest.raises(ValueError):
        EventConfig(drone_collision_distance=0.0)


def test_event_config_rejects_negative_tolerance():
    with pytest.raises(ValueError):
        EventConfig(boundary_tolerance=-1.0)


def test_distance_rejects_invalid_position_shape():
    with pytest.raises(ValueError):
        distance_between(
            np.array([0.0, 0.0]),
            np.zeros(3),
        )


def test_boundary_rejects_invalid_world_bounds():
    with pytest.raises(ValueError):
        detect_boundary_violations(
            positions={
                "drone_000": np.zeros(3),
            },
            world_min=np.array([10.0, 0.0, 0.0]),
            world_max=np.array([0.0, 10.0, 10.0]),
        )


def test_non_finite_position_is_rejected():
    with pytest.raises(ValueError):
        distance_between(
            np.array([np.nan, 0.0, 0.0]),
            np.zeros(3),
        )