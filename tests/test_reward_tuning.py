import json
from pathlib import Path

import pytest

from sensors.curriculum import CurriculumRewardTuner
from sensors.reward_tuning import (
    RewardTuningComparison,
    RewardTuningError,
    compare_reward_configs,
    export_reward_tuning_comparison,
)
from sensors.rewards import RewardConfig


def test_identical_configs_have_no_changes():
    baseline = RewardConfig()
    tuned = RewardConfig()

    comparison = compare_reward_configs(
        baseline_config=baseline,
        tuned_config=tuned,
    )

    assert isinstance(
        comparison,
        RewardTuningComparison,
    )
    assert comparison.changed_fields == ()
    assert comparison.changed_field_names == ()
    assert len(comparison.unchanged_fields) == 11


def test_obstacle_collision_change_is_detected():
    baseline = RewardConfig()
    tuned = RewardConfig(obstacle_collision=-2.5)

    comparison = compare_reward_configs(
        baseline_config=baseline,
        tuned_config=tuned,
    )

    assert comparison.changed_field_names == (
        "obstacle_collision",
    )

    change = comparison.changed_fields[0]

    assert change.field == "obstacle_collision"
    assert change.baseline == pytest.approx(-5.0)
    assert change.tuned == pytest.approx(-2.5)
    assert change.absolute_change == pytest.approx(2.5)
    assert change.percentage_change == pytest.approx(-50.0)


def test_multiple_changes_are_detected():
    baseline = RewardConfig()
    tuned = RewardConfig(
        new_area=2.0,
        obstacle_collision=-1.0,
        step_cost=-0.05,
    )

    comparison = compare_reward_configs(
        baseline_config=baseline,
        tuned_config=tuned,
    )

    assert set(
        comparison.changed_field_names
    ) == {
        "new_area",
        "obstacle_collision",
        "step_cost",
    }
    assert len(comparison.unchanged_fields) == 8


def test_percentage_change_is_none_for_zero_baseline():
    baseline = RewardConfig(repeated_area=0.0)
    tuned = RewardConfig(repeated_area=-0.2)

    comparison = compare_reward_configs(
        baseline_config=baseline,
        tuned_config=tuned,
    )

    change = comparison.changed_fields[0]

    assert change.field == "repeated_area"
    assert change.absolute_change == pytest.approx(-0.2)
    assert change.percentage_change is None


def test_curriculum_profile_can_be_compared():
    baseline = RewardConfig()
    profile = CurriculumRewardTuner().resolve(0.0)

    comparison = compare_reward_configs(
        baseline_config=baseline,
        tuned_config=profile.reward_config,
    )

    assert comparison.changed_field_names == (
        "obstacle_collision",
    )

    change = comparison.changed_fields[0]

    assert change.tuned == pytest.approx(-1.25)
    assert change.absolute_change == pytest.approx(3.75)


def test_comparison_is_json_serializable():
    comparison = compare_reward_configs(
        baseline_config=RewardConfig(),
        tuned_config=RewardConfig(
            obstacle_collision=-1.0
        ),
    )

    encoded = comparison.to_json()
    decoded = json.loads(encoded)

    assert decoded["changed_field_names"] == [
        "obstacle_collision"
    ]
    assert decoded["changed_fields"][0][
        "tuned"
    ] == pytest.approx(-1.0)


def test_export_writes_json(tmp_path):
    comparison = compare_reward_configs(
        baseline_config=RewardConfig(),
        tuned_config=RewardConfig(
            obstacle_collision=-1.0
        ),
    )

    output = tmp_path / "nested" / "comparison.json"

    export_reward_tuning_comparison(
        comparison,
        output,
    )

    assert output.exists()

    decoded = json.loads(
        output.read_text(encoding="utf-8")
    )

    assert decoded["changed_field_names"] == [
        "obstacle_collision"
    ]


def test_export_requires_json_suffix(tmp_path):
    comparison = compare_reward_configs(
        baseline_config=RewardConfig(),
        tuned_config=RewardConfig(),
    )

    with pytest.raises(RewardTuningError):
        export_reward_tuning_comparison(
            comparison,
            tmp_path / "comparison.txt",
        )


def test_invalid_baseline_config_is_rejected():
    with pytest.raises(TypeError):
        compare_reward_configs(
            baseline_config="invalid",
            tuned_config=RewardConfig(),
        )


def test_invalid_tuned_config_is_rejected():
    with pytest.raises(TypeError):
        compare_reward_configs(
            baseline_config=RewardConfig(),
            tuned_config="invalid",
        )


def test_source_configs_are_not_modified():
    baseline = RewardConfig()
    tuned = RewardConfig(obstacle_collision=-1.0)

    baseline_before = baseline.to_dict()
    tuned_before = tuned.to_dict()

    compare_reward_configs(
        baseline_config=baseline,
        tuned_config=tuned,
    )

    assert baseline.to_dict() == baseline_before
    assert tuned.to_dict() == tuned_before