from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from sensors.curriculum import (
    CurriculumRewardProfile,
    CurriculumRewardTuner,
)
from sensors.rewards import RewardConfig


class DifficultyScaleError(ValueError):
    """Raised when obstacle difficulty cannot be resolved."""


@dataclass(frozen=True)
class DifficultyLevel:
    """Obstacle difficulty settings for one curriculum level."""

    name: str
    obstacle_count: int
    obstacle_speed_scale: float
    reward_scale: float

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise DifficultyScaleError(
                "Difficulty level name must be a non-empty string."
            )

        if not isinstance(self.obstacle_count, int):
            raise TypeError(
                "obstacle_count must be an integer."
            )

        if self.obstacle_count < 0:
            raise DifficultyScaleError(
                "obstacle_count must not be negative."
            )

        if not isinstance(
            self.obstacle_speed_scale,
            (int, float),
        ):
            raise TypeError(
                "obstacle_speed_scale must be numeric."
            )

        if not 0.0 <= self.obstacle_speed_scale <= 1.0:
            raise DifficultyScaleError(
                "obstacle_speed_scale must be between 0 and 1."
            )

        if not isinstance(self.reward_scale, (int, float)):
            raise TypeError(
                "reward_scale must be numeric."
            )

        if not 0.0 <= self.reward_scale <= 1.0:
            raise DifficultyScaleError(
                "reward_scale must be between 0 and 1."
            )


DEFAULT_DIFFICULTY_LEVELS = (
    DifficultyLevel(
        name="easy",
        obstacle_count=2,
        obstacle_speed_scale=0.5,
        reward_scale=0.25,
    ),
    DifficultyLevel(
        name="moderate",
        obstacle_count=4,
        obstacle_speed_scale=0.75,
        reward_scale=0.60,
    ),
    DifficultyLevel(
        name="hard",
        obstacle_count=6,
        obstacle_speed_scale=1.0,
        reward_scale=1.0,
    ),
)


@dataclass(frozen=True)
class ObstacleDifficultyProfile:
    """Resolved difficulty and reward settings for one progress value."""

    level_name: str
    level_index: int
    progress: float
    obstacle_count: int
    obstacle_speed_scale: float
    reward_profile: CurriculumRewardProfile

    def to_dict(self) -> dict[str, Any]:
        return {
            "level_name": self.level_name,
            "level_index": self.level_index,
            "progress": float(self.progress),
            "obstacle_count": self.obstacle_count,
            "obstacle_speed_scale": float(
                self.obstacle_speed_scale
            ),
            "reward_profile": self.reward_profile.to_dict(),
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            indent=2,
            sort_keys=True,
        )


class ObstacleDifficultyScaler:
    """Resolve obstacle difficulty from normalized training progress."""

    def __init__(
        self,
        base_reward_config: RewardConfig | None = None,
        levels: tuple[DifficultyLevel, ...] = (
            DEFAULT_DIFFICULTY_LEVELS
        ),
    ) -> None:
        self.base_reward_config = (
            base_reward_config or RewardConfig()
        )
        self.levels = tuple(levels)

        if not self.levels:
            raise DifficultyScaleError(
                "At least one difficulty level is required."
            )

        if any(
            not isinstance(level, DifficultyLevel)
            for level in self.levels
        ):
            raise TypeError(
                "Every difficulty level must be a "
                "DifficultyLevel instance."
            )

        if len(
            {level.name for level in self.levels}
        ) != len(self.levels):
            raise DifficultyScaleError(
                "Difficulty level names must be unique."
            )

        counts = [
            level.obstacle_count
            for level in self.levels
        ]

        if any(
            earlier > later
            for earlier, later in zip(
                counts,
                counts[1:],
            )
        ):
            raise DifficultyScaleError(
                "Obstacle counts must be non-decreasing."
            )

        speeds = [
            level.obstacle_speed_scale
            for level in self.levels
        ]

        if any(
            earlier > later
            for earlier, later in zip(
                speeds,
                speeds[1:],
            )
        ):
            raise DifficultyScaleError(
                "Obstacle speed scales must be non-decreasing."
            )

        rewards = [
            level.reward_scale
            for level in self.levels
        ]

        if any(
            earlier > later
            for earlier, later in zip(
                rewards,
                rewards[1:],
            )
        ):
            raise DifficultyScaleError(
                "Reward scales must be non-decreasing."
            )

        self._reward_tuner = CurriculumRewardTuner(
            base_config=self.base_reward_config,
            stages=tuple(
                CurriculumRewardStage(
                    name=level.name,
                    obstacle_penalty_scale=level.reward_scale,
                )
                for level in self.levels
            ),
        )

    def resolve(
        self,
        progress: float,
    ) -> ObstacleDifficultyProfile:
        """Resolve difficulty for progress in the inclusive range 0 to 1."""
        if not isinstance(progress, (int, float)):
            raise TypeError(
                "progress must be numeric."
            )

        progress = float(progress)

        if not 0.0 <= progress <= 1.0:
            raise DifficultyScaleError(
                "progress must be between 0 and 1."
            )

        level_count = len(self.levels)

        level_index = min(
            int(progress * level_count),
            level_count - 1,
        )

        level = self.levels[level_index]
        reward_profile = self._reward_tuner.resolve(
            progress
        )

        return ObstacleDifficultyProfile(
            level_name=level.name,
            level_index=level_index,
            progress=progress,
            obstacle_count=level.obstacle_count,
            obstacle_speed_scale=(
                level.obstacle_speed_scale
            ),
            reward_profile=reward_profile,
        )


from sensors.curriculum import CurriculumRewardStage


def resolve_obstacle_difficulty(
    progress: float,
    base_reward_config: RewardConfig | None = None,
) -> ObstacleDifficultyProfile:
    """Resolve default obstacle difficulty for one progress value."""
    return ObstacleDifficultyScaler(
        base_reward_config=base_reward_config
    ).resolve(progress)