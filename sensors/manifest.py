from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


class TelemetryManifestError(ValueError):
    """Raised when a telemetry manifest cannot be built or verified."""


@dataclass(frozen=True)
class ArtifactMetadata:
    """Metadata for one telemetry artifact."""

    path: str
    size_bytes: int
    sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
        }


@dataclass(frozen=True)
class TelemetryManifest:
    """Manifest describing one telemetry artifact bundle."""

    schema_version: int
    generated_at: str
    artifacts: dict[str, ArtifactMetadata]
    counts: dict[str, int]
    healthy: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "artifacts": {
                name: artifact.to_dict()
                for name, artifact in self.artifacts.items()
            },
            "counts": dict(self.counts),
            "healthy": self.healthy,
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            indent=2,
            sort_keys=True,
        )


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

    return timestamp.astimezone(timezone.utc).isoformat()


def _validate_artifact_path(
    path: Path,
    expected_suffix: str,
    label: str,
) -> None:
    if path.suffix.lower() != expected_suffix:
        raise TelemetryManifestError(
            f"{label} path must have a "
            f"{expected_suffix} suffix."
        )

    if not path.is_file():
        raise TelemetryManifestError(
            f"{label} file does not exist."
        )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def _artifact_metadata(path: Path) -> ArtifactMetadata:
    return ArtifactMetadata(
        path=str(path),
        size_bytes=path.stat().st_size,
        sha256=_sha256(path),
    )


def _count_jsonl_records(path: Path) -> int:
    count = 0

    try:
        with path.open(
            encoding="utf-8"
        ) as file:
            for line_number, line in enumerate(
                file,
                start=1,
            ):
                if not line.strip():
                    continue

                try:
                    json.loads(line)
                except json.JSONDecodeError as error:
                    raise TelemetryManifestError(
                        f"Invalid JSON on line "
                        f"{line_number} of {path}."
                    ) from error

                count += 1
    except OSError as error:
        raise TelemetryManifestError(
            f"Could not read JSONL file: {path}."
        ) from error

    return count


def _count_jsonl_events(path: Path) -> int:
    return _count_jsonl_records(path)


def _read_health(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as error:
        raise TelemetryManifestError(
            "Health file is not valid JSON."
        ) from error

    if not isinstance(payload, dict):
        raise TelemetryManifestError(
            "Health file must contain a JSON object."
        )

    if not isinstance(
        payload.get("healthy"),
        bool,
    ):
        raise TelemetryManifestError(
            "Health file must contain a boolean "
            "'healthy' field."
        )

    return payload


def build_telemetry_manifest(
    metrics_path: Path | str,
    events_path: Path | str,
    report_path: Path | str,
    health_path: Path | str,
    *,
    clock: Callable[[], datetime] | None = None,
) -> TelemetryManifest:
    """Build a manifest for a telemetry artifact bundle."""
    metrics = Path(metrics_path)
    events = Path(events_path)
    report = Path(report_path)
    health = Path(health_path)

    _validate_artifact_path(
        metrics,
        ".jsonl",
        "Metrics",
    )
    _validate_artifact_path(
        events,
        ".jsonl",
        "Events",
    )
    _validate_artifact_path(
        report,
        ".json",
        "Report",
    )
    _validate_artifact_path(
        health,
        ".json",
        "Health",
    )

    health_payload = _read_health(health)

    artifacts = {
        "metrics": _artifact_metadata(metrics),
        "events": _artifact_metadata(events),
        "report": _artifact_metadata(report),
        "health": _artifact_metadata(health),
    }

    counts = {
        "metrics_records": _count_jsonl_records(metrics),
        "event_records": _count_jsonl_events(events),
    }

    return TelemetryManifest(
        schema_version=1,
        generated_at=_checked_timestamp(
            clock or _default_clock
        ),
        artifacts=artifacts,
        counts=counts,
        healthy=health_payload["healthy"],
    )


def export_telemetry_manifest(
    manifest: TelemetryManifest,
    output_path: Path | str,
) -> None:
    """Export a manifest as formatted JSON."""
    if not isinstance(
        manifest,
        TelemetryManifest,
    ):
        raise TypeError(
            "manifest must be a TelemetryManifest."
        )

    output = Path(output_path)

    if output.suffix.lower() != ".json":
        raise TelemetryManifestError(
            "Manifest output path must have a .json suffix."
        )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
        manifest.to_json() + "\n",
        encoding="utf-8",
    )


def verify_telemetry_manifest(
    manifest: TelemetryManifest,
    metrics_path: Path | str,
    events_path: Path | str,
    report_path: Path | str,
    health_path: Path | str,
) -> bool:
    """Return whether the supplied files match the manifest."""
    if not isinstance(
        manifest,
        TelemetryManifest,
    ):
        raise TypeError(
            "manifest must be a TelemetryManifest."
        )

    paths = {
        "metrics": Path(metrics_path),
        "events": Path(events_path),
        "report": Path(report_path),
        "health": Path(health_path),
    }

    suffixes = {
        "metrics": ".jsonl",
        "events": ".jsonl",
        "report": ".json",
        "health": ".json",
    }

    labels = {
        "metrics": "Metrics",
        "events": "Events",
        "report": "Report",
        "health": "Health",
    }

    for name, path in paths.items():
        _validate_artifact_path(
            path,
            suffixes[name],
            labels[name],
        )

        expected = manifest.artifacts.get(name)

        if expected is None:
            raise TelemetryManifestError(
                f"Manifest is missing '{name}' metadata."
            )

        actual = _artifact_metadata(path)

        if actual.path != expected.path:
            return False

        if actual.size_bytes != expected.size_bytes:
            return False

        if actual.sha256 != expected.sha256:
            return False

    return True