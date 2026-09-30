import json

import pytest

from sensors.rewards import (
    RewardBreakdown,
    RewardConfig,
    calculate_reward,
    calculate_reward_breakdown,
)


def test_default_reward_config_contains_expected_values():
    config = RewardConfig()

    assert config.new_area == 1.0
    assert config.team_new_area == 0.05
    assert config.target_found == 10.0
    assert config.team_target_found == 0.2
    assert config.drone_collision == -5.0
    assert config.obstacle_collision == -5.0
    assert config.boundary_violation == -5.0
    assert config.repeated_area == 0.0
    assert config.proximity_threshold == 3.0
    assert config.proximity_penalty == -0.5
    assert config.step_cost == -0.01


def test_new_area_reward_is_positive():
    reward, components = calculate_reward(
        agent_id="drone_000",
        new_cells=3,
        previously_explored=False,
        target_found=False,
        drone_collision=False,
        obstacle_collision=False,
        boundary_violation=False,
    )

    assert reward == pytest.approx(2.99)
    assert components["new_area"] == pytest.approx(3.0)
    assert components["target_found"] == 0.0
    assert components["step_cost"] == pytest.approx(-0.01)


def test_target_reward_is_positive():
    reward, components = calculate_reward(
        agent_id="drone_000",
        new_cells=0,
        previously_explored=False,
        target_found=True,
        drone_collision=False,
        obstacle_collision=False,
        boundary_violation=False,
    )

    assert reward == pytest.approx(9.99)
    assert components["target_found"] == pytest.approx(10.0)


def test_drone_collision_penalty_is_applied():
    reward, components = calculate_reward(
        agent_id="drone_000",
        new_cells=0,
        previously_explored=False,
        target_found=False,
        drone_collision=True,
        obstacle_collision=False,
        boundary_violation=False,
    )

    assert reward == pytest.approx(-5.01)
    assert components["drone_collision"] == -5.0


def test_obstacle_collision_penalty_is_applied():
    reward, components = calculate_reward(
        agent_id="drone_000",
        new_cells=0,
        previously_explored=False,
        target_found=False,
        drone_collision=False,
        obstacle_collision=True,
        boundary_violation=False,
    )

    assert reward == pytest.approx(-5.01)
    assert components["obstacle_collision"] == -5.0


def test_boundary_penalty_is_applied():
    reward, components = calculate_reward(
        agent_id="drone_000",
        new_cells=0,
        previously_explored=False,
        target_found=False,
        drone_collision=False,
        obstacle_collision=False,
        boundary_violation=True,
    )

    assert reward == pytest.approx(-5.01)
    assert components["boundary_violation"] == -5.0


def test_repeated_area_penalty_when_configured():
    config = RewardConfig(repeated_area=-0.1)
    reward, components = calculate_reward(
        agent_id="drone_000",
        new_cells=0,
        previously_explored=True,
        target_found=False,
        drone_collision=False,
        obstacle_collision=False,
        boundary_violation=False,
        config=config,
    )

    assert reward == pytest.approx(-0.11)
    assert components["repeated_area"] == pytest.approx(-0.1)


def test_repeated_area_penalty_defaults_to_zero():
    reward, components = calculate_reward(
        agent_id="drone_000",
        new_cells=0,
        previously_explored=True,
        target_found=False,
        drone_collision=False,
        obstacle_collision=False,
        boundary_violation=False,
    )

    assert reward == pytest.approx(-0.01)
    assert components["repeated_area"] == 0.0


def test_repeated_area_penalty_is_not_applied_for_new_cells():
    config = RewardConfig(repeated_area=-0.1)
    reward, components = calculate_reward(
        agent_id="drone_000",
        new_cells=2,
        previously_explored=True,
        target_found=False,
        drone_collision=False,
        obstacle_collision=False,
        boundary_violation=False,
        config=config,
    )

    assert components["repeated_area"] == 0.0
    assert reward == pytest.approx(1.99)


def test_team_new_area_reward_is_applied():
    reward, components = calculate_reward(
        agent_id="drone_000",
        new_cells=1,
        previously_explored=False,
        target_found=False,
        drone_collision=False,
        obstacle_collision=False,
        boundary_violation=False,
        team_cells=10,
    )

    # 1.0 (new_area) + 10 * 0.05 (team_new_area = 0.5) - 0.01 (step_cost) = 1.49
    assert reward == pytest.approx(1.49)
    assert components["new_area"] == pytest.approx(1.0)
    assert components["team_new_area"] == pytest.approx(0.5)


def test_team_target_found_reward_is_applied():
    reward, components = calculate_reward(
        agent_id="drone_000",
        new_cells=0,
        previously_explored=False,
        target_found=False,
        drone_collision=False,
        obstacle_collision=False,
        boundary_violation=False,
        team_target_found=True,
    )

    # 0.2 (team_target_found) - 0.01 (step_cost) = 0.19
    assert reward == pytest.approx(0.19)
    assert components["target_found"] == 0.0
    assert components["team_target_found"] == pytest.approx(0.2)


