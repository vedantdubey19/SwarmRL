import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


class TelemetryEventLogger:
    """Write structured telemetry lifecycle events as JSON-lines."""

    def __init__(
        self,
        path: Path | str,
        *,
        clock=None,
    ) -> None:
        path = Path(path)

        if path.suffix.lower() != ".jsonl":
            raise ValueError(
                "path must have a .jsonl suffix."
            )

        self.path = path
        self._clock = clock or (
            lambda: datetime.now(timezone.utc)
        )
        self._file = None

    @property
    def is_open(self) -> bool:
        """Return whether the event log is open."""
        return self._file is not None

    def open(self) -> None:
        """Open the event log for appending."""
        if self._file is not None:
            raise RuntimeError(
                "TelemetryEventLogger is already open."
            )

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._file = self.path.open(
            "a",
            encoding="utf-8",
            newline="",
        )

    def close(self) -> None:
        """Flush and close the event log."""
        if self._file is None:
            return

        self._file.flush()
        self._file.close()
        self._file = None

    def log(
        self,
        event: str,
        *,
        level: str = "info",
        details: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Append one validated structured event and return it."""
        if self._file is None:
            raise RuntimeError(
                "TelemetryEventLogger must be opened before logging."
            )

        if not isinstance(event, str) or not event.strip():
            raise ValueError(
                "event must be a non-empty string."
            )

        if not isinstance(level, str) or not level.strip():
            raise ValueError(
                "level must be a non-empty string."
            )

        normalized_level = level.lower()

        if normalized_level not in {
            "debug",
            "info",
            "warning",
            "error",
        }:
            raise ValueError(
                "level must be debug, info, warning, or error."
            )

        if details is None:
            details_dict: dict[str, Any] = {}
        elif isinstance(details, Mapping):
            details_dict = dict(details)
        else:
            raise TypeError(
                "details must be a mapping when provided."
            )

        timestamp = self._clock()

        if not isinstance(timestamp, datetime):
            raise TypeError(
                "clock must return a datetime instance."
            )

        if timestamp.tzinfo is None:
            raise ValueError(
                "clock must return a timezone-aware datetime."
            )

        record = {
            "timestamp": timestamp.astimezone(
                timezone.utc
            ).isoformat(),
            "event": event,
            "level": normalized_level,
            "details": details_dict,
        }

        try:
            encoded = json.dumps(
                record,
                separators=(",", ":"),
                sort_keys=True,
            )
        except TypeError as error:
            raise TypeError(
                "details must be JSON serializable."
            ) from error

        self._file.write(encoded)
        self._file.write("\n")
        self._file.flush()

        return record

    def __enter__(self):
        self.open()
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        self.close()