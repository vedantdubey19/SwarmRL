import pytest

from sensors.curriculum import (
    CurriculumRewardError,
    CurriculumRewardStage,
    CurriculumRewardTuner,
)
from sensors.rewards import RewardConfig


def test_default_tuner_uses_easy_stage_at_start():
    profile = CurriculumRewardTuner().resolve(0.0)

    assert profile.stage_name == "easy"
    assert profile.stage_index == 0
    assert profile.progress == 0.0
    assert profile.obstacle_penalty_scale == 0.25
    assert profile.reward_config.obstacle_collision == pytest.approx(
        -1.25
    )


def test_default_tuner_advances_through_stages():
    tuner = CurriculumRewardTuner()

    easy = tuner.resolve(0.0)
    moderate = tuner.resolve(0.34)
    full = tuner.resolve(1.0)

    assert easy.stage_name == "easy"
    assert moderate.stage_name == "moderate"
    assert full.stage_name == "full"
    assert full.reward_config.obstacle_collision == pytest.approx(
        -5.0
    )


def test_only_obstacle_penalty_changes():
    base = RewardConfig(
        new_area=2.0,
        drone_collision=-7.0,
        obstacle_collision=-8.0,
        step_cost=-0.2,
    )

    profile = CurriculumRewardTuner(
        base_config=base
    ).resolve(0.0)

    tuned = profile.reward_config

    assert tuned.obstacle_collision == pytest.approx(-2.0)
    assert tuned.new_area == base.new_area
    assert tuned.drone_collision == base.drone_collision
    assert tuned.step_cost == base.step_cost
    assert base.obstacle_collision == -8.0


def test_custom_stages_can_be_supplied():
    stages = (
        CurriculumRewardStage("intro", 0.1),
        CurriculumRewardStage("advanced", 0.8),
    )

    tuner = CurriculumRewardTuner(
        base_config=RewardConfig(obstacle_collision=-10.0),
        stages=stages,
    )

    first = tuner.resolve(0.2)
    second = tuner.resolve(0.8)

    assert first.stage_name == "intro"
    assert first.reward_config.obstacle_collision == pytest.approx(
        -1.0
    )
    assert second.stage_name == "advanced"
    assert second.reward_config.obstacle_collision == pytest.approx(
        -8.0
    )


@pytest.mark.parametrize(
    "progress",
    [-0.01, 1.01],
)
def test_progress_outside_range_is_rejected(progress):
    with pytest.raises(CurriculumRewardError):
        CurriculumRewardTuner().resolve(progress)


def test_non_numeric_progress_is_rejected():
    with pytest.raises(TypeError):
        CurriculumRewardTuner().resolve("half")


@pytest.mark.parametrize(
    "scale",
    [-0.1, 1.1],
)
def test_stage_rejects_scale_outside_range(scale):
    with pytest.raises(CurriculumRewardError):
        CurriculumRewardStage(
            name="invalid",
            obstacle_penalty_scale=scale,
        )


def test_stage_rejects_empty_name():
    with pytest.raises(CurriculumRewardError):
        CurriculumRewardStage(
            name=" ",
            obstacle_penalty_scale=0.5,
        )


def test_tuner_requires_at_least_one_stage():
    with pytest.raises(CurriculumRewardError):
        CurriculumRewardTuner(stages=())


def test_tuner_rejects_duplicate_stage_names():
    with pytest.raises(CurriculumRewardError):
        CurriculumRewardTuner(
            stages=(
                CurriculumRewardStage("stage", 0.2),
                CurriculumRewardStage("stage", 0.8),
            )
        )


def test_tuner_rejects_decreasing_penalty_scales():
    with pytest.raises(CurriculumRewardError):
        CurriculumRewardTuner(
            stages=(
                CurriculumRewardStage("first", 0.8),
                CurriculumRewardStage("second", 0.2),
            )
        )


def test_profile_is_json_serializable():
    import json

    profile = CurriculumRewardTuner().resolve(0.5)

    encoded = json.dumps(profile.to_dict())
    decoded = json.loads(encoded)

    assert decoded["stage_name"] == "moderate"
    assert decoded["reward_config"]["obstacle_collision"] == (
        pytest.approx(-3.0)
    )