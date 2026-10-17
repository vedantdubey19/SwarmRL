from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sensors.difficulty import (
    ObstacleDifficultyProfile,
)
from sensors.reward_tuning import (
    RewardTuningComparison,
)
from sensors.rewards import RewardConfig


class VisualsIntegrationError(ValueError):
    """Raised when visuals integration inputs are invalid."""


@dataclass(frozen=True)
class VisualsIntegrationCheck:
    """Readiness result for visuals integration support."""

    ready: bool
    issues: tuple[str, ...]
    reward_config: RewardConfig
    comparison: RewardTuningComparison
    difficulty_profile: ObstacleDifficultyProfile | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "issues": list(self.issues),
            "reward_config": self.reward_config.to_dict(),
            "changed_field_names": list(
                self.comparison.changed_field_names
            ),
            "difficulty_level": (
                None
                if self.difficulty_profile is None
                else self.difficulty_profile.level_name
            ),
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            indent=2,
            sort_keys=True,
        )


def _validate_reward_config(
    reward_config: Any,
) -> RewardConfig:
    if not isinstance(reward_config, RewardConfig):
        raise TypeError(
            "reward_config must be a RewardConfig instance."
        )

    return reward_config


def _validate_comparison(
    comparison: Any,
) -> RewardTuningComparison:
    if not isinstance(
        comparison,
        RewardTuningComparison,
    ):
        raise TypeError(
            "comparison must be a "
            "RewardTuningComparison instance."
        )

    return comparison


def _validate_difficulty_profile(
    difficulty_profile: Any,
) -> ObstacleDifficultyProfile | None:
    if difficulty_profile is None:
        return None

    if not isinstance(
        difficulty_profile,
        ObstacleDifficultyProfile,
    ):
        raise TypeError(
            "difficulty_profile must be an "
            "ObstacleDifficultyProfile instance or None."
        )

    return difficulty_profile


def validate_visuals_integration(
    reward_config: RewardConfig,
    comparison: RewardTuningComparison,
    difficulty_profile: ObstacleDifficultyProfile | None = None,
) -> VisualsIntegrationCheck:
    """Validate readiness for visuals integration."""
    reward_config = _validate_reward_config(
        reward_config
    )
    comparison = _validate_comparison(
        comparison
    )
    difficulty_profile = (
        _validate_difficulty_profile(
            difficulty_profile
        )
    )

    issues: list[str] = []

    if not comparison.changed_fields:
        issues.append(
            "Reward tuning comparison has no changed fields."
        )

    obstacle_changes = [
        change
        for change in comparison.changed_fields
        if change.field == "obstacle_collision"
    ]

    if not obstacle_changes:
        issues.append(
            "Reward tuning comparison does not change "
            "obstacle_collision."
        )
    else:
        obstacle_change = obstacle_changes[0]

        if obstacle_change.tuned > 0.0:
            issues.append(
                "Tuned obstacle_collision penalty must be "
                "zero or negative."
            )

    if difficulty_profile is not None:
        if (
            difficulty_profile.reward_profile.reward_config
            != reward_config
        ):
            issues.append(
                "Difficulty profile reward configuration "
                "does not match the supplied reward "
                "configuration."
            )

    return VisualsIntegrationCheck(
        ready=not issues,
        issues=tuple(issues),
        reward_config=reward_config,
        comparison=comparison,
        difficulty_profile=difficulty_profile,
    )


def export_visuals_integration_check(
    check: VisualsIntegrationCheck,
    output_path: Path | str,
) -> None:
    """Export an integration check as formatted JSON."""
    if not isinstance(
        check,
        VisualsIntegrationCheck,
    ):
        raise TypeError(
            "check must be a VisualsIntegrationCheck."
        )

    output = Path(output_path)

    if output.suffix.lower() != ".json":
        raise VisualsIntegrationError(
            "Integration check output path must have a "
            ".json suffix."
        )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
        check.to_json() + "\n",
        encoding="utf-8",
    )