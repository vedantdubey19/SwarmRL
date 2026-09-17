from dataclasses import dataclass


@dataclass
class RewardConfig:
    new_area: float = 1.0
    target_found: float = 20.0
    drone_collision: float = -100.0
    obstacle_collision: float = -50.0
    boundary_violation: float = -10.0
    repeated_area: float = -0.1
    step_cost: float = -0.01


def calculate_reward(
    agent_id: str,
    new_cells: int,
    previously_explored: bool,
    target_found: bool,
    drone_collision: bool,
    obstacle_collision: bool,
    boundary_violation: bool,
    config: RewardConfig | None = None,
) -> tuple[float, dict]:
    del agent_id

    config = config or RewardConfig()

    components = {
        "new_area": new_cells * config.new_area,
        "target_found": (
            config.target_found if target_found else 0.0
        ),
        "drone_collision": (
            config.drone_collision if drone_collision else 0.0
        ),
        "obstacle_collision": (
            config.obstacle_collision
            if obstacle_collision
            else 0.0
        ),
        "boundary_violation": (
            config.boundary_violation
            if boundary_violation
            else 0.0
        ),
        "repeated_area": (
            config.repeated_area
            if previously_explored and new_cells == 0
            else 0.0
        ),
        "step_cost": config.step_cost,
    }

    return float(sum(components.values())), components