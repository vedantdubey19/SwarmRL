from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


class TelemetryArchiveError(ValueError):
    """Raised when a telemetry archive cannot be created or verified."""


@dataclass(frozen=True)
class TelemetryArchive:
    """Metadata describing a telemetry bundle archive."""

    schema_version: int
    created_at: str
    archive_path: str
    artifacts: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "created_at": self.created_at,
            "archive_path": self.archive_path,
            "artifacts": list(self.artifacts),
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            indent=2,
            sort_keys=True,
        )


ARTIFACT_NAMES = (
    "metrics.jsonl",
    "events.jsonl",
    "report.json",
    "health.json",
    "manifest.json",
)

ARCHIVE_METADATA_NAME = "archive.json"


def _default_clock() -> datetime:
    return datetime.now(timezone.utc)


def _checked_timestamp(
    clock: Callable[[], datetime],
) -> str:
    timestamp = clock()

    if not isinstance(timestamp, datetime):
        raise TypeError(
            "clock must return a datetime instance."
        )

    if timestamp.tzinfo is None:
        raise ValueError(
            "clock must return a timezone-aware datetime."
        )

    return timestamp.astimezone(
        timezone.utc
    ).isoformat()


def _validate_input_path(
    path: Path,
    expected_suffix: str,
    label: str,
) -> None:
    if path.suffix.lower() != expected_suffix:
        raise TelemetryArchiveError(
            f"{label} path must have a "
            f"{expected_suffix} suffix."
        )

    if not path.is_file():
        raise TelemetryArchiveError(
            f"{label} file does not exist."
        )


def create_telemetry_archive(
    metrics_path: Path | str,
    events_path: Path | str,
    report_path: Path | str,
    health_path: Path | str,
    manifest_path: Path | str,
    output_path: Path | str,
    *,
    clock: Callable[[], datetime] | None = None,
) -> TelemetryArchive:
    """Create a ZIP archive for one telemetry bundle."""
    metrics = Path(metrics_path)
    events = Path(events_path)
    report = Path(report_path)
    health = Path(health_path)
    manifest = Path(manifest_path)
    output = Path(output_path)

    _validate_input_path(
        metrics,
        ".jsonl",
        "Metrics",
    )
    _validate_input_path(
        events,
        ".jsonl",
        "Events",
    )
    _validate_input_path(
        report,
        ".json",
        "Report",
    )
    _validate_input_path(
        health,
        ".json",
        "Health",
    )
    _validate_input_path(
        manifest,
        ".json",
        "Manifest",
    )

    if output.suffix.lower() != ".zip":
        raise TelemetryArchiveError(
            "Archive output path must have a .zip suffix."
        )

    created_at = _checked_timestamp(
        clock or _default_clock
    )

    artifact_sources = {
        "metrics.jsonl": metrics,
        "events.jsonl": events,
        "report.json": report,
        "health.json": health,
        "manifest.json": manifest,
    }

    metadata = {
        "schema_version": 1,
        "created_at": created_at,
        "artifacts": list(artifact_sources),
    }

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with zipfile.ZipFile(
        output,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
    ) as bundle:
        for archive_name, source in (
            artifact_sources.items()
        ):
            bundle.write(
                source,
                arcname=archive_name,
            )

        bundle.writestr(
            ARCHIVE_METADATA_NAME,
            json.dumps(
                metadata,
                indent=2,
                sort_keys=True,
            ) + "\n",
        )

    return TelemetryArchive(
        schema_version=1,
        created_at=created_at,
        archive_path=str(output),
        artifacts=tuple(artifact_sources),
    )


def _read_required_text(
    bundle: zipfile.ZipFile,
    name: str,
) -> str:
    try:
        return bundle.read(
            name
        ).decode("utf-8")
    except KeyError as error:
        raise TelemetryArchiveError(
            f"Archive is missing required entry: {name}."
        ) from error
    except UnicodeDecodeError as error:
        raise TelemetryArchiveError(
            f"Archive entry is not valid UTF-8: {name}."
        ) from error


def verify_telemetry_archive(
    archive_path: Path | str,
) -> bool:
    """Return whether a telemetry archive is valid."""
    archive = Path(archive_path)

    if archive.suffix.lower() != ".zip":
        raise TelemetryArchiveError(
            "Archive path must have a .zip suffix."
        )

    if not archive.is_file():
        raise TelemetryArchiveError(
            "Archive file does not exist."
        )

    try:
        with zipfile.ZipFile(
            archive,
            mode="r",
        ) as bundle:
            required_entries = (
                ARTIFACT_NAMES
                + (ARCHIVE_METADATA_NAME,)
            )

            for entry in required_entries:
                if entry not in bundle.namelist():
                    raise TelemetryArchiveError(
                        f"Archive is missing required "
                        f"entry: {entry}."
                    )

            metadata_text = _read_required_text(
                bundle,
                ARCHIVE_METADATA_NAME,
            )

            try:
                metadata = json.loads(
                    metadata_text
                )
            except json.JSONDecodeError as error:
                raise TelemetryArchiveError(
                    "Archive metadata is not valid JSON."
                ) from error

            if not isinstance(metadata, dict):
                raise TelemetryArchiveError(
                    "Archive metadata must contain "
                    "a JSON object."
                )

            if metadata.get(
                "schema_version"
            ) != 1:
                raise TelemetryArchiveError(
                    "Archive metadata has an "
                    "unsupported schema version."
                )

            _validate_json_entry(
                bundle,
                "report.json",
            )
            _validate_json_entry(
                bundle,
                "health.json",
            )
            _validate_json_entry(
                bundle,
                "manifest.json",
            )

            _validate_jsonl_entry(
                bundle,
                "metrics.jsonl",
            )
            _validate_jsonl_entry(
                bundle,
                "events.jsonl",
            )

    except zipfile.BadZipFile as error:
        raise TelemetryArchiveError(
            "Archive is not a valid ZIP file."
        ) from error

    return True


def _validate_json_entry(
    bundle: zipfile.ZipFile,
    name: str,
) -> None:
    text = _read_required_text(
        bundle,
        name,
    )

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise TelemetryArchiveError(
            f"Archive entry is not valid JSON: {name}."
        ) from error

    if not isinstance(payload, dict):
        raise TelemetryArchiveError(
            f"Archive entry must contain a JSON "
            f"object: {name}."
        )


def _validate_jsonl_entry(
    bundle: zipfile.ZipFile,
    name: str,
) -> None:
    text = _read_required_text(
        bundle,
        name,
    )

    for line_number, line in enumerate(
        text.splitlines(),
        start=1,
    ):
        if not line.strip():
            continue

        try:
            json.loads(line)
        except json.JSONDecodeError as error:
            raise TelemetryArchiveError(
                f"Invalid JSON on line {line_number} "
                f"of archive entry: {name}."
            ) from error