import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from sensors.health import (
    TelemetryHealthChecker,
    TelemetryHealthResult,
)
from sensors.session_summary import (
    summarize_telemetry_session,
)


def make_metric(
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
            "drone_collisions": 0,
            "obstacle_collisions": 0,
            "targets_found": 0,
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


def write_jsonl(
    path: Path,
    records: list[dict],
) -> None:
    path.write_text(
        "".join(
            json.dumps(record) + "\n"
            for record in records
        ),
        encoding="utf-8",
    )


def make_bundle(
    tmp_path: Path,
) -> tuple[Path, Path, Path]:
    metrics_path = tmp_path / "metrics.jsonl"
    events_path = tmp_path / "events.jsonl"
    report_path = tmp_path / "report.json"

    metrics_records = [
        make_metric(1, 0.10, 2.0),
        make_metric(2, 0.25, -1.0),
        make_metric(3, 0.40, 4.0),
    ]

    event_records = [
        make_event(
            "service_started",
            "info",
            "2026-10-06T12:00:00+00:00",
        ),
        make_event(
            "message_recorded",
            "info",
            "2026-10-06T12:01:00+00:00",
        ),
    ]

    write_jsonl(
        metrics_path,
        metrics_records,
    )
    write_jsonl(
        events_path,
        event_records,
    )

    metrics_summary = summarize_telemetry_session(
        metrics_path
    ).to_dict()

    event_summary = {
        "total_events": 2,
        "by_event": {
            "message_recorded": 1,
            "service_started": 1,
        },
        "by_level": {
            "info": 2,
        },
    }

    report_path.write_text(
        json.dumps(
            {
                "generated_at": (
                    "2026-10-06T12:02:00+00:00"
                ),
                "metrics_file": str(metrics_path),
                "events_file": str(events_path),
                "session_summary": metrics_summary,
                "event_summary": event_summary,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    return (
        metrics_path,
        events_path,
        report_path,
    )


def fixed_clock() -> datetime:
    return datetime(
        2026,
        10,
        6,
        12,
        5,
        0,
        tzinfo=timezone.utc,
    )


def test_healthy_bundle(
    tmp_path: Path,
):
    (
        metrics_path,
        events_path,
        report_path,
    ) = make_bundle(tmp_path)

    checker = TelemetryHealthChecker(
        metrics_path,
        events_path,
        report_path,
        clock=fixed_clock,
    )

    result = checker.check()

    assert isinstance(
        result,
        TelemetryHealthResult,
    )
    assert result.healthy is True
    assert result.checked_at == (
        "2026-10-06T12:05:00+00:00"
    )
    assert result.metrics_records == 3
    assert result.event_records == 2
    assert result.metric_steps_ordered is True
    assert result.report_matches_metrics is True
    assert result.report_matches_events is True
    assert result.issues == []


def test_health_result_serializes(
    tmp_path: Path,
):
    (
        metrics_path,
        events_path,
        report_path,
    ) = make_bundle(tmp_path)

    result = TelemetryHealthChecker(
        metrics_path,
        events_path,
        report_path,
        clock=fixed_clock,
    ).check()

    encoded = result.to_json()
    decoded = json.loads(encoded)

    assert decoded["healthy"] is True
    assert decoded["metrics_records"] == 3


@pytest.mark.parametrize(
    "missing_name",
    [
        "metrics",
        "events",
        "report",
    ],
)
def test_missing_file_is_reported(
    tmp_path: Path,
    missing_name: str,
):
    (
        metrics_path,
        events_path,
        report_path,
    ) = make_bundle(tmp_path)

    path = {
        "metrics": metrics_path,
        "events": events_path,
        "report": report_path,
    }[missing_name]

    path.unlink()

    result = TelemetryHealthChecker(
        metrics_path,
        events_path,
        report_path,
        clock=fixed_clock,
    ).check()

    assert result.healthy is False
    assert (
        f"{missing_name.capitalize()} file does not exist."
        in result.issues
    )


def test_invalid_suffixes_are_rejected(
    tmp_path: Path,
):
    (
        metrics_path,
        events_path,
        report_path,
    ) = make_bundle(tmp_path)

    checker = TelemetryHealthChecker(
        metrics_path.with_suffix(".txt"),
        events_path.with_suffix(".txt"),
        report_path.with_suffix(".txt"),
        clock=fixed_clock,
    )

    result = checker.check()

    assert result.healthy is False
    assert len(result.issues) >= 3


def test_unordered_metric_steps_are_reported(
    tmp_path: Path,
):
    (
        metrics_path,
        events_path,
        report_path,
    ) = make_bundle(tmp_path)

    write_jsonl(
        metrics_path,
        [
            make_metric(1, 0.10, 2.0),
            make_metric(3, 0.30, 2.0),
            make_metric(2, 0.40, 2.0),
        ],
    )

    result = TelemetryHealthChecker(
        metrics_path,
        events_path,
        report_path,
        clock=fixed_clock,
    ).check()

    assert result.healthy is False
    assert result.metric_steps_ordered is False
    assert (
        "Metrics steps are not strictly increasing."
        in result.issues
    )


def test_malformed_report_is_reported(
    tmp_path: Path,
):
    (
        metrics_path,
        events_path,
        report_path,
    ) = make_bundle(tmp_path)

    report_path.write_text(
        '{"invalid":\n',
        encoding="utf-8",
    )

    result = TelemetryHealthChecker(
        metrics_path,
        events_path,
        report_path,
        clock=fixed_clock,
    ).check()

    assert result.healthy is False
    assert (
        "Report file is not valid JSON."
        in result.issues
    )


def test_missing_report_sections_are_reported(
    tmp_path: Path,
):
    (
        metrics_path,
        events_path,
        report_path,
    ) = make_bundle(tmp_path)

    report_path.write_text(
        json.dumps(
            {
                "metrics_file": str(metrics_path),
                "events_file": str(events_path),
            }
        ),
        encoding="utf-8",
    )

    result = TelemetryHealthChecker(
        metrics_path,
        events_path,
        report_path,
        clock=fixed_clock,
    ).check()

    assert result.healthy is False
    assert any(
        "session_summary" in issue
        for issue in result.issues
    )
    assert any(
        "event_summary" in issue
        for issue in result.issues
    )


def test_mismatched_report_counts_are_reported(
    tmp_path: Path,
):
    (
        metrics_path,
        events_path,
        report_path,
    ) = make_bundle(tmp_path)

    report = json.loads(
        report_path.read_text(
            encoding="utf-8"
        )
    )

    report["session_summary"][
        "total_records"
    ] = 99

    report["event_summary"][
        "total_events"
    ] = 99

    report_path.write_text(
        json.dumps(report),
        encoding="utf-8",
    )

    result = TelemetryHealthChecker(
        metrics_path,
        events_path,
        report_path,
        clock=fixed_clock,
    ).check()

    assert result.healthy is False
    assert result.report_matches_metrics is False
    assert result.report_matches_events is False


def test_mismatched_source_paths_are_reported(
    tmp_path: Path,
):
    (
        metrics_path,
        events_path,
        report_path,
    ) = make_bundle(tmp_path)

    report = json.loads(
        report_path.read_text(
            encoding="utf-8"
        )
    )

    report["metrics_file"] = "different.jsonl"
    report["events_file"] = "other.jsonl"

    report_path.write_text(
        json.dumps(report),
        encoding="utf-8",
    )

    result = TelemetryHealthChecker(
        metrics_path,
        events_path,
        report_path,
        clock=fixed_clock,
    ).check()

    assert result.healthy is False
    assert any(
        "metrics_file" in issue
        for issue in result.issues
    )
    assert any(
        "events_file" in issue
        for issue in result.issues
    )


def test_invalid_clock_type_is_rejected(
    tmp_path: Path,
):
    (
        metrics_path,
        events_path,
        report_path,
    ) = make_bundle(tmp_path)

    checker = TelemetryHealthChecker(
        metrics_path,
        events_path,
        report_path,
        clock=lambda: "invalid",
    )

    with pytest.raises(TypeError):
        checker.check()


def test_naive_clock_is_rejected(
    tmp_path: Path,
):
    (
        metrics_path,
        events_path,
        report_path,
    ) = make_bundle(tmp_path)

    checker = TelemetryHealthChecker(
        metrics_path,
        events_path,
        report_path,
        clock=lambda: datetime(
            2026,
            10,
            6,
            12,
            0,
            0,
        ),
    )

    with pytest.raises(ValueError):
        checker.check()


def test_check_and_export_writes_json(
    tmp_path: Path,
):
    (
        metrics_path,
        events_path,
        report_path,
    ) = make_bundle(tmp_path)

    output_path = (
        tmp_path
        / "nested"
        / "health.json"
    )

    result = TelemetryHealthChecker(
        metrics_path,
        events_path,
        report_path,
        clock=fixed_clock,
    ).check_and_export(output_path)

    assert result.healthy is True
    assert output_path.exists()

    exported = json.loads(
        output_path.read_text(
            encoding="utf-8"
        )
    )

    assert exported["healthy"] is True
    assert exported["event_records"] == 2


def test_check_and_export_requires_json_suffix(
    tmp_path: Path,
):
    (
        metrics_path,
        events_path,
        report_path,
    ) = make_bundle(tmp_path)

    with pytest.raises(ValueError):
        TelemetryHealthChecker(
            metrics_path,
            events_path,
            report_path,
            clock=fixed_clock,
        ).check_and_export(
            tmp_path / "health.txt"
        )