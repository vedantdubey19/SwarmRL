from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

import numpy as np


class ScenarioLevel(str, Enum):
    """Named scenario difficulty levels."""

    BASELINE = "baseline"
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    STRESS = "stress"


@dataclass(frozen=True)
class ScenarioConfig:
    """Validated environment configuration for one scenario."""

    name: str
    level: ScenarioLevel
    num_agents: int
    world_size: tuple[float, float] = (100.0, 100.0)
    max_steps: int = 500
    num_targets: int = 3
    num_obstacles: int = 0
    obstacle_radius_range: tuple[float, float] = (
        1.0,
        3.0,
    )
    wind_strength: float = 0.0
    exploration_radius: float = 2.0
    sensor_range: float = 20.0
    field_of_view: float = np.pi / 2
    seed: int = 42

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError(
                "Scenario name must not be empty."
            )

        if self.num_agents <= 0:
            raise ValueError(
                "Number of agents must be positive."
            )

        if len(self.world_size) != 2:
            raise ValueError(
                "World size must contain width and depth."
            )

        if any(size <= 0 for size in self.world_size):
            raise ValueError(
                "World dimensions must be positive."
            )

        if self.max_steps <= 0:
            raise ValueError(
                "Maximum step count must be positive."
            )

        if self.num_targets < 0:
            raise ValueError(
                "Target count must not be negative."
            )

        if self.num_obstacles < 0:
            raise ValueError(
                "Obstacle count must not be negative."
            )

        if len(self.obstacle_radius_range) != 2:
            raise ValueError(
                "Obstacle radius range must contain two values."
            )

        minimum_radius, maximum_radius = (
            self.obstacle_radius_range
        )

        if minimum_radius <= 0:
            raise ValueError(
                "Minimum obstacle radius must be positive."
            )

        if maximum_radius < minimum_radius:
            raise ValueError(
                "Maximum obstacle radius must be at least "
                "the minimum radius."
            )

        if self.wind_strength < 0:
            raise ValueError(
                "Wind strength must not be negative."
            )

        if self.exploration_radius <= 0:
            raise ValueError(
                "Exploration radius must be positive."
            )

        if self.sensor_range <= 0:
            raise ValueError(
                "Sensor range must be positive."
            )

        if not 0 < self.field_of_view <= 2 * np.pi:
            raise ValueError(
                "Field of view must be in the interval "
                "(0, 2*pi]."
            )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible scenario configuration."""
        result = asdict(self)
        result["level"] = self.level.value
        result["world_size"] = list(self.world_size)
        result["obstacle_radius_range"] = list(
            self.obstacle_radius_range
        )
        result["field_of_view"] = float(
            self.field_of_view
        )

        return result


def scenario_preset(
    level: ScenarioLevel | str,
    seed: int = 42,
) -> ScenarioConfig:
    """Return a standard scenario configuration."""
    selected_level = ScenarioLevel(level)

    presets = {
        ScenarioLevel.BASELINE: {
            "name": "baseline_search",
            "num_agents": 5,
            "max_steps": 300,
            "num_targets": 1,
            "num_obstacles": 0,
            "wind_strength": 0.0,
        },
        ScenarioLevel.EASY: {
            "name": "easy_search",
            "num_agents": 10,
            "max_steps": 400,
            "num_targets": 3,
            "num_obstacles": 5,
            "wind_strength": 0.0,
        },
        ScenarioLevel.MEDIUM: {
            "name": "medium_search",
            "num_agents": 20,
            "max_steps": 500,
            "num_targets": 5,
            "num_obstacles": 12,
            "wind_strength": 0.5,
        },
        ScenarioLevel.HARD: {
            "name": "hard_search",
            "num_agents": 35,
            "max_steps": 600,
            "num_targets": 8,
            "num_obstacles": 20,
            "wind_strength": 1.0,
        },
        ScenarioLevel.STRESS: {
            "name": "stress_search",
            "num_agents": 50,
            "max_steps": 750,
            "num_targets": 10,
            "num_obstacles": 30,
            "wind_strength": 1.5,
        },
    }

    return ScenarioConfig(
        level=selected_level,
        seed=seed,
        **presets[selected_level],
    )


def curriculum_scenarios(
    seed: int = 42,
) -> list[ScenarioConfig]:
    """Return ordered presets for curriculum training."""
    return [
        scenario_preset(
            ScenarioLevel.BASELINE,
            seed=seed,
        ),
        scenario_preset(
            ScenarioLevel.EASY,
            seed=seed + 1,
        ),
        scenario_preset(
            ScenarioLevel.MEDIUM,
            seed=seed + 2,
        ),
        scenario_preset(
            ScenarioLevel.HARD,
            seed=seed + 3,
        ),
        scenario_preset(
            ScenarioLevel.STRESS,
            seed=seed + 4,
        ),
    ]


def _sample_position(
    generator: np.random.Generator,
    world_size: tuple[float, float],
    margin: float = 0.0,
) -> list[float]:
    """Sample one x-y-z position inside the world."""
    width, depth = world_size

    if margin < 0:
        raise ValueError(
            "Position margin must not be negative."
        )

    if margin * 2 >= width or margin * 2 >= depth:
        raise ValueError(
            "Position margin is too large for the world."
        )

    x = generator.uniform(
        -width / 2 + margin,
        width / 2 - margin,
    )
    z = generator.uniform(
        -depth / 2 + margin,
        depth / 2 - margin,
    )

    return [float(x), 0.0, float(z)]


def generate_obstacles(
    config: ScenarioConfig,
) -> list[dict[str, Any]]:
    """Generate deterministic obstacle positions and radii."""
    generator = np.random.default_rng(config.seed)
    obstacles = []

    minimum_radius, maximum_radius = (
        config.obstacle_radius_range
    )

    for index in range(config.num_obstacles):
        radius = float(
            generator.uniform(
                minimum_radius,
                maximum_radius,
            )
        )

        position = _sample_position(
            generator,
            config.world_size,
            margin=radius,
        )

        obstacles.append(
            {
                "id": f"obstacle_{index:03d}",
                "type": "obstacle",
                "position": position,
                "radius": radius,
            }
        )

    return obstacles


def generate_targets(
    config: ScenarioConfig,
) -> list[dict[str, Any]]:
    """Generate deterministic target positions."""
    generator = np.random.default_rng(config.seed + 10_000)
    targets = []

    for index in range(config.num_targets):
        targets.append(
            {
                "id": f"target_{index:03d}",
                "type": "target",
                "position": _sample_position(
                    generator,
                    config.world_size,
                ),
            }
        )

    return targets


def generate_agent_positions(
    config: ScenarioConfig,
) -> dict[str, list[float]]:
    """Generate deterministic initial drone positions."""
    generator = np.random.default_rng(config.seed + 20_000)
    positions = {}

    for index in range(config.num_agents):
        positions[f"drone_{index:03d}"] = _sample_position(
            generator,
            config.world_size,
        )

    return positions


def scenario_layout(
    config: ScenarioConfig,
) -> dict[str, Any]:
    """Build all deterministic world objects for one scenario."""
    return {
        "scenario": config.to_dict(),
        "agents": generate_agent_positions(config),
        "obstacles": generate_obstacles(config),
        "targets": generate_targets(config),
    }