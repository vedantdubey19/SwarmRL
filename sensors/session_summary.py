import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class TelemetrySummaryError(ValueError):
    """Raised when telemetry-session input cannot be summarized."""


@dataclass(frozen=True)
class TelemetrySessionSummary:
    """Aggregate summary of one telemetry JSON-lines session."""

    total_records: int
    first_step: int
    last_step: int
    start_explored_fraction: float
    final_explored_fraction: float
    exploration_gain: float
    cumulative_total_reward: float
    mean_total_reward: float
    cumulative_newly_explored_cells: int
    total_drone_collisions: int
    total_obstacle_collisions: int
    total_targets_found: int
    total_boundary_violations: int

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible summary dictionary."""
        return {
            "total_records": self.total_records,
            "first_step": self.first_step,
            "last_step": self.last_step,
            "start_explored_fraction": (
                self.start_explored_fraction
            ),
            "final_explored_fraction": (
                self.final_explored_fraction
            ),
            "exploration_gain": self.exploration_gain,
            "cumulative_total_reward": (
                self.cumulative_total_reward
            ),
            "mean_total_reward": self.mean_total_reward,
            "cumulative_newly_explored_cells": (
                self.cumulative_newly_explored_cells
            ),
            "total_drone_collisions": (
                self.total_drone_collisions
            ),
            "total_obstacle_collisions": (
                self.total_obstacle_collisions
            ),
            "total_targets_found": self.total_targets_found,
            "total_boundary_violations": (
                self.total_boundary_violations
            ),
        }

    def to_json(self) -> str:
        """Serialize the summary as readable JSON."""
        return json.dumps(
            self.to_dict(),
            indent=2,
            sort_keys=True,
        )


def _validate_metrics(
    message: Any,
    line_number: int,
) -> dict[str, Any]:
    """Return validated telemetry metrics for one JSON-lines record."""
    if not isinstance(message, dict):
        raise TelemetrySummaryError(
            f"Line {line_number} must contain a JSON object."
        )

    if message.get("type") != "swarm_metrics":
        raise TelemetrySummaryError(
            f"Line {line_number} must have type "
            "'swarm_metrics'."
        )

    metrics = message.get("metrics")

    if not isinstance(metrics, dict):
        raise TelemetrySummaryError(
            f"Line {line_number} metrics must be an object."
        )

    step = metrics.get("step")

    if isinstance(step, bool) or not isinstance(step, int):
        raise TelemetrySummaryError(
            f"Line {line_number} metrics step must be an integer."
        )

    return metrics


def _number(
    metrics: dict[str, Any],
    name: str,
    line_number: int,
    default: float | int = 0,
) -> float | int:
    """Read a non-boolean numeric metric value."""
    value = metrics.get(name, default)

    if isinstance(value, bool) or not isinstance(
        value,
        (int, float),
    ):
        raise TelemetrySummaryError(
            f"Line {line_number} metric '{name}' "
            "must be numeric."
        )

    return value


def summarize_telemetry_session(
    jsonl_path: Path | str,
) -> TelemetrySessionSummary:
    """Read one JSON-lines telemetry session and aggregate its metrics."""
    jsonl_path = Path(jsonl_path)

    if jsonl_path.suffix.lower() != ".jsonl":
        raise ValueError(
            "jsonl_path must have a .jsonl suffix."
        )

    if not jsonl_path.exists():
        raise FileNotFoundError(jsonl_path)

    records: list[dict[str, Any]] = []

    with jsonl_path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            stripped = line.strip()

            if not stripped:
                continue

            try:
                message = json.loads(stripped)
            except json.JSONDecodeError as error:
                raise TelemetrySummaryError(
                    f"Line {line_number} is not valid JSON."
                ) from error

            records.append(
                _validate_metrics(message, line_number)
            )

    if not records:
        raise TelemetrySummaryError(
            "Telemetry JSON-lines file contains no records."
        )

    first_metrics = records[0]
    last_metrics = records[-1]

    total_reward = sum(
        float(_number(metrics, "total_reward", index))
        for index, metrics in enumerate(records, start=1)
    )

    return TelemetrySessionSummary(
        total_records=len(records),
        first_step=int(first_metrics["step"]),
        last_step=int(last_metrics["step"]),
        start_explored_fraction=float(
            _number(
                first_metrics,
                "explored_fraction",
                1,
            )
        ),
        final_explored_fraction=float(
            _number(
                last_metrics,
                "explored_fraction",
                len(records),
            )
        ),
        exploration_gain=(
            float(
                _number(
                    last_metrics,
                    "explored_fraction",
                    len(records),
                )
            )
            - float(
                _number(
                    first_metrics,
                    "explored_fraction",
                    1,
                )
            )
        ),
        cumulative_total_reward=total_reward,
        mean_total_reward=total_reward / len(records),
        cumulative_newly_explored_cells=sum(
            int(
                _number(
                    metrics,
                    "newly_explored_cells",
                    index,
                )
            )
            for index, metrics in enumerate(records, start=1)
        ),
        total_drone_collisions=sum(
            int(
                _number(
                    metrics,
                    "drone_collisions",
                    index,
                )
            )
            for index, metrics in enumerate(records, start=1)
        ),
        total_obstacle_collisions=sum(
            int(
                _number(
                    metrics,
                    "obstacle_collisions",
                    index,
                )
            )
            for index, metrics in enumerate(records, start=1)
        ),
        total_targets_found=sum(
            int(
                _number(
                    metrics,
                    "targets_found",
                    index,
                )
            )
            for index, metrics in enumerate(records, start=1)
        ),
        total_boundary_violations=sum(
            int(
                _number(
                    metrics,
                    "boundary_violations",
                    index,
                )
            )
            for index, metrics in enumerate(records, start=1)
        ),
    )


def export_session_summary(
    summary: TelemetrySessionSummary,
    output_path: Path | str,
) -> Path:
    """Atomically write a telemetry-session summary JSON file."""
    if not isinstance(summary, TelemetrySessionSummary):
        raise TypeError(
            "summary must be a TelemetrySessionSummary instance."
        )

    output_path = Path(output_path)

    if output_path.suffix.lower() != ".json":
        raise ValueError(
            "output_path must have a .json suffix."
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=output_path.parent,
        prefix=f".{output_path.stem}_",
        suffix=".tmp",
        text=True,
    )

    temporary_path = Path(temporary_name)

    try:
        with os.fdopen(
            file_descriptor,
            "w",
            encoding="utf-8",
        ) as file:
            file.write(summary.to_json())
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())

        temporary_path.replace(output_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise

    return output_path


def summarize_and_export_session(
    jsonl_path: Path | str,
    output_path: Path | str,
) -> TelemetrySessionSummary:
    """Build and atomically export a summary from a telemetry session."""
    summary = summarize_telemetry_session(jsonl_path)
    export_session_summary(summary, output_path)

    return summary