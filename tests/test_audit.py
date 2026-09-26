import json

import pytest

from sensors.audit import (
    AuditReport,
    build_audit_report,
    compare_audit_reports,
    export_audit_comparison,
    export_audit_report,
)
from sensors.metrics import (
    AgentMetrics,
    MetricsTracker,
)


def make_tracker() -> MetricsTracker:
    tracker = MetricsTracker()

    tracker.record(
        step=1,
        explored_fraction=0.10,
        agent_metrics={
            "drone_000": AgentMetrics(
                reward=2.0,
                new_cells=3,
                visible_targets=1,
                visible_obstacles=2,
                visible_drones=1,
                target_found=True,
            ),
            "drone_001": AgentMetrics(
                reward=-1.0,
                new_cells=1,
                visible_obstacles=1,
                visible_drones=1,
                drone_collision=True,
            ),
        },
    )

    tracker.record(
        step=2,
        explored_fraction=0.25,
        agent_metrics={
            "drone_000": AgentMetrics(
                reward=3.0,
                new_cells=4,
                visible_targets=1,
                visible_obstacles=1,
                visible_drones=1,
            ),
            "drone_001": AgentMetrics(
                reward=-2.0,
                new_cells=0,
                visible_drones=1,
                boundary_violation=True,
            ),
        },
    )

    tracker.record(
        step=3,
        explored_fraction=0.40,
        agent_metrics={
            "drone_000": AgentMetrics(
                reward=4.0,
                new_cells=2,
                visible_targets=2,
                visible_obstacles=1,
                visible_drones=1,
                target_found=True,
            ),
            "drone_001": AgentMetrics(
                reward=-3.0,
                new_cells=0,
                visible_obstacles=1,
                visible_drones=1,
                obstacle_collision=True,
            ),
        },
    )

    return tracker


def test_build_audit_report_aggregates_metrics():
    report = build_audit_report(
        make_tracker(),
        label="baseline",
    )

    assert report.label == "baseline"
    assert report.total_steps == 3
    assert report.start_explored_fraction == pytest.approx(
        0.10
    )
    assert report.final_explored_fraction == pytest.approx(
        0.40
    )
    assert report.exploration_gain == pytest.approx(0.30)
    assert report.mean_total_reward == pytest.approx(1.0)
    assert report.cumulative_reward == pytest.approx(3.0)
    assert report.cumulative_new_cells == 10
    assert report.total_drone_collisions == 1
    assert report.total_obstacle_collisions == 1
    assert report.total_targets_found == 2
    assert report.total_boundary_violations == 1
    assert report.mean_visible_targets == pytest.approx(
        4 / 3
    )
    assert report.mean_visible_obstacles == pytest.approx(
        2.0
    )
    assert report.mean_visible_drones == pytest.approx(
        2.0
    )


def test_audit_report_is_json_serializable():
    report = build_audit_report(
        make_tracker(),
        label="baseline",
    )

    encoded = report.to_json()
    decoded = json.loads(encoded)

    assert decoded["label"] == "baseline"
    assert decoded["total_steps"] == 3


def test_single_step_report_has_zero_reward_deviation():
    tracker = MetricsTracker()
    tracker.record(
        step=1,
        explored_fraction=0.5,
        agent_metrics={
            "drone_000": AgentMetrics(reward=5.0),
        },
    )

    report = build_audit_report(
        tracker,
        label="single_step",
    )

    assert report.reward_standard_deviation == 0.0


def test_empty_tracker_is_rejected():
    with pytest.raises(ValueError):
        build_audit_report(MetricsTracker())


def test_empty_label_is_rejected():
    with pytest.raises(ValueError):
        build_audit_report(
            make_tracker(),
            label="",
        )


def test_compare_audit_reports_returns_deltas():
    baseline = AuditReport(
        label="baseline",
        total_steps=2,
        start_explored_fraction=0.1,
        final_explored_fraction=0.2,
        exploration_gain=0.1,
        mean_total_reward=1.0,
        reward_standard_deviation=0.2,
        cumulative_reward=2.0,
        cumulative_new_cells=4,
        total_drone_collisions=3,
        total_obstacle_collisions=2,
        total_targets_found=1,
        total_boundary_violations=1,
        mean_visible_targets=1.0,
        mean_visible_obstacles=2.0,
        mean_visible_drones=3.0,
    )

    candidate = AuditReport(
        label="mappo",
        total_steps=2,
        start_explored_fraction=0.1,
        final_explored_fraction=0.4,
        exploration_gain=0.3,
        mean_total_reward=2.5,
        reward_standard_deviation=0.1,
        cumulative_reward=5.0,
        cumulative_new_cells=9,
        total_drone_collisions=1,
        total_obstacle_collisions=1,
        total_targets_found=3,
        total_boundary_violations=0,
        mean_visible_targets=2.0,
        mean_visible_obstacles=1.0,
        mean_visible_drones=3.0,
    )

    comparison = compare_audit_reports(
        baseline,
        candidate,
    )

    assert comparison["baseline_label"] == "baseline"
    assert comparison["candidate_label"] == "mappo"
    assert comparison["exploration_gain_delta"] == pytest.approx(
        0.2
    )
    assert comparison["mean_reward_delta"] == pytest.approx(
        1.5
    )
    assert comparison["drone_collisions_delta"] == -2
    assert comparison["targets_found_delta"] == 2


def test_export_audit_report_writes_json(tmp_path):
    report = build_audit_report(
        make_tracker(),
        label="baseline",
    )
    path = tmp_path / "reports" / "audit.json"

    result = export_audit_report(report, path)

    assert result == path
    assert path.exists()

    exported = json.loads(
        path.read_text(encoding="utf-8")
    )

    assert exported["label"] == "baseline"
    assert exported["total_steps"] == 3


def test_export_audit_comparison_writes_json(tmp_path):
    comparison = {
        "baseline_label": "baseline",
        "candidate_label": "mappo",
        "mean_reward_delta": 1.5,
    }
    path = tmp_path / "reports" / "comparison.json"

    result = export_audit_comparison(
        comparison,
        path,
    )

    assert result == path
    assert path.exists()

    exported = json.loads(
        path.read_text(encoding="utf-8")
    )

    assert exported["candidate_label"] == "mappo"


def test_audit_export_requires_json_suffix(tmp_path):
    report = build_audit_report(
        make_tracker(),
        label="baseline",
    )

    with pytest.raises(ValueError):
        export_audit_report(
            report,
            tmp_path / "audit.txt",
        )


def test_comparison_export_requires_json_suffix(tmp_path):
    with pytest.raises(ValueError):
        export_audit_comparison(
            {},
            tmp_path / "comparison.csv",
        )