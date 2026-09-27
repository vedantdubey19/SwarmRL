import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

from sensors.metrics import MetricsTracker, SwarmMetrics


@dataclass(frozen=True)
class AuditReport:
    """Summary of one metric-history audit."""

    label: str
    total_steps: int
    start_explored_fraction: float
    final_explored_fraction: float
    exploration_gain: float
    mean_total_reward: float
    reward_standard_deviation: float
    cumulative_reward: float
    cumulative_new_cells: int
    total_drone_collisions: int
    total_obstacle_collisions: int
    total_targets_found: int
    total_boundary_violations: int
    mean_visible_targets: float
    mean_visible_obstacles: float
    mean_visible_drones: float

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible audit report."""
        return {
            "label": self.label,
            "total_steps": int(self.total_steps),
            "start_explored_fraction": float(
                self.start_explored_fraction
            ),
            "final_explored_fraction": float(
                self.final_explored_fraction
            ),
            "exploration_gain": float(
                self.exploration_gain
            ),
            "mean_total_reward": float(
                self.mean_total_reward
            ),
            "reward_standard_deviation": float(
                self.reward_standard_deviation
            ),
            "cumulative_reward": float(
                self.cumulative_reward
            ),
            "cumulative_new_cells": int(
                self.cumulative_new_cells
            ),
            "total_drone_collisions": int(
                self.total_drone_collisions
            ),
            "total_obstacle_collisions": int(
                self.total_obstacle_collisions
            ),
            "total_targets_found": int(
                self.total_targets_found
            ),
            "total_boundary_violations": int(
                self.total_boundary_violations
            ),
            "mean_visible_targets": float(
                self.mean_visible_targets
            ),
            "mean_visible_obstacles": float(
                self.mean_visible_obstacles
            ),
            "mean_visible_drones": float(
                self.mean_visible_drones
            ),
        }

    def to_json(self) -> str:
        """Encode the audit report as JSON."""
        return json.dumps(self.to_dict(), indent=2)


def _records(
    tracker: MetricsTracker,
) -> list[SwarmMetrics]:
    """Return tracker history or fail with a clear message."""
    if not tracker.history:
        raise ValueError(
            "Cannot audit an empty metrics tracker."
        )

    return tracker.history


def build_audit_report(
    tracker: MetricsTracker,
    label: str = "swarm_run",
) -> AuditReport:
    """Build an audit report from recorded swarm metrics."""
    if not label.strip():
        raise ValueError("Audit label must not be empty.")

    records = _records(tracker)

    rewards = [
        record.total_reward
        for record in records
    ]
    explored_fractions = [
        record.explored_fraction
        for record in records
    ]
    visible_targets = [
        record.visible_targets
        for record in records
    ]
    visible_obstacles = [
        record.visible_obstacles
        for record in records
    ]
    visible_drones = [
        record.visible_drones
        for record in records
    ]

    return AuditReport(
        label=label,
        total_steps=len(records),
        start_explored_fraction=explored_fractions[0],
        final_explored_fraction=explored_fractions[-1],
        exploration_gain=(
            explored_fractions[-1]
            - explored_fractions[0]
        ),
        mean_total_reward=mean(rewards),
        reward_standard_deviation=(
            pstdev(rewards)
            if len(rewards) > 1
            else 0.0
        ),
        cumulative_reward=sum(rewards),
        cumulative_new_cells=sum(
            record.newly_explored_cells
            for record in records
        ),
        total_drone_collisions=sum(
            record.drone_collisions
            for record in records
        ),
        total_obstacle_collisions=sum(
            record.obstacle_collisions
            for record in records
        ),
        total_targets_found=sum(
            record.targets_found
            for record in records
        ),
        total_boundary_violations=sum(
            record.boundary_violations
            for record in records
        ),
        mean_visible_targets=mean(visible_targets),
        mean_visible_obstacles=mean(
            visible_obstacles
        ),
        mean_visible_drones=mean(visible_drones),
    )


def compare_audit_reports(
    baseline: AuditReport,
    candidate: AuditReport,
) -> dict[str, Any]:
    """Compare a candidate experiment against a baseline."""
    return {
        "baseline_label": baseline.label,
        "candidate_label": candidate.label,
        "exploration_gain_delta": (
            candidate.exploration_gain
            - baseline.exploration_gain
        ),
        "final_explored_fraction_delta": (
            candidate.final_explored_fraction
            - baseline.final_explored_fraction
        ),
        "mean_reward_delta": (
            candidate.mean_total_reward
            - baseline.mean_total_reward
        ),
        "cumulative_reward_delta": (
            candidate.cumulative_reward
            - baseline.cumulative_reward
        ),
        "new_cells_delta": (
            candidate.cumulative_new_cells
            - baseline.cumulative_new_cells
        ),
        "drone_collisions_delta": (
            candidate.total_drone_collisions
            - baseline.total_drone_collisions
        ),
        "obstacle_collisions_delta": (
            candidate.total_obstacle_collisions
            - baseline.total_obstacle_collisions
        ),
        "targets_found_delta": (
            candidate.total_targets_found
            - baseline.total_targets_found
        ),
        "boundary_violations_delta": (
            candidate.total_boundary_violations
            - baseline.total_boundary_violations
        ),
    }


def export_audit_report(
    report: AuditReport,
    path: str | Path,
) -> Path:
    """Write one audit report to a JSON file."""
    output_path = Path(path)

    if output_path.suffix.lower() != ".json":
        raise ValueError(
            "Audit report path must end with .json."
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    output_path.write_text(
        report.to_json(),
        encoding="utf-8",
    )

    return output_path


def export_audit_comparison(
    comparison: dict[str, Any],
    path: str | Path,
) -> Path:
    """Write an audit comparison to a JSON file."""
    output_path = Path(path)

    if output_path.suffix.lower() != ".json":
        raise ValueError(
            "Audit comparison path must end with .json."
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    output_path.write_text(
        json.dumps(comparison, indent=2),
        encoding="utf-8",
    )

    return output_path