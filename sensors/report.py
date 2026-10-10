import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sensors.event_reader import TelemetryEventReader
from sensors.session_summary import (
    TelemetrySessionSummary,
    summarize_telemetry_session,
)


class TelemetryReportError(ValueError):
    """Raised when a telemetry report cannot be built."""


@dataclass(frozen=True)
class TelemetryReport:
    """Combined telemetry summary and event-log report."""

    generated_at: str
    metrics_file: str
    events_file: str
    session_summary: dict[str, Any]
    event_summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible report dictionary."""
        return {
            "generated_at": self.generated_at,
            "metrics_file": self.metrics_file,
            "events_file": self.events_file,
            "session_summary": dict(self.session_summary),
            "event_summary": dict(self.event_summary),
        }

    def to_json(self) -> str:
        """Serialize the report as formatted JSON."""
        return json.dumps(
            self.to_dict(),
            indent=2,
            sort_keys=True,
        )


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def build_telemetry_report(
    metrics_path: Path | str,
    events_path: Path | str,
    *,
    clock=None,
) -> TelemetryReport:
    """Build one report from telemetry and event JSON-lines files."""
    metrics_path = Path(metrics_path)
    events_path = Path(events_path)

    if metrics_path.suffix.lower() != ".jsonl":
        raise ValueError(
            "metrics_path must have a .jsonl suffix."
        )

    if events_path.suffix.lower() != ".jsonl":
        raise ValueError(
            "events_path must have a .jsonl suffix."
        )

    if not metrics_path.exists():
        raise FileNotFoundError(metrics_path)

    if not events_path.exists():
        raise FileNotFoundError(events_path)

    summary = summarize_telemetry_session(metrics_path)
    event_summary = TelemetryEventReader(
        events_path
    ).summary()

    timestamp = (clock or _utc_now)()

    if not isinstance(timestamp, datetime):
        raise TypeError(
            "clock must return a datetime instance."
        )

    if timestamp.tzinfo is None:
        raise ValueError(
            "clock must return a timezone-aware datetime."
        )

    return TelemetryReport(
        generated_at=timestamp.astimezone(
            timezone.utc
        ).isoformat(),
        metrics_file=str(metrics_path),
        events_file=str(events_path),
        session_summary=summary.to_dict(),
        event_summary=event_summary,
    )


def export_telemetry_report(
    report: TelemetryReport,
    output_path: Path | str,
) -> Path:
    """Write a telemetry report as formatted JSON."""
    if not isinstance(report, TelemetryReport):
        raise TypeError(
            "report must be a TelemetryReport instance."
        )

    output_path = Path(output_path)

    if output_path.suffix.lower() != ".json":
        raise ValueError(
            "output_path must have a .json suffix."
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        report.to_json() + "\n",
        encoding="utf-8",
    )

    return output_path


def build_and_export_telemetry_report(
    metrics_path: Path | str,
    events_path: Path | str,
    output_path: Path | str,
    *,
    clock=None,
) -> TelemetryReport:
    """Build and export a report in one operation."""
    report = build_telemetry_report(
        metrics_path,
        events_path,
        clock=clock,
    )

    export_telemetry_report(
        report,
        output_path,
    )

    return report