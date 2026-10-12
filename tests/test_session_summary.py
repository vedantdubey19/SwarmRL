import json
from pathlib import Path

import pytest

from sensors.session_summary import (
    TelemetrySessionSummary,
    TelemetrySummaryError,
    export_session_summary,
    summarize_and_export_session,
    summarize_telemetry_session,
)


def make_message(
    step: int,
    *,
    explored_fraction: float = 0.0,
    total_reward: float = 0.0,
    newly_explored_cells: int = 0,
    drone_collisions: int = 0,
    obstacle_collisions: int = 0,
    targets_found: int = 0,
    boundary_violations: int = 0,
) -> dict:
    return {
        "type": "swarm_metrics",
        "metrics": {
            "step": step,
            "explored_fraction": explored_fraction,
            "total_reward": total_reward,
            "newly_explored_cells": newly_explored_cells,
            "drone_collisions": drone_collisions,
            "obstacle_collisions": obstacle_collisions,
            "targets_found": targets_found,
            "boundary_violations": boundary_violations,
        },
    }


def write_jsonl(path: Path, messages: list[dict]) -> None:
    path.write_text(
        "".join(
            json.dumps(message) + "\n"
            for message in messages
        ),
        encoding="utf-8",
    )


def test_summarize_telemetry_session_aggregates_records(
    tmp_path: Path,
):
    jsonl_path = tmp_path / "metrics.jsonl"

    write_jsonl(
        jsonl_path,
        [
            make_message(
                1,
                explored_fraction=0.10,
                total_reward=2.0,
                newly_explored_cells=3,
                drone_collisions=1,
                targets_found=1,
            ),
            make_message(
                2,
                explored_fraction=0.25,
                total_reward=-1.0,
                newly_explored_cells=2,
                obstacle_collisions=1,
            ),
            make_message(
                3,
                explored_fraction=0.40,
                total_reward=4.0,
                newly_explored_cells=5,
                targets_found=2,
                boundary_violations=1,
            ),
        ],
    )

    summary = summarize_telemetry_session(jsonl_path)

    assert summary.total_records == 3
    assert summary.first_step == 1
    assert summary.last_step == 3
    assert summary.start_explored_fraction == pytest.approx(
        0.10
    )
    assert summary.final_explored_fraction == pytest.approx(
        0.40
    )
    assert summary.exploration_gain == pytest.approx(0.30)
    assert summary.cumulative_total_reward == pytest.approx(5.0)
    assert summary.mean_total_reward == pytest.approx(5.0 / 3)
    assert summary.cumulative_newly_explored_cells == 10
    assert summary.total_drone_collisions == 1
    assert summary.total_obstacle_collisions == 1
    assert summary.total_targets_found == 3
    assert summary.total_boundary_violations == 1


def test_blank_lines_are_ignored(tmp_path: Path):
    jsonl_path = tmp_path / "metrics.jsonl"

    jsonl_path.write_text(
        "\n"
        + json.dumps(make_message(1))
        + "\n\n"
        + json.dumps(make_message(2))
        + "\n",
        encoding="utf-8",
    )

    summary = summarize_telemetry_session(jsonl_path)

    assert summary.total_records == 2
    assert summary.first_step == 1
    assert summary.last_step == 2


def test_summary_to_dict_and_json():
    summary = TelemetrySessionSummary(
        total_records=1,
        first_step=2,
        last_step=2,
        start_explored_fraction=0.2,
        final_explored_fraction=0.2,
        exploration_gain=0.0,
        cumulative_total_reward=3.0,
        mean_total_reward=3.0,
        cumulative_newly_explored_cells=4,
        total_drone_collisions=0,
        total_obstacle_collisions=1,
        total_targets_found=2,
        total_boundary_violations=0,
    )

    result = summary.to_dict()
    encoded = summary.to_json()

    assert result["first_step"] == 2
    assert json.loads(encoded)["total_targets_found"] == 2


def test_export_session_summary_writes_json(
    tmp_path: Path,
):
    summary = TelemetrySessionSummary(
        total_records=1,
        first_step=1,
        last_step=1,
        start_explored_fraction=0.1,
        final_explored_fraction=0.1,
        exploration_gain=0.0,
        cumulative_total_reward=2.0,
        mean_total_reward=2.0,
        cumulative_newly_explored_cells=3,
        total_drone_collisions=0,
        total_obstacle_collisions=0,
        total_targets_found=1,
        total_boundary_violations=0,
    )
    output_path = tmp_path / "nested" / "summary.json"

    result = export_session_summary(summary, output_path)

    assert result == output_path
    assert output_path.exists()

    exported = json.loads(
        output_path.read_text(encoding="utf-8")
    )

    assert exported["total_records"] == 1
    assert exported["cumulative_total_reward"] == 2.0