def test_proximity_penalty_applied_when_close():
    # min_neighbor_dist = 1.0m, threshold = 3.0m, weight = -0.5 -> penalty = -0.5 * (3.0 - 1.0) = -1.0
    reward, components = calculate_reward(
        agent_id="drone_000",
        new_cells=0,
        previously_explored=False,
        target_found=False,
        drone_collision=False,
        obstacle_collision=False,
        boundary_violation=False,
        min_neighbor_dist=1.0,
    )

    assert reward == pytest.approx(-1.01)
    assert components["proximity_penalty"] == pytest.approx(-1.0)


def test_proximity_penalty_zero_when_outside_threshold():
    # min_neighbor_dist = 5.0m >= threshold 3.0m -> penalty = 0.0
    reward, components = calculate_reward(
        agent_id="drone_000",
        new_cells=0,
        previously_explored=False,
        target_found=False,
        drone_collision=False,
        obstacle_collision=False,
        boundary_violation=False,
        min_neighbor_dist=5.0,
    )

    assert reward == pytest.approx(-0.01)
    assert components["proximity_penalty"] == 0.0


def test_breakdown_total_matches_components():
    breakdown = calculate_reward_breakdown(
        new_cells=2,
        previously_explored=False,
        target_found=True,
        drone_collision=False,
        obstacle_collision=False,
        boundary_violation=False,
    )

    assert isinstance(breakdown, RewardBreakdown)
    assert breakdown.new_area == pytest.approx(2.0)
    assert breakdown.target_found == pytest.approx(10.0)
    assert breakdown.total == pytest.approx(11.99)


def test_reward_details_include_total():
    _, components = calculate_reward(
        agent_id="drone_000",
        new_cells=1,
        previously_explored=False,
        target_found=False,
        drone_collision=False,
        obstacle_collision=False,
        boundary_violation=False,
    )

    assert "total" in components
    assert components["total"] == pytest.approx(0.99)


def test_reward_details_are_json_serializable():
    reward, components = calculate_reward(
        agent_id="drone_000",
        new_cells=1,
        previously_explored=False,
        target_found=True,
        drone_collision=False,
        obstacle_collision=False,
        boundary_violation=False,
        team_cells=5,
        team_target_found=True,
        min_neighbor_dist=2.0,
    )

    encoded = json.dumps(
        {
            "reward": reward,
            "components": components,
        }
    )

    assert isinstance(encoded, str)


def test_custom_reward_config_is_used():
    config = RewardConfig(
        new_area=2.0,
        target_found=10.0,
        step_cost=-0.5,
    )

    reward, components = calculate_reward(
        agent_id="drone_000",
        new_cells=3,
        previously_explored=False,
        target_found=True,
        drone_collision=False,
        obstacle_collision=False,
        boundary_violation=False,
        config=config,
    )

    assert reward == pytest.approx(15.5)
    assert components["new_area"] == pytest.approx(6.0)
    assert components["target_found"] == pytest.approx(10.0)
    assert components["step_cost"] == pytest.approx(-0.5)


def test_negative_new_cells_are_rejected():
    with pytest.raises(ValueError):
        calculate_reward(
            agent_id="drone_000",
            new_cells=-1,
            previously_explored=False,
            target_found=False,
            drone_collision=False,
            obstacle_collision=False,
            boundary_violation=False,
        )


def test_negative_team_cells_are_rejected():
    with pytest.raises(ValueError):
        calculate_reward(
            agent_id="drone_000",
            new_cells=0,
            previously_explored=False,
            target_found=False,
            drone_collision=False,
            obstacle_collision=False,
            boundary_violation=False,
            team_cells=-5,
        )


def test_non_integer_new_cells_are_rejected():
    with pytest.raises(TypeError):
        calculate_reward(
            agent_id="drone_000",
            new_cells=1.5,
            previously_explored=False,
            target_found=False,
            drone_collision=False,
            obstacle_collision=False,
            boundary_violation=False,
        )


def test_empty_agent_id_is_rejected():
    with pytest.raises(ValueError):
        calculate_reward(
            agent_id="",
            new_cells=0,
            previously_explored=False,
            target_found=False,
            drone_collision=False,
            obstacle_collision=False,
            boundary_violation=False,
        )


def test_invalid_positive_collision_penalty_is_rejected():
    with pytest.raises(ValueError):
        RewardConfig(drone_collision=5.0)


def test_invalid_positive_step_cost_is_rejected():
    with pytest.raises(ValueError):
        RewardConfig(step_cost=1.0)


def test_invalid_negative_min_neighbor_dist_is_rejected():
    with pytest.raises(ValueError):
        calculate_reward(
            agent_id="drone_000",
            new_cells=0,
            previously_explored=False,
            target_found=False,
            drone_collision=False,
            obstacle_collision=False,
            boundary_violation=False,
            min_neighbor_dist=-1.0,
        )