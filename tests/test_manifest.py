import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from sensors.manifest import (
    TelemetryManifest,
    TelemetryManifestError,
    build_telemetry_manifest,
    export_telemetry_manifest,
    verify_telemetry_manifest,
)


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
) -> tuple[Path, Path, Path, Path]:
    metrics_path = tmp_path / "metrics.jsonl"
    events_path = tmp_path / "events.jsonl"
    report_path = tmp_path / "report.json"
    health_path = tmp_path / "health.json"

    write_jsonl(
        metrics_path,
        [
            {
                "metrics": {
                    "step": 1,
                    "total_reward": 2.0,
                }
            },
            {
                "metrics": {
                    "step": 2,
                    "total_reward": 4.0,
                }
            },
        ],
    )

    write_jsonl(
        events_path,
        [
            {
                "event": "started",
                "level": "info",
            },
            {
                "event": "completed",
                "level": "info",
            },
            {
                "event": "saved",
                "level": "info",
            },
        ],
    )

    report_path.write_text(
        json.dumps(
            {
                "session_summary": {
                    "total_records": 2,
                },
                "event_summary": {
                    "total_events": 3,
                },
            }
        ),
        encoding="utf-8",
    )

    health_path.write_text(
        json.dumps(
            {
                "healthy": True,
                "issues": [],
            }
        ),
        encoding="utf-8",
    )

    return (
        metrics_path,
        events_path,
        report_path,
        health_path,
    )


def fixed_clock() -> datetime:
    return datetime(
        2026,
        10,
        6,
        12,
        10,
        0,
        tzinfo=timezone.utc,
    )


def test_builds_healthy_manifest(
    tmp_path: Path,
):
    (
        metrics,
        events,
        report,
        health,
    ) = make_bundle(tmp_path)

    manifest = build_telemetry_manifest(
        metrics,
        events,
        report,
        health,
        clock=fixed_clock,
    )

    assert isinstance(
        manifest,
        TelemetryManifest,
    )
    assert manifest.schema_version == 1
    assert manifest.generated_at == (
        "2026-10-06T12:10:00+00:00"
    )
    assert manifest.healthy is True
    assert manifest.counts == {
        "metrics_records": 2,
        "event_records": 3,
    }


def test_manifest_contains_file_sizes(
    tmp_path: Path,
):
    (
        metrics,
        events,
        report,
        health,
    ) = make_bundle(tmp_path)

    manifest = build_telemetry_manifest(
        metrics,
        events,
        report,
        health,
        clock=fixed_clock,
    )

    assert (
        manifest.artifacts["metrics"].size_bytes
        == metrics.stat().st_size
    )
    assert (
        manifest.artifacts["events"].size_bytes
        == events.stat().st_size
    )


def test_manifest_contains_sha256(
    tmp_path: Path,
):
    (
        metrics,
        events,
        report,
        health,
    ) = make_bundle(tmp_path)

    manifest = build_telemetry_manifest(
        metrics,
        events,
        report,
        health,
        clock=fixed_clock,
    )

    expected = hashlib.sha256(
        metrics.read_bytes()
    ).hexdigest()

    assert (
        manifest.artifacts["metrics"].sha256
        == expected
    )


def test_manifest_json_is_deterministic(
    tmp_path: Path,
):
    (
        metrics,
        events,
        report,
        health,
    ) = make_bundle(tmp_path)

    manifest = build_telemetry_manifest(
        metrics,
        events,
        report,
        health,
        clock=fixed_clock,
    )

    assert manifest.to_json() == manifest.to_json()


def test_manifest_to_dict_is_json_compatible(
    tmp_path: Path,
):
    (
        metrics,
        events,
        report,
        health,
    ) = make_bundle(tmp_path)

    manifest = build_telemetry_manifest(
        metrics,
        events,
        report,
        health,
        clock=fixed_clock,
    )

    encoded = json.dumps(manifest.to_dict())
    decoded = json.loads(encoded)

    assert decoded["healthy"] is True
    assert decoded["counts"]["metrics_records"] == 2


