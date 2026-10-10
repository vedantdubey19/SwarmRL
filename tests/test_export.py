import csv
import json

import pytest

from sensors.export import (
    CSV_FIELDS,
    export_metrics_csv,
    export_metrics_json,
    export_summary_json,
    metric_records,
    metrics_from_records,
)
from sensors.metrics import (
    AgentMetrics,
    MetricsTracker,
)


def make_tracker() -> MetricsTracker:
    tracker = MetricsTracker()

    tracker.record(
        step=1,
        episode=0,
        explored_fraction=0.1,
        agent_metrics={
            "drone_000": AgentMetrics(
                reward=2.0,
                new_cells=3,
                visible_targets=1,
                target_found=True,
            ),
            "drone_001": AgentMetrics(
                reward=-1.0,
                new_cells=1,
                drone_collision=True,
            ),
        },
    )

    tracker.record(
        step=2,
        episode=0,
        explored_fraction=0.25,
        agent_metrics={
            "drone_000": AgentMetrics(
                reward=1.5,
                new_cells=2,
                visible_obstacles=1,
            ),
            "drone_001": AgentMetrics(
                reward=-0.5,
                new_cells=0,
                boundary_violation=True,
            ),
        },
    )

    return tracker


def test_metric_records_returns_history():
    tracker = make_tracker()

    records = metric_records(tracker)

    assert len(records) == 2
    assert records[0]["step"] == 1
    assert records[1]["explored_fraction"] == 0.25
    assert "agents" in records[0]


def test_metric_records_can_exclude_agents():
    tracker = make_tracker()

    records = metric_records(
        tracker,
        include_agents=False,
    )

    assert len(records) == 2
    assert "agents" not in records[0]


def test_export_metrics_json_creates_file(tmp_path):
    tracker = make_tracker()
    path = tmp_path / "exports" / "metrics.json"

    result = export_metrics_json(
        tracker,
        path,
        include_agents=True,
    )

    assert result == path
    assert path.exists()

    payload = json.loads(
        path.read_text(encoding="utf-8")
    )

    assert len(payload["records"]) == 2
    assert payload["records"][0]["agents"][
        "drone_000"
    ]["new_cells"] == 3
    assert payload["summary"]["total_steps"] == 2


def test_export_metrics_json_can_exclude_agents(tmp_path):
    tracker = make_tracker()
    path = tmp_path / "metrics.json"

    export_metrics_json(
        tracker,
        path,
        include_agents=False,
    )

    payload = json.loads(
        path.read_text(encoding="utf-8")
    )

    assert "agents" not in payload["records"][0]


def test_export_metrics_csv_creates_tabular_file(tmp_path):
    tracker = make_tracker()
    path = tmp_path / "metrics.csv"

    result = export_metrics_csv(tracker, path)

    assert result == path
    assert path.exists()

    with path.open(
        newline="",
        encoding="utf-8",
    ) as file:
        rows = list(csv.DictReader(file))

    assert len(rows) == 2
    assert list(rows[0].keys()) == CSV_FIELDS
    assert rows[0]["step"] == "1"
    assert rows[1]["explored_fraction"] == "0.25"
    assert rows[0]["newly_explored_cells"] == "4"


def test_export_summary_json_creates_file(tmp_path):
    tracker = make_tracker()
    path = tmp_path / "summary.json"

    result = export_summary_json(tracker, path)

    assert result == path
    assert path.exists()

    summary = json.loads(
        path.read_text(encoding="utf-8")
    )

    assert summary["total_steps"] == 2
    assert summary["final_explored_fraction"] == 0.25
    assert summary["cumulative_new_cells"] == 6


def test_empty_tracker_export_is_valid(tmp_path):
    tracker = MetricsTracker()
    path = tmp_path / "empty.json"

    export_metrics_json(tracker, path)

    payload = json.loads(
        path.read_text(encoding="utf-8")
    )

    assert payload["records"] == []
    assert payload["summary"]["total_steps"] == 0


def test_metrics_from_records_rebuilds_basic_metrics():
    records = [
        {
            "step": 1,
            "episode": 2,
            "explored_fraction": 0.1,
        },
        {
            "step": 2,
            "episode": 2,
            "explored_fraction": 0.2,
        },
    ]

    metrics = metrics_from_records(records)

    assert len(metrics) == 2
    assert metrics[0].step == 1
    assert metrics[0].episode == 2
    assert metrics[1].explored_fraction == 0.2


def test_metrics_from_records_rejects_missing_step():
    with pytest.raises(ValueError):
        metrics_from_records(
            [
                {
                    "episode": 0,
                }
            ]
        )


def test_json_export_requires_json_suffix(tmp_path):
    tracker = make_tracker()

    with pytest.raises(ValueError):
        export_metrics_json(
            tracker,
            tmp_path / "metrics.csv",
        )


def test_csv_export_requires_csv_suffix(tmp_path):
    tracker = make_tracker()

    with pytest.raises(ValueError):
        export_metrics_csv(
            tracker,
            tmp_path / "metrics.json",
        )


def test_summary_export_requires_json_suffix(tmp_path):
    tracker = make_tracker()

    with pytest.raises(ValueError):
        export_summary_json(
            tracker,
            tmp_path / "summary.txt",
        )