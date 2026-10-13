import json

import pytest

from sensors.curriculum import (
    CurriculumRewardError,
    CurriculumRewardTuner,
)
from sensors.rewards import (
    RewardConfig,
    calculate_reward,
    calculate_reward_breakdown,
)


def test_no_obstacle_collision_has_zero_penalty():
    reward, components = calculate_reward(
        agent_id="drone_000",
        new_cells=1,
        previously_explored=False,
        target_found=False,
        drone_collision=False,
        obstacle_collision=False,
        boundary_violation=False,
    )

    assert components["obstacle_collision"] == 0.0
    assert reward == pytest.approx(0.99)


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

    assert components["obstacle_collision"] == pytest.approx(
        -5.0
    )
    assert reward == pytest.approx(-5.01)


def test_obstacle_collision_combines_with_new_area():
    config = RewardConfig(
        new_area=2.0,
        obstacle_collision=-4.0,
        step_cost=-0.1,
    )

    reward, components = calculate_reward(
        agent_id="drone_000",
        new_cells=3,
        previously_explored=False,
        target_found=False,
        drone_collision=False,
        obstacle_collision=True,
        boundary_violation=False,
        config=config,
    )

    assert components["new_area"] == pytest.approx(6.0)
    assert components["obstacle_collision"] == pytest.approx(
        -4.0
    )
    assert components["step_cost"] == pytest.approx(-0.1)
    assert reward == pytest.approx(1.9)


def test_breakdown_reports_obstacle_collision():
    breakdown = calculate_reward_breakdown(
        new_cells=0,
        previously_explored=False,
        target_found=False,
        drone_collision=False,
        obstacle_collision=True,
        boundary_violation=False,
    )

    assert breakdown.obstacle_collision == pytest.approx(
        -5.0
    )
    assert breakdown.total == pytest.approx(-5.01)


def test_curriculum_easy_reduces_obstacle_penalty():
    tuner = CurriculumRewardTuner()
    profile = tuner.resolve(0.0)

    reward, components = calculate_reward(
        agent_id="drone_000",
        new_cells=0,
        previously_explored=False,
        target_found=False,
        drone_collision=False,
        obstacle_collision=True,
        boundary_violation=False,
        config=profile.reward_config,
    )

    assert profile.stage_name == "easy"
    assert components["obstacle_collision"] == pytest.approx(
        -1.25
    )
    assert reward == pytest.approx(-1.26)


def test_curriculum_moderate_uses_sixty_percent_penalty():
    tuner = CurriculumRewardTuner()
    profile = tuner.resolve(0.5)

    reward, components = calculate_reward(
        agent_id="drone_000",
        new_cells=0,
        previously_explored=False,
        target_found=False,
        drone_collision=False,
        obstacle_collision=True,
        boundary_violation=False,
        config=profile.reward_config,
    )

    assert profile.stage_name == "moderate"
    assert components["obstacle_collision"] == pytest.approx(
        -3.0
    )
    assert reward == pytest.approx(-3.01)


def test_curriculum_full_uses_original_penalty():
    tuner = CurriculumRewardTuner()
    profile = tuner.resolve(1.0)

    reward, components = calculate_reward(
        agent_id="drone_000",
        new_cells=0,
        previously_explored=False,
        target_found=False,
        drone_collision=False,
        obstacle_collision=True,
        boundary_violation=False,
        config=profile.reward_config,
    )

    assert profile.stage_name == "full"
    assert components["obstacle_collision"] == pytest.approx(
        -5.0
    )
    assert reward == pytest.approx(-5.01)


def test_curriculum_stages_resolve_expected_names():
    tuner = CurriculumRewardTuner()

    assert tuner.resolve(0.0).stage_name == "easy"
    assert tuner.resolve(0.5).stage_name == "moderate"
    assert tuner.resolve(1.0).stage_name == "full"


def test_curriculum_progress_outside_range_is_rejected():
    tuner = CurriculumRewardTuner()

    with pytest.raises(CurriculumRewardError):
        tuner.resolve(-0.01)

    with pytest.raises(CurriculumRewardError):
        tuner.resolve(1.01)


def test_positive_obstacle_penalty_is_rejected():
    with pytest.raises(ValueError):
        RewardConfig(obstacle_collision=5.0)


def test_reward_details_are_json_serializable():
    profile = CurriculumRewardTuner().resolve(0.5)

    reward, components = calculate_reward(
        agent_id="drone_000",
        new_cells=2,
        previously_explored=False,
        target_found=False,
        drone_collision=False,
        obstacle_collision=True,
        boundary_violation=False,
        config=profile.reward_config,
    )

    encoded = json.dumps(
        {
            "reward": reward,
            "components": components,
        }
    )

    decoded = json.loads(encoded)

    assert decoded["components"][
        "obstacle_collision"
    ] == pytest.approx(-3.0)