def test_exports_manifest(
    tmp_path: Path,
):
    (
        metrics,
        events,
        report,
        health,
    ) = make_bundle(tmp_path)

    manifest = build_telemetry_manifest(
        metrics,
        events,
        report,
        health,
        clock=fixed_clock,
    )

    output = tmp_path / "nested" / "manifest.json"

    export_telemetry_manifest(
        manifest,
        output,
    )

    assert output.exists()

    payload = json.loads(
        output.read_text(encoding="utf-8")
    )

    assert payload["schema_version"] == 1
    assert payload["healthy"] is True


@pytest.mark.parametrize(
    "missing_index",
    [0, 1, 2, 3],
)
def test_missing_file_is_rejected(
    tmp_path: Path,
    missing_index: int,
):
    paths = list(make_bundle(tmp_path))
    paths[missing_index].unlink()

    with pytest.raises(
        TelemetryManifestError
    ):
        build_telemetry_manifest(
            *paths,
            clock=fixed_clock,
        )


def test_invalid_suffix_is_rejected(
    tmp_path: Path,
):
    (
        metrics,
        events,
        report,
        health,
    ) = make_bundle(tmp_path)

    invalid_metrics = metrics.with_suffix(".txt")

    with pytest.raises(
        TelemetryManifestError
    ):
        build_telemetry_manifest(
            invalid_metrics,
            events,
            report,
            health,
            clock=fixed_clock,
        )


def test_invalid_health_json_is_rejected(
    tmp_path: Path,
):
    (
        metrics,
        events,
        report,
        health,
    ) = make_bundle(tmp_path)

    health.write_text(
        '{"healthy": "yes"}',
        encoding="utf-8",
    )

    with pytest.raises(
        TelemetryManifestError
    ):
        build_telemetry_manifest(
            metrics,
            events,
            report,
            health,
            clock=fixed_clock,
        )


def test_invalid_clock_type_is_rejected(
    tmp_path: Path,
):
    paths = make_bundle(tmp_path)

    with pytest.raises(TypeError):
        build_telemetry_manifest(
            *paths,
            clock=lambda: "invalid",
        )


def test_naive_clock_is_rejected(
    tmp_path: Path,
):
    paths = make_bundle(tmp_path)

    with pytest.raises(ValueError):
        build_telemetry_manifest(
            *paths,
            clock=lambda: datetime(
                2026,
                10,
                6,
                12,
                10,
            ),
        )


def test_verification_succeeds_for_unchanged_files(
    tmp_path: Path,
):
    paths = make_bundle(tmp_path)

    manifest = build_telemetry_manifest(
        *paths,
        clock=fixed_clock,
    )

    assert verify_telemetry_manifest(
        manifest,
        *paths,
    ) is True


def test_verification_detects_changed_file(
    tmp_path: Path,
):
    paths = make_bundle(tmp_path)

    manifest = build_telemetry_manifest(
        *paths,
        clock=fixed_clock,
    )

    paths[0].write_text(
        paths[0].read_text(encoding="utf-8")
        + '{"changed": true}\n',
        encoding="utf-8",
    )

    assert verify_telemetry_manifest(
        manifest,
        *paths,
    ) is False


def test_verification_rejects_missing_file(
    tmp_path: Path,
):
    paths = list(make_bundle(tmp_path))

    manifest = build_telemetry_manifest(
        *paths,
        clock=fixed_clock,
    )

    paths[1].unlink()

    with pytest.raises(
        TelemetryManifestError
    ):
        verify_telemetry_manifest(
            manifest,
            *paths,
        )


def test_export_requires_json_suffix(
    tmp_path: Path,
):
    paths = make_bundle(tmp_path)

    manifest = build_telemetry_manifest(
        *paths,
        clock=fixed_clock,
    )

    with pytest.raises(
        TelemetryManifestError
    ):
        export_telemetry_manifest(
            manifest,
            tmp_path / "manifest.txt",
        )


def test_source_files_are_not_modified(
    tmp_path: Path,
):
    paths = make_bundle(tmp_path)
    before = {
        path: path.read_bytes()
        for path in paths
    }

    build_telemetry_manifest(
        *paths,
        clock=fixed_clock,
    )

    after = {
        path: path.read_bytes()
        for path in paths
    }

    assert before == after