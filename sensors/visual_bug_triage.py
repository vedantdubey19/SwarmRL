from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


class VisualBugTriageError(ValueError):
    """Raised when a visual bug cannot be created, updated, or exported."""


VALID_SEVERITIES = (
    "low",
    "medium",
    "high",
    "critical",
)

VALID_STATUSES = (
    "open",
    "in_progress",
    "resolved",
    "closed",
)


@dataclass(frozen=True)
class VisualBugTriage:
    """Triage record for one visual integration bug."""

    bug_id: str
    title: str
    description: str
    severity: str
    status: str
    assigned_to: str
    created_at: str

    def __post_init__(self) -> None:
        if not isinstance(self.bug_id, str) or not self.bug_id.strip():
            raise VisualBugTriageError(
                "bug_id must be a non-empty string."
            )

        if not isinstance(self.title, str) or not self.title.strip():
            raise VisualBugTriageError(
                "title must be a non-empty string."
            )

        if (
            not isinstance(self.description, str)
            or not self.description.strip()
        ):
            raise VisualBugTriageError(
                "description must be a non-empty string."
            )

        if self.severity not in VALID_SEVERITIES:
            raise VisualBugTriageError(
                f"severity must be one of: "
                f"{', '.join(VALID_SEVERITIES)}."
            )

        if self.status not in VALID_STATUSES:
            raise VisualBugTriageError(
                f"status must be one of: "
                f"{', '.join(VALID_STATUSES)}."
            )

        if (
            not isinstance(self.assigned_to, str)
            or not self.assigned_to.strip()
        ):
            raise VisualBugTriageError(
                "assigned_to must be a non-empty string."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "bug_id": self.bug_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "status": self.status,
            "assigned_to": self.assigned_to,
            "created_at": self.created_at,
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
        raise VisualBugTriageError(
            "clock must return a timezone-aware datetime."
        )

    return timestamp.astimezone(
        timezone.utc
    ).isoformat()


def triage_visual_bug(
    bug_id: str,
    title: str,
    description: str,
    severity: str,
    *,
    status: str = "open",
    assigned_to: str = "Saju",
    clock: Callable[[], datetime] | None = None,
) -> VisualBugTriage:
    """Create a triage record for one visual integration bug."""
    return VisualBugTriage(
        bug_id=bug_id,
        title=title,
        description=description,
        severity=severity,
        status=status,
        assigned_to=assigned_to,
        created_at=_checked_timestamp(
            clock or _default_clock
        ),
    )


def update_visual_bug_status(
    bug: VisualBugTriage,
    status: str,
) -> VisualBugTriage:
    """Return a new bug record with an updated status."""
    if not isinstance(bug, VisualBugTriage):
        raise TypeError(
            "bug must be a VisualBugTriage instance."
        )

    if status not in VALID_STATUSES:
        raise VisualBugTriageError(
            f"status must be one of: "
            f"{', '.join(VALID_STATUSES)}."
        )

    return replace(bug, status=status)


def export_visual_bug_triage(
    bug: VisualBugTriage,
    output_path: Path | str,
) -> None:
    """Export a visual bug triage record as formatted JSON."""
    if not isinstance(bug, VisualBugTriage):
        raise TypeError(
            "bug must be a VisualBugTriage instance."
        )

    output = Path(output_path)

    if output.suffix.lower() != ".json":
        raise VisualBugTriageError(
            "Triage output path must have a .json suffix."
        )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
        bug.to_json() + "\n",
        encoding="utf-8",
    )