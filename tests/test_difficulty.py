import json

import pytest

from sensors.difficulty import (
    DifficultyLevel,
    DifficultyScaleError,
    ObstacleDifficultyScaler,
    resolve_obstacle_difficulty,
)
from sensors.rewards import RewardConfig


def test_progress_zero_resolves_easy_level():
    profile = ObstacleDifficultyScaler().resolve(0.0)

    assert profile.level_name == "easy"
    assert profile.level_index == 0
    assert profile.obstacle_count == 2
    assert profile.obstacle_speed_scale == pytest.approx(0.5)
    assert profile.reward_profile.stage_name == "easy"


def test_progress_half_resolves_moderate_level():
    profile = ObstacleDifficultyScaler().resolve(0.5)

    assert profile.level_name == "moderate"
    assert profile.level_index == 1
    assert profile.obstacle_count == 4
    assert profile.obstacle_speed_scale == pytest.approx(0.75)
    assert profile.reward_profile.stage_name == "moderate"


def test_progress_one_resolves_hard_level():
    profile = ObstacleDifficultyScaler().resolve(1.0)

    assert profile.level_name == "hard"
    assert profile.level_index == 2
    assert profile.obstacle_count == 6
    assert profile.obstacle_speed_scale == pytest.approx(1.0)
    assert profile.reward_profile.stage_name == "hard"


def test_obstacle_count_and_speed_increase():
    scaler = ObstacleDifficultyScaler()

    easy = scaler.resolve(0.0)
    moderate = scaler.resolve(0.5)
    hard = scaler.resolve(1.0)

    assert easy.obstacle_count < moderate.obstacle_count
    assert moderate.obstacle_count < hard.obstacle_count
    assert (
        easy.obstacle_speed_scale
        < moderate.obstacle_speed_scale
    )
    assert (
        moderate.obstacle_speed_scale
        < hard.obstacle_speed_scale
    )


def test_reward_config_matches_curriculum_tuner():
    profile = ObstacleDifficultyScaler().resolve(0.5)

    assert profile.reward_profile.reward_config.obstacle_collision == (
        pytest.approx(-3.0)
    )


def test_custom_base_reward_config_is_used():
    base = RewardConfig(
        new_area=2.0,
        obstacle_collision=-10.0,
        step_cost=-0.2,
    )

    profile = ObstacleDifficultyScaler(
        base_reward_config=base
    ).resolve(0.0)

    tuned = profile.reward_profile.reward_config

    assert tuned.obstacle_collision == pytest.approx(-2.5)
    assert tuned.new_area == base.new_area
    assert tuned.step_cost == base.step_cost
    assert base.obstacle_collision == -10.0


@pytest.mark.parametrize(
    "progress",
    [-0.01, 1.01],
)
def test_progress_outside_range_is_rejected(progress):
    with pytest.raises(DifficultyScaleError):
        ObstacleDifficultyScaler().resolve(progress)


def test_non_numeric_progress_is_rejected():
    with pytest.raises(TypeError):
        ObstacleDifficultyScaler().resolve("half")


def test_empty_levels_are_rejected():
    with pytest.raises(DifficultyScaleError):
        ObstacleDifficultyScaler(levels=())


def test_duplicate_level_names_are_rejected():
    from sensors.difficulty import DifficultyLevel

    with pytest.raises(DifficultyScaleError):
        ObstacleDifficultyScaler(
            levels=(
                DifficultyLevel("level", 1, 0.2, 0.2),
                DifficultyLevel("level", 2, 0.5, 0.5),
            )
        )


def test_decreasing_obstacle_counts_are_rejected():
    from sensors.difficulty import DifficultyLevel

    with pytest.raises(DifficultyScaleError):
        ObstacleDifficultyScaler(
            levels=(
                DifficultyLevel("first", 5, 0.5, 0.5),
                DifficultyLevel("second", 2, 0.8, 0.8),
            )
        )


def test_decreasing_speed_scales_are_rejected():
    from sensors.difficulty import DifficultyLevel

    with pytest.raises(DifficultyScaleError):
        ObstacleDifficultyScaler(
            levels=(
                DifficultyLevel("first", 2, 0.8, 0.5),
                DifficultyLevel("second", 4, 0.5, 0.8),
            )
        )


def test_decreasing_reward_scales_are_rejected():
    from sensors.difficulty import DifficultyLevel

    with pytest.raises(DifficultyScaleError):
        ObstacleDifficultyScaler(
            levels=(
                DifficultyLevel("first", 2, 0.5, 0.8),
                DifficultyLevel("second", 4, 0.9, 0.5),
            )
        )


def test_profile_is_json_serializable():
    profile = ObstacleDifficultyScaler().resolve(0.5)

    encoded = profile.to_json()
    decoded = json.loads(encoded)

    assert decoded["level_name"] == "moderate"
    assert decoded["obstacle_count"] == 4
    assert decoded["obstacle_speed_scale"] == pytest.approx(0.75)


def test_convenience_function_resolves_difficulty():
    profile = resolve_obstacle_difficulty(0.5)

    assert profile.level_name == "moderate"
    assert profile.obstacle_count == 4