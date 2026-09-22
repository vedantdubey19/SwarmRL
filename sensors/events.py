from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class EventConfig:
    """Thresholds used to detect swarm events."""

    drone_collision_distance: float = 2.0
    obstacle_collision_distance: float = 1.0
    target_detection_distance: float = 3.0
    boundary_tolerance: float = 0.0

    def __post_init__(self) -> None:
        if self.drone_collision_distance <= 0:
            raise ValueError(
                "Drone collision distance must be positive."
            )

        if self.obstacle_collision_distance <= 0:
            raise ValueError(
                "Obstacle collision distance must be positive."
            )

        if self.target_detection_distance <= 0:
            raise ValueError(
                "Target detection distance must be positive."
            )

        if self.boundary_tolerance < 0:
            raise ValueError(
                "Boundary tolerance must not be negative."
            )


def _position(value: np.ndarray | list[float]) -> np.ndarray:
    """Convert a position to a validated 3D float vector."""
    result = np.asarray(value, dtype=np.float32)

    if result.shape != (3,):
        raise ValueError(
            "Every position must contain exactly three values."
        )

    if not np.all(np.isfinite(result)):
        raise ValueError(
            "Position values must be finite."
        )

    return result


def distance_between(
    first: np.ndarray | list[float],
    second: np.ndarray | list[float],
) -> float:
    """Return Euclidean distance between two 3D positions."""
    first_position = _position(first)
    second_position = _position(second)

    return float(np.linalg.norm(first_position - second_position))


def detect_drone_collisions(
    positions: dict[str, np.ndarray | list[float]],
    collision_distance: float = 2.0,
) -> set[str]:
    """Return IDs of all drones involved in a collision."""
    if collision_distance <= 0:
        raise ValueError(
            "Collision distance must be positive."
        )

    normalized = {
        agent_id: _position(position)
        for agent_id, position in positions.items()
    }

    collided_agents: set[str] = set()
    agent_ids = list(normalized)

    for index, first_id in enumerate(agent_ids):
        for second_id in agent_ids[index + 1:]:
            separation = distance_between(
                normalized[first_id],
                normalized[second_id],
            )

            if separation < collision_distance:
                collided_agents.add(first_id)
                collided_agents.add(second_id)

    return collided_agents


def detect_obstacle_collisions(
    drone_positions: dict[
        str,
        np.ndarray | list[float],
    ],
    obstacles: list[dict],
    collision_distance: float = 1.0,
) -> set[str]:
    """Return drone IDs touching at least one obstacle."""
    if collision_distance <= 0:
        raise ValueError(
            "Collision distance must be positive."
        )

    normalized_drones = {
        agent_id: _position(position)
        for agent_id, position in drone_positions.items()
    }

    collided_agents: set[str] = set()

    for obstacle in obstacles:
        if "position" not in obstacle:
            raise ValueError(
                "Each obstacle must contain a position."
            )

        obstacle_position = _position(obstacle["position"])
        obstacle_radius = float(
            obstacle.get("radius", 0.0)
        )

        if obstacle_radius < 0:
            raise ValueError(
                "Obstacle radius must not be negative."
            )

        threshold = collision_distance + obstacle_radius

        for agent_id, drone_position in normalized_drones.items():
            if distance_between(
                drone_position,
                obstacle_position,
            ) < threshold:
                collided_agents.add(agent_id)

    return collided_agents


def detect_targets_found(
    drone_positions: dict[
        str,
        np.ndarray | list[float],
    ],
    targets: list[dict],
    detection_distance: float = 3.0,
) -> set[str]:
    """Return drone IDs that are close enough to a target."""
    if detection_distance <= 0:
        raise ValueError(
            "Target detection distance must be positive."
        )

    normalized_drones = {
        agent_id: _position(position)
        for agent_id, position in drone_positions.items()
    }

    found_agents: set[str] = set()

    for target in targets:
        if "position" not in target:
            raise ValueError(
                "Each target must contain a position."
            )

        target_position = _position(target["position"])

        for agent_id, drone_position in normalized_drones.items():
            if distance_between(
                drone_position,
                target_position,
            ) <= detection_distance:
                found_agents.add(agent_id)

    return found_agents


def detect_boundary_violations(
    positions: dict[str, np.ndarray | list[float]],
    world_min: np.ndarray | list[float],
    world_max: np.ndarray | list[float],
    tolerance: float = 0.0,
) -> set[str]:
    """Return IDs whose positions are outside world bounds."""
    if tolerance < 0:
        raise ValueError(
            "Boundary tolerance must not be negative."
        )

    minimum = _position(world_min)
    maximum = _position(world_max)

    if np.any(minimum >= maximum):
        raise ValueError(
            "Every world minimum must be less than its maximum."
        )

    normalized_positions = {
        agent_id: _position(position)
        for agent_id, position in positions.items()
    }

    violations: set[str] = set()
    lower_bound = minimum - tolerance
    upper_bound = maximum + tolerance

    for agent_id, position in normalized_positions.items():
        outside_lower = np.any(position < lower_bound)
        outside_upper = np.any(position > upper_bound)

        if outside_lower or outside_upper:
            violations.add(agent_id)

    return violations


def build_event_flags(
    agent_id: str,
    drone_positions: dict[
        str,
        np.ndarray | list[float],
    ],
    obstacles: list[dict],
    targets: list[dict],
    world_min: np.ndarray | list[float],
    world_max: np.ndarray | list[float],
    config: EventConfig | None = None,
) -> dict[str, bool]:
    """Build reward-ready event flags for one drone."""
    if not agent_id:
        raise ValueError("Agent ID must not be empty.")

    config = config or EventConfig()

    drone_collisions = detect_drone_collisions(
        positions=drone_positions,
        collision_distance=(
            config.drone_collision_distance
        ),
    )

    obstacle_collisions = detect_obstacle_collisions(
        drone_positions=drone_positions,
        obstacles=obstacles,
        collision_distance=(
            config.obstacle_collision_distance
        ),
    )

    targets_found = detect_targets_found(
        drone_positions=drone_positions,
        targets=targets,
        detection_distance=(
            config.target_detection_distance
        ),
    )

    boundary_violations = detect_boundary_violations(
        positions=drone_positions,
        world_min=world_min,
        world_max=world_max,
        tolerance=config.boundary_tolerance,
    )

    return {
        "drone_collision": (
            agent_id in drone_collisions
        ),
        "obstacle_collision": (
            agent_id in obstacle_collisions
        ),
        "target_found": (
            agent_id in targets_found
        ),
        "boundary_violation": (
            agent_id in boundary_violations
        ),
    }