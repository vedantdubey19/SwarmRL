import csv
import json
from pathlib import Path
from typing import Any

from sensors.metrics import MetricsTracker, SwarmMetrics


CSV_FIELDS = [
    "step",
    "episode",
    "active_agents",
    "explored_fraction",
    "total_reward",
    "mean_reward",
    "newly_explored_cells",
    "drone_collisions",
    "obstacle_collisions",
    "targets_found",
    "boundary_violations",
    "visible_targets",
    "visible_obstacles",
    "visible_drones",
]


def _output_path(
    path: str | Path,
    expected_suffix: str,
) -> Path:
    """Validate and return an output path."""
    result = Path(path)

    if not result.name:
        raise ValueError(
            "Output path must include a file name."
        )

    if result.suffix.lower() != expected_suffix:
        raise ValueError(
            f"Output path must end with {expected_suffix}."
        )

    result.parent.mkdir(parents=True, exist_ok=True)

    return result


def metric_records(
    tracker: MetricsTracker,
    include_agents: bool = True,
) -> list[dict[str, Any]]:
    """Convert tracker history into JSON-friendly records."""
    return [
        record.to_dict(include_agents=include_agents)
        for record in tracker.history
    ]


def export_metrics_json(
    tracker: MetricsTracker,
    path: str | Path,
    include_agents: bool = True,
) -> Path:
    """Export complete metric history as JSON."""
    output_path = _output_path(path, ".json")

    payload = {
        "records": metric_records(
            tracker,
            include_agents=include_agents,
        ),
        "summary": tracker.summary(),
    }

    output_path.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )

    return output_path


def export_metrics_csv(
    tracker: MetricsTracker,
    path: str | Path,
) -> Path:
    """Export aggregate step metrics as CSV."""
    output_path = _output_path(path, ".csv")

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=CSV_FIELDS,
        )
        writer.writeheader()

        for record in tracker.history:
            row = record.to_dict(include_agents=False)

            writer.writerow(
                {
                    field: row[field]
                    for field in CSV_FIELDS
                }
            )

    return output_path


def export_summary_json(
    tracker: MetricsTracker,
    path: str | Path,
) -> Path:
    """Export aggregate tracker summary as JSON."""
    output_path = _output_path(path, ".json")

    output_path.write_text(
        json.dumps(tracker.summary(), indent=2),
        encoding="utf-8",
    )

    return output_path


def metrics_from_records(
    records: list[dict[str, Any]],
) -> list[SwarmMetrics]:
    """Rebuild basic swarm metrics from exported records."""
    metrics = []

    for record in records:
        if "step" not in record:
            raise ValueError(
                "Every metric record must contain step."
            )

        metrics.append(
            SwarmMetrics(
                step=int(record["step"]),
                episode=int(record.get("episode", 0)),
                explored_fraction=float(
                    record.get(
                        "explored_fraction",
                        0.0,
                    )
                ),
            )
        )

    return metrics