import json

import numpy as np
import pytest

from sensors.scenario import (
    ScenarioConfig,
    ScenarioLevel,
    curriculum_scenarios,
    generate_agent_positions,
    generate_obstacles,
    generate_targets,
    scenario_layout,
    scenario_preset,
)


def test_all_presets_create_valid_configs():
    for level in ScenarioLevel:
        config = scenario_preset(level)

        assert config.level == level
        assert config.num_agents > 0
        assert config.max_steps > 0
        assert config.sensor_range > 0


def test_stress_preset_has_fifty_agents():
    config = scenario_preset(ScenarioLevel.STRESS)

    assert config.num_agents == 50
    assert config.num_obstacles == 30
    assert config.wind_strength == pytest.approx(1.5)


def test_preset_accepts_string_level():
    config = scenario_preset("easy")

    assert config.level == ScenarioLevel.EASY
    assert config.name == "easy_search"


def test_curriculum_is_ordered_by_agent_count():
    scenarios = curriculum_scenarios(seed=10)
    agent_counts = [
        scenario.num_agents
        for scenario in scenarios
    ]

    assert agent_counts == [5, 10, 20, 35, 50]
    assert scenarios[0].seed == 10
    assert scenarios[-1].seed == 14


def test_config_to_dict_is_json_serializable():
    config = scenario_preset("medium")

    encoded = json.dumps(config.to_dict())
    result = json.loads(encoded)

    assert result["level"] == "medium"
    assert result["world_size"] == [100.0, 100.0]


def test_obstacle_generation_is_deterministic():
    config = scenario_preset("medium", seed=123)

    first = generate_obstacles(config)
    second = generate_obstacles(config)

    assert first == second
    assert len(first) == config.num_obstacles


def test_target_generation_is_deterministic():
    config = scenario_preset("easy", seed=456)

    first = generate_targets(config)
    second = generate_targets(config)

    assert first == second
    assert len(first) == config.num_targets


def test_agent_position_generation_is_deterministic():
    config = scenario_preset("baseline", seed=789)

    first = generate_agent_positions(config)
    second = generate_agent_positions(config)

    assert first == second
    assert len(first) == config.num_agents
    assert "drone_000" in first


def test_generated_positions_are_inside_world():
    config = scenario_preset("hard", seed=123)

    layout = scenario_layout(config)
    width, depth = config.world_size

    positions = list(layout["agents"].values())

    for obstacle in layout["obstacles"]:
        positions.append(obstacle["position"])

    for target in layout["targets"]:
        positions.append(target["position"])

    for position in positions:
        assert -width / 2 <= position[0] <= width / 2
        assert position[1] == 0.0
        assert -depth / 2 <= position[2] <= depth / 2


def test_obstacle_radius_is_in_configured_range():
    config = scenario_preset("hard", seed=123)

    obstacles = generate_obstacles(config)
    minimum_radius, maximum_radius = (
        config.obstacle_radius_range
    )

    for obstacle in obstacles:
        assert (
            minimum_radius
            <= obstacle["radius"]
            <= maximum_radius
        )


def test_scenario_layout_contains_all_sections():
    config = scenario_preset("easy")
    layout = scenario_layout(config)

    assert set(layout) == {
        "scenario",
        "agents",
        "obstacles",
        "targets",
    }
    assert layout["scenario"]["name"] == "easy_search"
    assert len(layout["agents"]) == config.num_agents
    assert len(layout["obstacles"]) == config.num_obstacles
    assert len(layout["targets"]) == config.num_targets


def test_scenario_layout_is_json_serializable():
    layout = scenario_layout(
        scenario_preset("baseline")
    )

    encoded = json.dumps(layout)

    assert isinstance(encoded, str)


def test_invalid_empty_name_is_rejected():
    with pytest.raises(ValueError):
        ScenarioConfig(
            name="",
            level=ScenarioLevel.BASELINE,
            num_agents=1,
        )


def test_invalid_agent_count_is_rejected():
    with pytest.raises(ValueError):
        ScenarioConfig(
            name="bad",
            level=ScenarioLevel.BASELINE,
            num_agents=0,
        )


def test_invalid_world_size_is_rejected():
    with pytest.raises(ValueError):
        ScenarioConfig(
            name="bad",
            level=ScenarioLevel.BASELINE,
            num_agents=1,
            world_size=(100.0, 0.0),
        )


def test_invalid_target_count_is_rejected():
    with pytest.raises(ValueError):
        ScenarioConfig(
            name="bad",
            level=ScenarioLevel.BASELINE,
            num_agents=1,
            num_targets=-1,
        )


def test_invalid_obstacle_range_is_rejected():
    with pytest.raises(ValueError):
        ScenarioConfig(
            name="bad",
            level=ScenarioLevel.BASELINE,
            num_agents=1,
            obstacle_radius_range=(3.0, 1.0),
        )


def test_invalid_wind_strength_is_rejected():
    with pytest.raises(ValueError):
        ScenarioConfig(
            name="bad",
            level=ScenarioLevel.BASELINE,
            num_agents=1,
            wind_strength=-0.1,
        )


def test_invalid_sensor_range_is_rejected():
    with pytest.raises(ValueError):
        ScenarioConfig(
            name="bad",
            level=ScenarioLevel.BASELINE,
            num_agents=1,
            sensor_range=0.0,
        )


def test_invalid_field_of_view_is_rejected():
    with pytest.raises(ValueError):
        ScenarioConfig(
            name="bad",
            level=ScenarioLevel.BASELINE,
            num_agents=1,
            field_of_view=0.0,
        )