def test_export_replaces_existing_summary(
    tmp_path: Path,
):
    output_path = tmp_path / "summary.json"
    output_path.write_text(
        '{"old": true}\n',
        encoding="utf-8",
    )

    summary = TelemetrySessionSummary(
        total_records=2,
        first_step=1,
        last_step=2,
        start_explored_fraction=0.1,
        final_explored_fraction=0.2,
        exploration_gain=0.1,
        cumulative_total_reward=3.0,
        mean_total_reward=1.5,
        cumulative_newly_explored_cells=5,
        total_drone_collisions=1,
        total_obstacle_collisions=0,
        total_targets_found=2,
        total_boundary_violations=0,
    )

    export_session_summary(summary, output_path)

    exported = json.loads(
        output_path.read_text(encoding="utf-8")
    )

    assert "old" not in exported
    assert exported["total_records"] == 2


def test_summarize_and_export_session(
    tmp_path: Path,
):
    jsonl_path = tmp_path / "metrics.jsonl"
    output_path = tmp_path / "summary.json"

    write_jsonl(
        jsonl_path,
        [
            make_message(
                1,
                explored_fraction=0.1,
                total_reward=2.0,
            ),
            make_message(
                2,
                explored_fraction=0.3,
                total_reward=4.0,
            ),
        ],
    )

    summary = summarize_and_export_session(
        jsonl_path,
        output_path,
    )

    assert summary.total_records == 2
    assert output_path.exists()

    exported = json.loads(
        output_path.read_text(encoding="utf-8")
    )

    assert exported["mean_total_reward"] == pytest.approx(3.0)


def test_invalid_jsonl_suffix_is_rejected(
    tmp_path: Path,
):
    with pytest.raises(ValueError):
        summarize_telemetry_session(
            tmp_path / "metrics.txt"
        )


def test_missing_jsonl_file_raises_file_not_found(
    tmp_path: Path,
):
    with pytest.raises(FileNotFoundError):
        summarize_telemetry_session(
            tmp_path / "missing.jsonl"
        )


def test_empty_jsonl_file_is_rejected(
    tmp_path: Path,
):
    jsonl_path = tmp_path / "metrics.jsonl"
    jsonl_path.write_text("", encoding="utf-8")

    with pytest.raises(
        TelemetrySummaryError,
        match="contains no records",
    ):
        summarize_telemetry_session(jsonl_path)


def test_invalid_json_line_is_rejected(
    tmp_path: Path,
):
    jsonl_path = tmp_path / "metrics.jsonl"
    jsonl_path.write_text(
        '{"type":\n',
        encoding="utf-8",
    )

    with pytest.raises(
        TelemetrySummaryError,
        match="Line 1 is not valid JSON",
    ):
        summarize_telemetry_session(jsonl_path)


def test_wrong_message_type_is_rejected(
    tmp_path: Path,
):
    jsonl_path = tmp_path / "metrics.jsonl"

    write_jsonl(
        jsonl_path,
        [
            {
                "type": "other",
                "metrics": {
                    "step": 1,
                },
            }
        ],
    )

    with pytest.raises(
        TelemetrySummaryError,
        match="must have type",
    ):
        summarize_telemetry_session(jsonl_path)


def test_missing_metrics_is_rejected(
    tmp_path: Path,
):
    jsonl_path = tmp_path / "metrics.jsonl"

    write_jsonl(
        jsonl_path,
        [
            {
                "type": "swarm_metrics",
            }
        ],
    )

    with pytest.raises(
        TelemetrySummaryError,
        match="metrics must be an object",
    ):
        summarize_telemetry_session(jsonl_path)


@pytest.mark.parametrize(
    "step",
    [
        None,
        "1",
        True,
    ],
)
def test_invalid_step_is_rejected(
    tmp_path: Path,
    step,
):
    jsonl_path = tmp_path / "metrics.jsonl"

    write_jsonl(
        jsonl_path,
        [
            {
                "type": "swarm_metrics",
                "metrics": {
                    "step": step,
                },
            }
        ],
    )

    with pytest.raises(
        TelemetrySummaryError,
        match="step must be an integer",
    ):
        summarize_telemetry_session(jsonl_path)


def test_non_numeric_metric_is_rejected(
    tmp_path: Path,
):
    jsonl_path = tmp_path / "metrics.jsonl"

    write_jsonl(
        jsonl_path,
        [
            make_message(
                1,
                total_reward="invalid",
            )
        ],
    )

    with pytest.raises(
        TelemetrySummaryError,
        match="total_reward",
    ):
        summarize_telemetry_session(jsonl_path)


def test_export_requires_summary_instance(
    tmp_path: Path,
):
    with pytest.raises(TypeError):
        export_session_summary(
            object(),
            tmp_path / "summary.json",
        )


def test_export_requires_json_suffix(
    tmp_path: Path,
):
    summary = TelemetrySessionSummary(
        total_records=1,
        first_step=1,
        last_step=1,
        start_explored_fraction=0.0,
        final_explored_fraction=0.0,
        exploration_gain=0.0,
        cumulative_total_reward=0.0,
        mean_total_reward=0.0,
        cumulative_newly_explored_cells=0,
        total_drone_collisions=0,
        total_obstacle_collisions=0,
        total_targets_found=0,
        total_boundary_violations=0,
    )

    with pytest.raises(ValueError):
        export_session_summary(
            summary,
            tmp_path / "summary.txt",
        )