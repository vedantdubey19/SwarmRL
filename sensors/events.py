from dataclasses import dataclass
from typing import Any
import numpy as np


@dataclass(frozen=True)
class EventConfig:
    drone_collision_distance: float = 2.0
    obstacle_collision_distance: float = 1.0
    target_detection_distance: float = 3.0
    boundary_tolerance: float = 0.0

    def __post_init__(self) -> None:
        if self.drone_collision_distance <= 0:
            raise ValueError("Drone collision distance must be positive.")
        if self.obstacle_collision_distance <= 0:
            raise ValueError("Obstacle collision distance must be positive.")
        if self.target_detection_distance <= 0:
            raise ValueError("Target detection distance must be positive.")
        if self.boundary_tolerance < 0:
            raise ValueError("Boundary tolerance must not be negative.")


def _position(value: np.ndarray | list[float]) -> np.ndarray:
    result = np.asarray(value, dtype=np.float32)
    if result.shape != (3,):
        raise ValueError("Every position must contain exactly three values.")
    if not np.all(np.isfinite(result)):
        raise ValueError("Position values must be finite.")
    return result


def detect_drone_collisions_vectorized(positions: np.ndarray, collision_distance: float = 2.0) -> np.ndarray:
    """Return boolean array of length N indicating if each drone is in collision."""
    num_agents = positions.shape[0]
    if num_agents <= 1:
        return np.zeros(num_agents, dtype=bool)

    diff = positions[:, None, :] - positions[None, :, :]
    dists = np.linalg.norm(diff, axis=2)
    np.fill_diagonal(dists, np.inf)
    collided = np.any(dists < collision_distance, axis=1)
    return collided


def detect_obstacle_collisions_vectorized(
    positions: np.ndarray,
    obs_positions: np.ndarray,
    obs_radii: np.ndarray,
    obs_heights: np.ndarray,
    collision_distance: float = 1.0,
) -> np.ndarray:
    num_agents = positions.shape[0]
    num_obs = obs_positions.shape[0]
    if num_agents == 0 or num_obs == 0:
        return np.zeros(num_agents, dtype=bool)

    # Horizontal distance in x-z
    dx = positions[:, None, 0] - obs_positions[None, :, 0]
    dz = positions[:, None, 2] - obs_positions[None, :, 2]
    horiz_dists = np.hypot(dx, dz)

    # Vertical bounds: y in [0, obs_heights]
    y_in_range = (positions[:, None, 1] >= 0.0) & (positions[:, None, 1] <= obs_heights[None, :])
    colliding = (horiz_dists < (obs_radii[None, :] + collision_distance)) & y_in_range
    return np.any(colliding, axis=1)


def detect_target_found_vectorized(
    positions: np.ndarray,
    target_positions: np.ndarray,
    active_mask: np.ndarray,
    detection_distance: float = 3.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Returns (drone_found_mask: (N,), target_found_mask: (M,))."""
    num_agents = positions.shape[0]
    num_targets = target_positions.shape[0]
    if num_agents == 0 or num_targets == 0:
        return np.zeros(num_agents, dtype=bool), np.zeros(num_targets, dtype=bool)

    diff = positions[:, None, :] - target_positions[None, :, :]
    dists = np.linalg.norm(diff, axis=2)  # (N, M)

    valid_targets = dists < detection_distance
    valid_targets = valid_targets & active_mask[None, :]

    drone_has_target = np.any(valid_targets, axis=1)
    newly_found_targets = np.any(valid_targets, axis=0)
    return drone_has_target, newly_found_targets


def detect_drone_collisions(
    positions: dict[str, np.ndarray | list[float]],
    collision_distance: float = 2.0,
) -> set[str]:
    """Dictionary-based interface for compatibility and testing."""
    if collision_distance <= 0:
        raise ValueError("Collision distance must be positive.")

    agent_ids = list(positions.keys())
    if len(agent_ids) <= 1:
        return set()

    pos_array = np.array([_position(positions[aid]) for aid in agent_ids], dtype=np.float32)
    collided_mask = detect_drone_collisions_vectorized(pos_array, collision_distance)
    return {agent_ids[i] for i in range(len(agent_ids)) if collided_mask[i]}


def detect_obstacle_collisions(
    drone_positions: dict[str, np.ndarray | list[float]],
    obstacles: list[dict],
    collision_distance: float = 1.0,
) -> set[str]:
    if collision_distance <= 0:
        raise ValueError("Collision distance must be positive.")

    agent_ids = list(drone_positions.keys())
    if not agent_ids or not obstacles:
        return set()

    pos_array = np.array([_position(drone_positions[aid]) for aid in agent_ids], dtype=np.float32)
    obs_pos = np.array([_position(obs["position"]) for obs in obstacles], dtype=np.float32)
    obs_radii = np.array([float(obs.get("radius", 0.0)) for obs in obstacles], dtype=np.float32)
    obs_heights = np.array([float(obs.get("height", 20.0)) for obs in obstacles], dtype=np.float32)

    collided_mask = detect_obstacle_collisions_vectorized(
        pos_array, obs_pos, obs_radii, obs_heights, collision_distance
    )
    return {agent_ids[i] for i in range(len(agent_ids)) if collided_mask[i]}


def detect_targets_found(
    drone_positions: dict[str, np.ndarray | list[float]],
    targets: list[dict],
    detection_distance: float = 3.0,
) -> set[str]:
    if detection_distance <= 0:
        raise ValueError("Target detection distance must be positive.")

    agent_ids = list(drone_positions.keys())
    if not agent_ids or not targets:
        return set()

    pos_array = np.array([_position(drone_positions[aid]) for aid in agent_ids], dtype=np.float32)
    target_pos = np.array([_position(t["position"]) for t in targets], dtype=np.float32)
    active_mask = np.ones(len(targets), dtype=bool)

    drone_mask, _ = detect_target_found_vectorized(pos_array, target_pos, active_mask, detection_distance)
    return {agent_ids[i] for i in range(len(agent_ids)) if drone_mask[i]}


def detect_boundary_violations(
    positions: dict[str, np.ndarray | list[float]],
    world_min: np.ndarray | list[float],
    world_max: np.ndarray | list[float],
    tolerance: float = 0.0,
) -> set[str]:
    if tolerance < 0:
        raise ValueError("Boundary tolerance must not be negative.")
    minimum = _position(world_min)
    maximum = _position(world_max)
    if np.any(minimum >= maximum):
        raise ValueError("Every world minimum must be less than its maximum.")
    lower_bound = minimum - tolerance
    upper_bound = maximum + tolerance
    violations = set()
    for aid, pos in positions.items():
        p = _position(pos)
        if np.any(p < lower_bound) or np.any(p > upper_bound):
            violations.add(aid)
    return violations


def compute_min_neighbor_distance(agent_id: str, positions: dict[str, np.ndarray | list[float]]) -> float | None:
    if agent_id not in positions or len(positions) <= 1:
        return None
    target = _position(positions[agent_id])
    nearest = float("inf")
    for other_id, other_pos in positions.items():
        if other_id == agent_id:
            continue
        d = float(np.linalg.norm(target - _position(other_pos)))
        if d < nearest:
            nearest = d
    return nearest if nearest != float("inf") else None
