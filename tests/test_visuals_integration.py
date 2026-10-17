import json
from pathlib import Path

import pytest

from sensors.curriculum import CurriculumRewardTuner
from sensors.difficulty import ObstacleDifficultyScaler
from sensors.reward_tuning import (
    RewardFieldChange,
    RewardTuningComparison,
    compare_reward_configs,
)
from sensors.rewards import RewardConfig
from sensors.visuals_integration import (
    VisualsIntegrationCheck,
    VisualsIntegrationError,
    validate_visuals_integration,
)


def make_ready_inputs():
    baseline = RewardConfig()
    profile = CurriculumRewardTuner().resolve(0.0)

    comparison = compare_reward_configs(
        baseline_config=baseline,
        tuned_config=profile.reward_config,
    )

    return profile.reward_config, comparison


def test_ready_check_for_valid_inputs():
    reward_config, comparison = make_ready_inputs()

    check = validate_visuals_integration(
        reward_config=reward_config,
        comparison=comparison,
    )

    assert isinstance(
        check,
        VisualsIntegrationCheck,
    )
    assert check.ready is True
    assert check.issues == ()
    assert check.comparison.changed_field_names == (
        "obstacle_collision",
    )


def test_missing_obstacle_change_reports_issue():
    baseline = RewardConfig()
    tuned = RewardConfig(new_area=2.0)

    comparison = compare_reward_configs(
        baseline_config=baseline,
        tuned_config=tuned,
    )

    check = validate_visuals_integration(
        reward_config=tuned,
        comparison=comparison,
    )

    assert check.ready is False
    assert (
        "Reward tuning comparison does not change "
        "obstacle_collision."
        in check.issues
    )


def test_positive_obstacle_penalty_reports_issue():
    positive_change = RewardFieldChange(
        field="obstacle_collision",
        baseline=-5.0,
        tuned=1.0,
        absolute_change=6.0,
        percentage_change=-120.0,
    )

    comparison = RewardTuningComparison(
        changed_fields=(positive_change,),
        unchanged_fields=(),
    )

    check = validate_visuals_integration(
        reward_config=RewardConfig(),
        comparison=comparison,
    )

    assert check.ready is False
    assert (
        "Tuned obstacle_collision penalty must be "
        "zero or negative."
        in check.issues
    )


def test_no_changed_fields_reports_issue():
    baseline = RewardConfig()
    comparison = compare_reward_configs(
        baseline_config=baseline,
        tuned_config=baseline,
    )

    check = validate_visuals_integration(
        reward_config=baseline,
        comparison=comparison,
    )

    assert check.ready is False
    assert (
        "Reward tuning comparison has no changed fields."
        in check.issues
    )


def test_matching_difficulty_profile_is_ready():
    reward_config, comparison = make_ready_inputs()

    difficulty = ObstacleDifficultyScaler(
        base_reward_config=RewardConfig()
    ).resolve(0.0)

    check = validate_visuals_integration(
        reward_config=reward_config,
        comparison=comparison,
        difficulty_profile=difficulty,
    )

    assert check.ready is True
    assert check.difficulty_profile is difficulty


def test_mismatched_difficulty_profile_reports_issue():
    reward_config, comparison = make_ready_inputs()

    difficulty = ObstacleDifficultyScaler(
        base_reward_config=RewardConfig(
            obstacle_collision=-10.0
        )
    ).resolve(0.0)

    check = validate_visuals_integration(
        reward_config=reward_config,
        comparison=comparison,
        difficulty_profile=difficulty,
    )

    assert check.ready is False
    assert any(
        "does not match" in issue
        for issue in check.issues
    )


def test_invalid_reward_config_is_rejected():
    _, comparison = make_ready_inputs()

    with pytest.raises(TypeError):
        validate_visuals_integration(
            reward_config="invalid",
            comparison=comparison,
        )


def test_invalid_comparison_is_rejected():
    reward_config, _ = make_ready_inputs()

    with pytest.raises(TypeError):
        validate_visuals_integration(
            reward_config=reward_config,
            comparison="invalid",
        )


def test_invalid_difficulty_profile_is_rejected():
    reward_config, comparison = make_ready_inputs()

    with pytest.raises(TypeError):
        validate_visuals_integration(
            reward_config=reward_config,
            comparison=comparison,
            difficulty_profile="invalid",
        )


def test_check_is_json_serializable():
    reward_config, comparison = make_ready_inputs()

    check = validate_visuals_integration(
        reward_config=reward_config,
        comparison=comparison,
    )

    encoded = check.to_json()
    decoded = json.loads(encoded)

    assert decoded["ready"] is True
    assert decoded["changed_field_names"] == [
        "obstacle_collision"
    ]


def test_source_inputs_are_not_modified():
    reward_config, comparison = make_ready_inputs()
    reward_before = reward_config.to_dict()
    comparison_before = comparison.to_dict()

    validate_visuals_integration(
        reward_config=reward_config,
        comparison=comparison,
    )

    assert reward_config.to_dict() == reward_before
    assert comparison.to_dict() == comparison_before