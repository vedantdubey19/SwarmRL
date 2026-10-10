from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from sensors.rewards import RewardConfig


class CurriculumRewardError(ValueError):
    """Raised when curriculum reward configuration is invalid."""


@dataclass(frozen=True)
class CurriculumRewardStage:
    """Obstacle-reward settings for one curriculum stage."""

    name: str
    obstacle_penalty_scale: float

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise CurriculumRewardError(
                "Stage name must be a non-empty string."
            )

        if not isinstance(
            self.obstacle_penalty_scale,
            (int, float),
        ):
            raise TypeError(
                "obstacle_penalty_scale must be numeric."
            )

        if not 0.0 <= self.obstacle_penalty_scale <= 1.0:
            raise CurriculumRewardError(
                "obstacle_penalty_scale must be between 0 and 1."
            )


DEFAULT_CURRICULUM_STAGES = (
    CurriculumRewardStage(
        name="easy",
        obstacle_penalty_scale=0.25,
    ),
    CurriculumRewardStage(
        name="moderate",
        obstacle_penalty_scale=0.60,
    ),
    CurriculumRewardStage(
        name="full",
        obstacle_penalty_scale=1.0,
    ),
)


@dataclass(frozen=True)
class CurriculumRewardProfile:
    """Reward configuration resolved for one curriculum stage."""

    stage_name: str
    stage_index: int
    progress: float
    obstacle_penalty_scale: float
    reward_config: RewardConfig

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_name": self.stage_name,
            "stage_index": self.stage_index,
            "progress": float(self.progress),
            "obstacle_penalty_scale": float(
                self.obstacle_penalty_scale
            ),
            "reward_config": self.reward_config.to_dict(),
        }


class CurriculumRewardTuner:
    """Resolve reward settings from a curriculum progress value.

    The tuner scales only `obstacle_collision`. All other configured
    reward components retain their original values.
    """

    def __init__(
        self,
        base_config: RewardConfig | None = None,
        stages: tuple[CurriculumRewardStage, ...] = (
            DEFAULT_CURRICULUM_STAGES
        ),
    ) -> None:
        self.base_config = base_config or RewardConfig()
        self.stages = tuple(stages)

        if not self.stages:
            raise CurriculumRewardError(
                "At least one curriculum stage is required."
            )

        if any(
            not isinstance(stage, CurriculumRewardStage)
            for stage in self.stages
        ):
            raise TypeError(
                "Every stage must be a CurriculumRewardStage."
            )

        if len(
            {stage.name for stage in self.stages}
        ) != len(self.stages):
            raise CurriculumRewardError(
                "Curriculum stage names must be unique."
            )

        scales = [
            stage.obstacle_penalty_scale
            for stage in self.stages
        ]

        if any(
            earlier > later
            for earlier, later in zip(
                scales,
                scales[1:],
            )
        ):
            raise CurriculumRewardError(
                "Obstacle penalty scales must be "
                "non-decreasing across stages."
            )

    def resolve(
        self,
        progress: float,
    ) -> CurriculumRewardProfile:
        """Resolve the stage and reward config for progress in [0, 1]."""
        if not isinstance(progress, (int, float)):
            raise TypeError(
                "progress must be numeric."
            )

        progress = float(progress)

        if not 0.0 <= progress <= 1.0:
            raise CurriculumRewardError(
                "progress must be between 0 and 1."
            )

        stage_count = len(self.stages)

        # Progress 1.0 selects the final stage exactly.
        stage_index = min(
            int(progress * stage_count),
            stage_count - 1,
        )

        stage = self.stages[stage_index]

        tuned_config = replace(
            self.base_config,
            obstacle_collision=(
                self.base_config.obstacle_collision
                * stage.obstacle_penalty_scale
            ),
        )

        return CurriculumRewardProfile(
            stage_name=stage.name,
            stage_index=stage_index,
            progress=progress,
            obstacle_penalty_scale=(
                stage.obstacle_penalty_scale
            ),
            reward_config=tuned_config,
        )