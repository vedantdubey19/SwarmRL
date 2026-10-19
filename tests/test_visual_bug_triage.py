import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from sensors.visual_bug_triage import (
    VisualBugTriage,
    VisualBugTriageError,
    export_visual_bug_triage,
    triage_visual_bug,
    update_visual_bug_status,
)


def fixed_clock():
    return datetime(
        2026,
        10,
        19,
        9,
        30,
        0,
        tzinfo=timezone.utc,
    )


def make_bug():
    return triage_visual_bug(
        bug_id="VIS-001",
        title="Cone of vision flickers",
        description=(
            "Sensor cone flickers when 50 drones "
            "move quickly."
        ),
        severity="high",
        clock=fixed_clock,
    )


def test_creates_low_severity_bug():
    bug = triage_visual_bug(
        bug_id="VIS-002",
        title="Minor label overlap",
        description="Chart labels overlap on small screens.",
        severity="low",
        clock=fixed_clock,
    )

    assert bug.severity == "low"
    assert bug.status == "open"
    assert bug.assigned_to == "Saju"


def test_creates_critical_bug():
    bug = triage_visual_bug(
        bug_id="VIS-003",
        title="Rendering feed stops",
        description="Drone rendering feed stops after reconnect.",
        severity="critical",
        clock=fixed_clock,
    )

    assert bug.severity == "critical"
    assert bug.status == "open"


def test_default_status_and_assignee():
    bug = make_bug()

    assert bug.status == "open"
    assert bug.assigned_to == "Saju"


def test_created_at_is_timezone_aware():
    bug = make_bug()

    timestamp = datetime.fromisoformat(
        bug.created_at
    )

    assert timestamp.tzinfo is not None
    assert timestamp.utcoffset() is not None
    assert bug.created_at == (
        "2026-10-19T09:30:00+00:00"
    )


@pytest.mark.parametrize(
    "severity",
    ["invalid", "", "urgent"],
)
def test_invalid_severity_is_rejected(severity):
    with pytest.raises(VisualBugTriageError):
        triage_visual_bug(
            bug_id="VIS-004",
            title="Invalid severity",
            description="Severity value is invalid.",
            severity=severity,
            clock=fixed_clock,
        )


def test_empty_title_is_rejected():
    with pytest.raises(VisualBugTriageError):
        triage_visual_bug(
            bug_id="VIS-004",
            title=" ",
            description="Title is empty.",
            severity="medium",
            clock=fixed_clock,
        )


def test_empty_description_is_rejected():
    with pytest.raises(VisualBugTriageError):
        triage_visual_bug(
            bug_id="VIS-005",
            title="Missing description",
            description=" ",
            severity="medium",
            clock=fixed_clock,
        )


def test_invalid_clock_type_is_rejected():
    with pytest.raises(TypeError):
        triage_visual_bug(
            bug_id="VIS-005",
            title="Invalid clock",
            description="Clock returns an invalid type.",
            severity="medium",
            clock=lambda: "invalid",
        )


def test_naive_clock_is_rejected():
    with pytest.raises(VisualBugTriageError):
        triage_visual_bug(
            bug_id="VIS-006",
            title="Naive clock",
            description="Clock returns a naive datetime.",
            severity="medium",
            clock=lambda: datetime(
                2026,
                10,
                19,
                9,
                30,
            ),
        )


def test_status_can_be_updated():
    bug = make_bug()
    updated = update_visual_bug_status(
        bug,
        "in_progress",
    )

    assert updated.status == "in_progress"
    assert bug.status == "open"


def test_invalid_status_is_rejected():
    bug = make_bug()

    with pytest.raises(VisualBugTriageError):
        update_visual_bug_status(
            bug,
            "invalid",
        )


def test_triage_is_json_serializable():
    bug = make_bug()

    encoded = bug.to_json()
    decoded = json.loads(encoded)

    assert decoded["bug_id"] == "VIS-001"
    assert decoded["severity"] == "high"
    assert decoded["status"] == "open"


def test_export_writes_json(tmp_path: Path):
    bug = make_bug()
    output = tmp_path / "nested" / "VIS-001.json"

    export_visual_bug_triage(
        bug,
        output,
    )

    assert output.exists()

    decoded = json.loads(
        output.read_text(encoding="utf-8")
    )

    assert decoded["bug_id"] == "VIS-001"


def test_export_requires_json_suffix(tmp_path: Path):
    bug = make_bug()

    with pytest.raises(VisualBugTriageError):
        export_visual_bug_triage(
            bug,
            tmp_path / "VIS-001.txt",
        )


def test_source_bug_is_not_modified():
    bug = make_bug()
    before = bug.to_dict()

    update_visual_bug_status(
        bug,
        "resolved",
    )

    assert bug.to_dict() == before