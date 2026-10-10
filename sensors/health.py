import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sensors.event_reader import TelemetryEventReader
from sensors.session_summary import (
    summarize_telemetry_session,
)


class TelemetryHealthError(ValueError):
    """Raised when telemetry health checking cannot continue."""


@dataclass(frozen=True)
class TelemetryHealthResult:
    """Result of validating one telemetry artifact bundle."""

    healthy: bool
    checked_at: str
    metrics_records: int
    event_records: int
    metric_steps_ordered: bool
    report_matches_metrics: bool
    report_matches_events: bool
    issues: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible health result."""
        return {
            "healthy": self.healthy,
            "checked_at": self.checked_at,
            "metrics_records": self.metrics_records,
            "event_records": self.event_records,
            "metric_steps_ordered": (
                self.metric_steps_ordered
            ),
            "report_matches_metrics": (
                self.report_matches_metrics
            ),
            "report_matches_events": (
                self.report_matches_events
            ),
            "issues": list(self.issues),
        }

    def to_json(self) -> str:
        """Serialize the health result as formatted JSON."""
        return json.dumps(
            self.to_dict(),
            indent=2,
            sort_keys=True,
        )


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TelemetryHealthChecker:
    """Validate metrics, events, and report artifact consistency."""

    def __init__(
        self,
        metrics_path: Path | str,
        events_path: Path | str,
        report_path: Path | str,
        *,
        clock=None,
    ) -> None:
        self.metrics_path = Path(metrics_path)
        self.events_path = Path(events_path)
        self.report_path = Path(report_path)
        self._clock = clock or _utc_now

    def _validate_paths(self) -> list[str]:
        """Return path and existence issues."""
        issues = []

        if self.metrics_path.suffix.lower() != ".jsonl":
            issues.append(
                "Metrics path must have a .jsonl suffix."
            )

        if self.events_path.suffix.lower() != ".jsonl":
            issues.append(
                "Events path must have a .jsonl suffix."
            )

        if self.report_path.suffix.lower() != ".json":
            issues.append(
                "Report path must have a .json suffix."
            )

        if not self.metrics_path.exists():
            issues.append("Metrics file does not exist.")

        if not self.events_path.exists():
            issues.append("Events file does not exist.")

        if not self.report_path.exists():
            issues.append("Report file does not exist.")

        return issues

    @staticmethod
    def _steps_are_ordered(
        metrics_records: list[dict[str, Any]],
    ) -> bool:
        """Return whether metric steps increase strictly."""
        steps = [
            int(record["step"])
            for record in metrics_records
        ]

        return all(
            earlier < later
            for earlier, later in zip(
                steps,
                steps[1:],
            )
        )

    def _load_report(self) -> dict[str, Any]:
        """Load and minimally validate the report JSON."""
        try:
            report = json.loads(
                self.report_path.read_text(
                    encoding="utf-8"
                )
            )
        except json.JSONDecodeError as error:
            raise TelemetryHealthError(
                "Report file is not valid JSON."
            ) from error

        if not isinstance(report, dict):
            raise TelemetryHealthError(
                "Report must contain a JSON object."
            )

        return report

    def check(self) -> TelemetryHealthResult:
        """Validate all telemetry artifacts and return a result."""
        issues = self._validate_paths()

        timestamp = self._clock()

        if not isinstance(timestamp, datetime):
            raise TypeError(
                "clock must return a datetime instance."
            )

        if timestamp.tzinfo is None:
            raise ValueError(
                "clock must return a timezone-aware datetime."
            )

        checked_at = timestamp.astimezone(
            timezone.utc
        ).isoformat()

        if issues:
            return TelemetryHealthResult(
                healthy=False,
                checked_at=checked_at,
                metrics_records=0,
                event_records=0,
                metric_steps_ordered=False,
                report_matches_metrics=False,
                report_matches_events=False,
                issues=issues,
            )

        try:
            metrics_summary = summarize_telemetry_session(
                self.metrics_path
            )
        except Exception as error:
            issues.append(
                f"Metrics validation failed: {error}"
            )
            metrics_summary = None

        try:
            events = TelemetryEventReader(
                self.events_path
            ).read()
        except Exception as error:
            issues.append(
                f"Events validation failed: {error}"
            )
            events = []

        try:
            report = self._load_report()
        except Exception as error:
            issues.append(str(error))
            report = {}

        metrics_records = (
            metrics_summary.total_records
            if metrics_summary is not None
            else 0
        )
        event_records = len(events)

        metric_steps_ordered = False

        if metrics_summary is not None:
            try:
                metrics_records_raw = []

                with self.metrics_path.open(
                    encoding="utf-8"
                ) as file:
                    for line in file:
                        if line.strip():
                            metrics_records_raw.append(
                                json.loads(line)
                            )

                metric_steps = [
                    int(
                        record["metrics"]["step"]
                    )
                    for record in metrics_records_raw
                ]

                metric_steps_ordered = all(
                    earlier < later
                    for earlier, later in zip(
                        metric_steps,
                        metric_steps[1:],
                    )
                )

                if not metric_steps_ordered:
                    issues.append(
                        "Metrics steps are not strictly increasing."
                    )
            except Exception as error:
                issues.append(
                    f"Metrics ordering check failed: {error}"
                )

        report_matches_metrics = False
        report_matches_events = False

        session_summary = report.get(
            "session_summary"
        )
        event_summary = report.get(
            "event_summary"
        )

        if not isinstance(session_summary, dict):
            issues.append(
                "Report session_summary is missing or invalid."
            )
        elif metrics_summary is not None:
            expected_metrics = (
                metrics_summary.to_dict()
            )

            report_matches_metrics = (
                session_summary == expected_metrics
            )

            if not report_matches_metrics:
                issues.append(
                    "Report session summary does not "
                    "match metrics."
                )

        if not isinstance(event_summary, dict):
            issues.append(
                "Report event_summary is missing or invalid."
            )
        else:
            expected_events = (
                TelemetryEventReader(
                    self.events_path
                ).summary()
            )

            report_matches_events = (
                event_summary == expected_events
            )

            if not report_matches_events:
                issues.append(
                    "Report event summary does not "
                    "match events."
                )

        report_metrics_path = report.get(
            "metrics_file"
        )
        report_events_path = report.get(
            "events_file"
        )

        if report_metrics_path != str(self.metrics_path):
            issues.append(
                "Report metrics_file does not match "
                "the supplied metrics path."
            )

        if report_events_path != str(self.events_path):
            issues.append(
                "Report events_file does not match "
                "the supplied events path."
            )

        return TelemetryHealthResult(
            healthy=not issues,
            checked_at=checked_at,
            metrics_records=metrics_records,
            event_records=event_records,
            metric_steps_ordered=metric_steps_ordered,
            report_matches_metrics=(
                report_matches_metrics
            ),
            report_matches_events=(
                report_matches_events
            ),
            issues=issues,
        )

    def check_and_export(
        self,
        output_path: Path | str,
    ) -> TelemetryHealthResult:
        """Check artifacts and export the health result as JSON."""
        output_path = Path(output_path)

        if output_path.suffix.lower() != ".json":
            raise ValueError(
                "output_path must have a .json suffix."
            )

        result = self.check()

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path.write_text(
            result.to_json() + "\n",
            encoding="utf-8",
        )

        return result