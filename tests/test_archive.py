import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from sensors.archive import (
    TelemetryArchiveError,
    create_telemetry_archive,
    verify_telemetry_archive,
)


ARTIFACT_NAMES = (
    "metrics.jsonl",
    "events.jsonl",
    "report.json",
    "health.json",
    "manifest.json",
    "archive.json",
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
) -> tuple[Path, Path, Path, Path, Path]:
    metrics_path = tmp_path / "metrics.jsonl"
    events_path = tmp_path / "events.jsonl"
    report_path = tmp_path / "report.json"
    health_path = tmp_path / "health.json"
    manifest_path = tmp_path / "manifest.json"

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
        ],
    )

    report_path.write_text(
        json.dumps(
            {
                "session_summary": {
                    "total_records": 2,
                },
                "event_summary": {
                    "total_events": 2,
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

    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "healthy": True,
            }
        ),
        encoding="utf-8",
    )

    return (
        metrics_path,
        events_path,
        report_path,
        health_path,
        manifest_path,
    )


def fixed_clock() -> datetime:
    return datetime(
        2026,
        10,
        9,
        9,
        0,
        0,
        tzinfo=timezone.utc,
    )


def create_archive(
    tmp_path: Path,
) -> tuple[Path, tuple[Path, ...]]:
    paths = make_bundle(tmp_path)
    archive_path = tmp_path / "bundle.zip"

    create_telemetry_archive(
        *paths,
        output_path=archive_path,
        clock=fixed_clock,
    )

    return archive_path, paths


def rebuild_archive(
    source_path: Path,
    output_path: Path,
    *,
    omit: str | None = None,
    replacements: dict[str, bytes] | None = None,
) -> None:
    replacements = replacements or {}

    with (
        zipfile.ZipFile(source_path, mode="r") as source,
        zipfile.ZipFile(output_path, mode="w") as destination,
    ):
        for name in source.namelist():
            if name == omit:
                continue

            data = replacements.get(
                name,
                source.read(name),
            )
            destination.writestr(name, data)


def test_creates_archive(
    tmp_path: Path,
):
    archive_path, _ = create_archive(tmp_path)

    assert archive_path.exists()
    assert zipfile.is_zipfile(archive_path)


def test_returns_archive_metadata(
    tmp_path: Path,
):
    archive_path, paths = create_archive(tmp_path)

    result = create_telemetry_archive(
        *paths,
        output_path=tmp_path / "second_bundle.zip",
        clock=fixed_clock,
    )

    assert result.schema_version == 1
    assert result.created_at == (
        "2026-10-09T09:00:00+00:00"
    )
    assert result.archive_path == str(
        tmp_path / "second_bundle.zip"
    )
    assert result.artifacts == (
        "metrics.jsonl",
        "events.jsonl",
        "report.json",
        "health.json",
        "manifest.json",
    )

    with zipfile.ZipFile(
        archive_path,
        mode="r",
    ) as bundle:
        metadata = json.loads(
            bundle.read("archive.json")
        )

    assert metadata["schema_version"] == 1
    assert metadata["created_at"] == (
        "2026-10-09T09:00:00+00:00"
    )
    assert metadata["artifacts"] == [
        "metrics.jsonl",
        "events.jsonl",
        "report.json",
        "health.json",
        "manifest.json",
    ]


def test_archive_contains_required_entries(
    tmp_path: Path,
):
    archive_path, _ = create_archive(tmp_path)

    with zipfile.ZipFile(
        archive_path,
        mode="r",
    ) as bundle:
        names = set(bundle.namelist())

    assert names == set(ARTIFACT_NAMES)


def test_archive_preserves_artifact_contents(
    tmp_path: Path,
):
    archive_path, paths = create_archive(tmp_path)

    names_and_paths = {
        "metrics.jsonl": paths[0],
        "events.jsonl": paths[1],
        "report.json": paths[2],
        "health.json": paths[3],
        "manifest.json": paths[4],
    }

    with zipfile.ZipFile(
        archive_path,
        mode="r",
    ) as bundle:
        for name, source_path in names_and_paths.items():
            assert bundle.read(name) == source_path.read_bytes()


def test_archive_metadata_is_valid_json(
    tmp_path: Path,
):
    archive_path, _ = create_archive(tmp_path)

    with zipfile.ZipFile(
        archive_path,
        mode="r",
    ) as bundle:
        metadata = json.loads(
            bundle.read("archive.json")
        )

    assert isinstance(metadata, dict)
    assert metadata["schema_version"] == 1


def test_archive_timestamp_is_timezone_aware(
    tmp_path: Path,
):
    archive_path, _ = create_archive(tmp_path)

    with zipfile.ZipFile(
        archive_path,
        mode="r",
    ) as bundle:
        metadata = json.loads(
            bundle.read("archive.json")
        )

    timestamp = datetime.fromisoformat(
        metadata["created_at"]
    )

    assert timestamp.tzinfo is not None
    assert timestamp.utcoffset() is not None


def test_verifies_valid_archive(
    tmp_path: Path,
):
    archive_path, _ = create_archive(tmp_path)

    assert verify_telemetry_archive(
        archive_path
    ) is True


def test_verification_detects_missing_entry(
    tmp_path: Path,
):
    archive_path, _ = create_archive(tmp_path)
    rebuilt = tmp_path / "missing.zip"

    rebuild_archive(
        archive_path,
        rebuilt,
        omit="health.json",
    )

    with pytest.raises(TelemetryArchiveError):
        verify_telemetry_archive(rebuilt)


def test_verification_detects_invalid_report(
    tmp_path: Path,
):
    archive_path, _ = create_archive(tmp_path)
    rebuilt = tmp_path / "invalid_report.zip"

    rebuild_archive(
        archive_path,
        rebuilt,
        replacements={
            "report.json": b'{"invalid":',
        },
    )

    with pytest.raises(TelemetryArchiveError):
        verify_telemetry_archive(rebuilt)


def test_verification_detects_invalid_metrics(
    tmp_path: Path,
):
    archive_path, _ = create_archive(tmp_path)
    rebuilt = tmp_path / "invalid_metrics.zip"

    rebuild_archive(
        archive_path,
        rebuilt,
        replacements={
            "metrics.jsonl": b'{"invalid":\n',
        },
    )

    with pytest.raises(TelemetryArchiveError):
        verify_telemetry_archive(rebuilt)


def test_missing_input_file_is_rejected(
    tmp_path: Path,
):
    paths = list(make_bundle(tmp_path))
    paths[0].unlink()

    with pytest.raises(TelemetryArchiveError):
        create_telemetry_archive(
            *paths,
            output_path=tmp_path / "bundle.zip",
            clock=fixed_clock,
        )


def test_invalid_input_suffix_is_rejected(
    tmp_path: Path,
):
    paths = list(make_bundle(tmp_path))
    invalid_metrics = paths[0].with_suffix(".txt")

    with pytest.raises(TelemetryArchiveError):
        create_telemetry_archive(
            invalid_metrics,
            *paths[1:],
            output_path=tmp_path / "bundle.zip",
            clock=fixed_clock,
        )


def test_invalid_output_suffix_is_rejected(
    tmp_path: Path,
):
    paths = make_bundle(tmp_path)

    with pytest.raises(TelemetryArchiveError):
        create_telemetry_archive(
            *paths,
            output_path=tmp_path / "bundle.txt",
            clock=fixed_clock,
        )


def test_invalid_clock_type_is_rejected(
    tmp_path: Path,
):
    paths = make_bundle(tmp_path)

    with pytest.raises(TypeError):
        create_telemetry_archive(
            *paths,
            output_path=tmp_path / "bundle.zip",
            clock=lambda: "invalid",
        )


def test_naive_clock_is_rejected(
    tmp_path: Path,
):
    paths = make_bundle(tmp_path)

    with pytest.raises(ValueError):
        create_telemetry_archive(
            *paths,
            output_path=tmp_path / "bundle.zip",
            clock=lambda: datetime(
                2026,
                10,
                9,
                9,
                0,
            ),
        )


def test_source_files_are_not_modified(
    tmp_path: Path,
):
    paths = make_bundle(tmp_path)
    before = {
        path: path.read_bytes()
        for path in paths
    }

    create_telemetry_archive(
        *paths,
        output_path=tmp_path / "bundle.zip",
        clock=fixed_clock,
    )

    after = {
        path: path.read_bytes()
        for path in paths
    }

    assert before == after