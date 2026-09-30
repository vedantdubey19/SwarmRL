from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class RewardConfig:
    """Weights used to calculate one agent's reward."""

    new_area: float = 1.0
    team_new_area: float = 0.05
    target_found: float = 10.0
    team_target_found: float = 0.2
    drone_collision: float = -5.0
    obstacle_collision: float = -5.0
    boundary_violation: float = -5.0
    repeated_area: float = 0.0
    proximity_threshold: float = 3.0
    proximity_penalty: float = -0.5
    step_cost: float = -0.01

    def __post_init__(self) -> None:
        if self.new_area < 0:
            raise ValueError(
                "New-area reward must not be negative."
            )

        if self.team_new_area < 0:
            raise ValueError(
                "Team new-area reward must not be negative."
            )

        if self.target_found < 0:
            raise ValueError(
                "Target-found reward must not be negative."
            )

        if self.team_target_found < 0:
            raise ValueError(
                "Team target-found reward must not be negative."
            )

        if self.drone_collision > 0:
            raise ValueError(
                "Drone-collision penalty must be zero or negative."
            )

        if self.obstacle_collision > 0:
            raise ValueError(
                "Obstacle-collision penalty must be zero or negative."
            )

        if self.boundary_violation > 0:
            raise ValueError(
                "Boundary penalty must be zero or negative."
            )

        if self.repeated_area > 0:
            raise ValueError(
                "Repeated-area penalty must be zero or negative."
            )

        if self.proximity_threshold < 0:
            raise ValueError(
                "Proximity threshold must not be negative."
            )

        if self.proximity_penalty > 0:
            raise ValueError(
                "Proximity penalty must be zero or negative."
            )

        if self.step_cost > 0:
            raise ValueError(
                "Step cost must be zero or negative."
            )

    def to_dict(self) -> dict[str, float]:
        """Return configuration as a JSON-friendly dictionary."""
        return {
            key: float(value)
            for key, value in asdict(self).items()
        }


@dataclass
class RewardBreakdown:
    """Individual reward components and their total."""

    new_area: float = 0.0
    team_new_area: float = 0.0
    target_found: float = 0.0
    team_target_found: float = 0.0
    drone_collision: float = 0.0
    obstacle_collision: float = 0.0
    boundary_violation: float = 0.0
    repeated_area: float = 0.0
    proximity_penalty: float = 0.0
    step_cost: float = 0.0

    @property
    def total(self) -> float:
        """Return the sum of all reward components."""
        return float(
            self.new_area
            + self.team_new_area
            + self.target_found
            + self.team_target_found
            + self.drone_collision
            + self.obstacle_collision
            + self.boundary_violation
            + self.repeated_area
            + self.proximity_penalty
            + self.step_cost
        )

    def to_dict(self) -> dict[str, float]:
        """Return reward components and total as a dictionary."""
        return {
            "new_area": float(self.new_area),
            "team_new_area": float(self.team_new_area),
            "target_found": float(self.target_found),
            "team_target_found": float(self.team_target_found),
            "drone_collision": float(self.drone_collision),
            "obstacle_collision": float(self.obstacle_collision),
            "boundary_violation": float(self.boundary_violation),
            "repeated_area": float(self.repeated_area),
            "proximity_penalty": float(self.proximity_penalty),
            "step_cost": float(self.step_cost),
            "total": float(self.total),
        }


def calculate_reward_breakdown(
    new_cells: int,
    previously_explored: bool,
    target_found: bool,
    drone_collision: bool,
    obstacle_collision: bool,
    boundary_violation: bool,
    config: RewardConfig | None = None,
    team_cells: int = 0,
    team_target_found: bool = False,
    min_neighbor_dist: float | None = None,
) -> RewardBreakdown:
    """Calculate all reward components for one agent."""
    config = config or RewardConfig()

    if not isinstance(new_cells, int):
        raise TypeError("new_cells must be an integer.")

    if new_cells < 0:
        raise ValueError("new_cells must not be negative.")

    if not isinstance(team_cells, int):
        raise TypeError("team_cells must be an integer.")

    if team_cells < 0:
        raise ValueError("team_cells must not be negative.")

    if min_neighbor_dist is not None:
        if not isinstance(min_neighbor_dist, (int, float)):
            raise TypeError("min_neighbor_dist must be a number.")
        if min_neighbor_dist < 0:
            raise ValueError("min_neighbor_dist must not be negative.")

    prox_cost = 0.0
    if (
        min_neighbor_dist is not None
        and min_neighbor_dist < config.proximity_threshold
    ):
        prox_cost = config.proximity_penalty * (
            config.proximity_threshold - float(min_neighbor_dist)
        )

    breakdown = RewardBreakdown(
        new_area=float(new_cells) * config.new_area,
        team_new_area=float(team_cells) * config.team_new_area,
        target_found=(
            config.target_found
            if target_found
            else 0.0
        ),
        team_target_found=(
            config.team_target_found
            if team_target_found
            else 0.0
        ),
        drone_collision=(
            config.drone_collision
            if drone_collision
            else 0.0
        ),
        obstacle_collision=(
            config.obstacle_collision
            if obstacle_collision
            else 0.0
        ),
        boundary_violation=(
            config.boundary_violation
            if boundary_violation
            else 0.0
        ),
        repeated_area=(
            config.repeated_area
            if previously_explored and new_cells == 0
            else 0.0
        ),
        proximity_penalty=prox_cost,
        step_cost=config.step_cost,
    )

    return breakdown


def calculate_reward(
    agent_id: str,
    new_cells: int,
    previously_explored: bool,
    target_found: bool,
    drone_collision: bool,
    obstacle_collision: bool,
    boundary_violation: bool,
    config: RewardConfig | None = None,
    team_cells: int = 0,
    team_target_found: bool = False,
    min_neighbor_dist: float | None = None,
) -> tuple[float, dict[str, Any]]:
    """Return total reward and component details.

    The agent_id argument is retained for compatibility with the
    environment interface.
    """
    if not agent_id:
        raise ValueError("agent_id must not be empty.")

    breakdown = calculate_reward_breakdown(
        new_cells=new_cells,
        previously_explored=previously_explored,
        target_found=target_found,
        drone_collision=drone_collision,
        obstacle_collision=obstacle_collision,
        boundary_violation=boundary_violation,
        config=config,
        team_cells=team_cells,
        team_target_found=team_target_found,
        min_neighbor_dist=min_neighbor_dist,
    )

    details = breakdown.to_dict()

    return float(breakdown.total), details