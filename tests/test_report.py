import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from sensors.report import (
    TelemetryReport,
    TelemetryReportError,
    build_and_export_telemetry_report,
    build_telemetry_report,
    export_telemetry_report,
)


def make_metric_message(
    step: int,
    explored_fraction: float,
    total_reward: float,
) -> dict:
    return {
        "type": "swarm_metrics",
        "metrics": {
            "step": step,
            "explored_fraction": explored_fraction,
            "total_reward": total_reward,
            "newly_explored_cells": step,
            "drone_collisions": 1 if step == 2 else 0,
            "obstacle_collisions": 0,
            "targets_found": step,
            "boundary_violations": 0,
        },
    }


def make_event(
    event: str,
    level: str,
    timestamp: str,
) -> dict:
    return {
        "timestamp": timestamp,
        "event": event,
        "level": level,
        "details": {},
    }


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text(
        "".join(
            json.dumps(record) + "\n"
            for record in records
        ),
        encoding="utf-8",
    )


def fixed_clock() -> datetime:
    return datetime(
        2026,
        10,
        6,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )


def make_input_files(tmp_path: Path) -> tuple[
    Path,
    Path,
]:
    metrics_path = tmp_path / "metrics.jsonl"
    events_path = tmp_path / "events.jsonl"

    write_jsonl(
        metrics_path,
        [
            make_metric_message(1, 0.10, 2.0),
            make_metric_message(2, 0.25, -1.0),
            make_metric_message(3, 0.40, 4.0),
        ],
    )

    write_jsonl(
        events_path,
        [
            make_event(
                "service_started",
                "info",
                "2026-10-06T11:59:00+00:00",
            ),
            make_event(
                "message_recorded",
                "info",
                "2026-10-06T11:59:30+00:00",
            ),
            make_event(
                "message_failed",
                "error",
                "2026-10-06T12:00:00+00:00",
            ),
        ],
    )

    return metrics_path, events_path


def test_build_report_combines_sources(tmp_path: Path):
    metrics_path, events_path = make_input_files(tmp_path)

    report = build_telemetry_report(
        metrics_path,
        events_path,
        clock=fixed_clock,
    )

    assert isinstance(report, TelemetryReport)
    assert report.generated_at == (
        "2026-10-06T12:00:00+00:00"
    )
    assert report.metrics_file == str(metrics_path)
    assert report.events_file == str(events_path)

    assert report.session_summary[
        "total_records"
    ] == 3
    assert report.session_summary[
        "exploration_gain"
    ] == pytest.approx(0.30)
    assert report.session_summary[
        "cumulative_total_reward"
    ] == pytest.approx(5.0)

    assert report.event_summary == {
        "total_events": 3,
        "by_event": {
            "message_failed": 1,
            "message_recorded": 1,
            "service_started": 1,
        },
        "by_level": {
            "error": 1,
            "info": 2,
        },
    }


def test_report_to_dict_and_json(tmp_path: Path):
    metrics_path, events_path = make_input_files(tmp_path)

    report = build_telemetry_report(
        metrics_path,
        events_path,
        clock=fixed_clock,
    )

    result = report.to_dict()
    encoded = report.to_json()

    assert result["generated_at"] == (
        "2026-10-06T12:00:00+00:00"
    )
    assert json.loads(encoded)["event_summary"][
        "total_events"
    ] == 3


def test_export_report_writes_json(tmp_path: Path):
    metrics_path, events_path = make_input_files(tmp_path)
    report = build_telemetry_report(
        metrics_path,
        events_path,
        clock=fixed_clock,
    )

    output_path = tmp_path / "nested" / "report.json"

    result = export_telemetry_report(
        report,
        output_path,
    )

    assert result == output_path
    assert output_path.exists()

    exported = json.loads(
        output_path.read_text(encoding="utf-8")
    )

    assert exported["session_summary"][
        "last_step"
    ] == 3
    assert exported["event_summary"][
        "total_events"
    ] == 3


def test_build_and_export_report(tmp_path: Path):
    metrics_path, events_path = make_input_files(tmp_path)
    output_path = tmp_path / "report.json"

    report = build_and_export_telemetry_report(
        metrics_path,
        events_path,
        output_path,
        clock=fixed_clock,
    )

    assert isinstance(report, TelemetryReport)
    assert output_path.exists()


def test_missing_metrics_file_is_rejected(
    tmp_path: Path,
):
    _, events_path = make_input_files(tmp_path)

    with pytest.raises(FileNotFoundError):
        build_telemetry_report(
            tmp_path / "missing.jsonl",
            events_path,
        )


def test_missing_events_file_is_rejected(
    tmp_path: Path,
):
    metrics_path, _ = make_input_files(tmp_path)

    with pytest.raises(FileNotFoundError):
        build_telemetry_report(
            metrics_path,
            tmp_path / "missing.jsonl",
        )


def test_invalid_input_suffix_is_rejected(
    tmp_path: Path,
):
    with pytest.raises(ValueError):
        build_telemetry_report(
            tmp_path / "metrics.txt",
            tmp_path / "events.jsonl",
        )

    with pytest.raises(ValueError):
        build_telemetry_report(
            tmp_path / "metrics.jsonl",
            tmp_path / "events.txt",
        )


def test_invalid_clock_type_is_rejected(tmp_path: Path):
    metrics_path, events_path = make_input_files(tmp_path)

    with pytest.raises(TypeError):
        build_telemetry_report(
            metrics_path,
            events_path,
            clock=lambda: "invalid",
        )


def test_naive_clock_is_rejected(tmp_path: Path):
    metrics_path, events_path = make_input_files(tmp_path)

    with pytest.raises(ValueError):
        build_telemetry_report(
            metrics_path,
            events_path,
            clock=lambda: datetime(
                2026,
                10,
                6,
                12,
                0,
                0,
            ),
        )


def test_export_requires_report_instance(
    tmp_path: Path,
):
    with pytest.raises(TypeError):
        export_telemetry_report(
            object(),
            tmp_path / "report.json",
        )


def test_export_requires_json_suffix(
    tmp_path: Path,
):
    metrics_path, events_path = make_input_files(tmp_path)
    report = build_telemetry_report(
        metrics_path,
        events_path,
        clock=fixed_clock,
    )

    with pytest.raises(ValueError):
        export_telemetry_report(
            report,
            tmp_path / "report.txt",
        )