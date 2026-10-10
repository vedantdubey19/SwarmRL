import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


class TelemetryEventReadError(ValueError):
    """Raised when an event log cannot be read or validated."""


VALID_LEVELS = frozenset(
    {
        "debug",
        "info",
        "warning",
        "error",
    }
)


class TelemetryEventReader:
    """Read, validate, filter, and summarize telemetry event logs."""

    def __init__(
        self,
        path: Path | str,
    ) -> None:
        path = Path(path)

        if path.suffix.lower() != ".jsonl":
            raise ValueError(
                "path must have a .jsonl suffix."
            )

        self.path = path

    @staticmethod
    def _parse_timestamp(
        value: Any,
        line_number: int,
    ) -> datetime:
        """Parse and normalize one timezone-aware timestamp."""
        if not isinstance(value, str) or not value.strip():
            raise TelemetryEventReadError(
                f"Line {line_number} timestamp "
                "must be a non-empty string."
            )

        try:
            timestamp = datetime.fromisoformat(value)
        except ValueError as error:
            raise TelemetryEventReadError(
                f"Line {line_number} timestamp "
                "is not valid ISO-8601."
            ) from error

        if timestamp.tzinfo is None:
            raise TelemetryEventReadError(
                f"Line {line_number} timestamp "
                "must include a timezone."
            )

        return timestamp.astimezone(timezone.utc)

    @classmethod
    def _validate_record(
        cls,
        record: Any,
        line_number: int,
    ) -> dict[str, Any]:
        """Validate one parsed event record."""
        if not isinstance(record, Mapping):
            raise TelemetryEventReadError(
                f"Line {line_number} must contain "
                "a JSON object."
            )

        timestamp = cls._parse_timestamp(
            record.get("timestamp"),
            line_number,
        )

        event = record.get("event")

        if not isinstance(event, str) or not event.strip():
            raise TelemetryEventReadError(
                f"Line {line_number} event "
                "must be a non-empty string."
            )

        level = record.get("level")

        if not isinstance(level, str) or not level.strip():
            raise TelemetryEventReadError(
                f"Line {line_number} level "
                "must be a non-empty string."
            )

        normalized_level = level.lower()

        if normalized_level not in VALID_LEVELS:
            raise TelemetryEventReadError(
                f"Line {line_number} level "
                "is not supported."
            )

        details = record.get("details")

        if not isinstance(details, Mapping):
            raise TelemetryEventReadError(
                f"Line {line_number} details "
                "must be an object."
            )

        return {
            "timestamp": timestamp.isoformat(),
            "event": event,
            "level": normalized_level,
            "details": dict(details),
        }

    @staticmethod
    def _normalize_filter_timestamp(
        value: datetime | None,
        name: str,
    ) -> datetime | None:
        """Validate and normalize a time-range filter endpoint."""
        if value is None:
            return None

        if not isinstance(value, datetime):
            raise TypeError(
                f"{name} must be a datetime when provided."
            )

        if value.tzinfo is None:
            raise ValueError(
                f"{name} must be timezone-aware."
            )

        return value.astimezone(timezone.utc)

    def read(self) -> list[dict[str, Any]]:
        """Read all nonblank validated event records in file order."""
        if not self.path.exists():
            raise FileNotFoundError(self.path)

        events = []

        with self.path.open(encoding="utf-8") as file:
            for line_number, line in enumerate(
                file,
                start=1,
            ):
                stripped = line.strip()

                if not stripped:
                    continue

                try:
                    record = json.loads(stripped)
                except json.JSONDecodeError as error:
                    raise TelemetryEventReadError(
                        f"Line {line_number} is not valid JSON."
                    ) from error

                events.append(
                    self._validate_record(
                        record,
                        line_number,
                    )
                )

        return events

    def filter(
        self,
        *,
        event: str | None = None,
        level: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Return validated events that match supplied filters."""
        if event is not None:
            if not isinstance(event, str) or not event.strip():
                raise ValueError(
                    "event filter must be a non-empty string."
                )

        if level is not None:
            if not isinstance(level, str) or not level.strip():
                raise ValueError(
                    "level filter must be a non-empty string."
                )

            level = level.lower()

            if level not in VALID_LEVELS:
                raise ValueError(
                    "level filter is not supported."
                )

        start = self._normalize_filter_timestamp(
            start,
            "start",
        )
        end = self._normalize_filter_timestamp(
            end,
            "end",
        )

        if start is not None and end is not None and start > end:
            raise ValueError(
                "start must not be later than end."
            )

        filtered = []

        for record in self.read():
            timestamp = datetime.fromisoformat(
                record["timestamp"]
            )

            if event is not None and record["event"] != event:
                continue

            if level is not None and record["level"] != level:
                continue

            if start is not None and timestamp < start:
                continue

            if end is not None and timestamp > end:
                continue

            filtered.append(record)

        return filtered

    def summary(self) -> dict[str, Any]:
        """Return record totals grouped by event name and level."""
        events = self.read()

        by_event = Counter(
            record["event"] for record in events
        )
        by_level = Counter(
            record["level"] for record in events
        )

        return {
            "total_events": len(events),
            "by_event": dict(sorted(by_event.items())),
            "by_level": dict(sorted(by_level.items())),
        }