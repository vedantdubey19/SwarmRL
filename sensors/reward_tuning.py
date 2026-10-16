from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sensors.rewards import RewardConfig


class RewardTuningError(ValueError):
    """Raised when reward configurations cannot be compared or exported."""


@dataclass(frozen=True)
class RewardFieldChange:
    """Change between baseline and tuned values for one reward field."""

    field: str
    baseline: float
    tuned: float
    absolute_change: float
    percentage_change: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "baseline": float(self.baseline),
            "tuned": float(self.tuned),
            "absolute_change": float(
                self.absolute_change
            ),
            "percentage_change": (
                None
                if self.percentage_change is None
                else float(self.percentage_change)
            ),
        }


@dataclass(frozen=True)
class RewardTuningComparison:
    """Comparison between a baseline and tuned reward configuration."""

    changed_fields: tuple[RewardFieldChange, ...]
    unchanged_fields: tuple[str, ...]

    @property
    def changed_field_names(self) -> tuple[str, ...]:
        return tuple(
            change.field
            for change in self.changed_fields
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "changed_fields": [
                change.to_dict()
                for change in self.changed_fields
            ],
            "changed_field_names": list(
                self.changed_field_names
            ),
            "unchanged_fields": list(
                self.unchanged_fields
            ),
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            indent=2,
            sort_keys=True,
        )


def _validate_config(
    config: Any,
    label: str,
) -> RewardConfig:
    if not isinstance(config, RewardConfig):
        raise TypeError(
            f"{label} must be a RewardConfig instance."
        )

    return config


def compare_reward_configs(
    baseline_config: RewardConfig,
    tuned_config: RewardConfig,
) -> RewardTuningComparison:
    """Compare two reward configurations field by field."""
    baseline = _validate_config(
        baseline_config,
        "baseline_config",
    )
    tuned = _validate_config(
        tuned_config,
        "tuned_config",
    )

    baseline_values = baseline.to_dict()
    tuned_values = tuned.to_dict()

    changed: list[RewardFieldChange] = []
    unchanged: list[str] = []

    for field in baseline_values:
        baseline_value = baseline_values[field]
        tuned_value = tuned_values[field]

        if baseline_value == tuned_value:
            unchanged.append(field)
            continue

        absolute_change = (
            tuned_value - baseline_value
        )

        if baseline_value == 0.0:
            percentage_change = None
        else:
            percentage_change = (
                absolute_change
                / baseline_value
                * 100.0
            )

        changed.append(
            RewardFieldChange(
                field=field,
                baseline=baseline_value,
                tuned=tuned_value,
                absolute_change=absolute_change,
                percentage_change=(
                    percentage_change
                ),
            )
        )

    return RewardTuningComparison(
        changed_fields=tuple(changed),
        unchanged_fields=tuple(unchanged),
    )


def export_reward_tuning_comparison(
    comparison: RewardTuningComparison,
    output_path: Path | str,
) -> None:
    """Export a reward comparison as formatted JSON."""
    if not isinstance(
        comparison,
        RewardTuningComparison,
    ):
        raise TypeError(
            "comparison must be a "
            "RewardTuningComparison."
        )

    output = Path(output_path)

    if output.suffix.lower() != ".json":
        raise RewardTuningError(
            "Comparison output path must have a .json suffix."
        )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
        comparison.to_json() + "\n",
        encoding="utf-8",
    )