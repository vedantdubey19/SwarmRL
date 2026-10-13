import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from sensors.event_reader import (
    TelemetryEventReadError,
    TelemetryEventReader,
)


def make_record(
    timestamp: str = "2026-10-03T10:00:00+00:00",
    event: str = "service_started",
    level: str = "info",
    details: dict | None = None,
) -> dict:
    return {
        "timestamp": timestamp,
        "event": event,
        "level": level,
        "details": details or {},
    }


def write_events(
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


def test_read_returns_validated_events_in_order(
    tmp_path: Path,
):
    path = tmp_path / "events.jsonl"

    write_events(
        path,
        [
            make_record(
                event="service_started",
            ),
            make_record(
                timestamp=(
                    "2026-10-03T10:01:00+00:00"
                ),
                event="message_recorded",
                level="warning",
                details={"step": 2},
            ),
        ],
    )

    reader = TelemetryEventReader(path)
    events = reader.read()

    assert len(events) == 2
    assert events[0]["event"] == "service_started"
    assert events[1]["event"] == "message_recorded"
    assert events[1]["level"] == "warning"
    assert events[1]["details"] == {"step": 2}


def test_read_normalizes_timestamp_to_utc(
    tmp_path: Path,
):
    path = tmp_path / "events.jsonl"

    write_events(
        path,
        [
            make_record(
                timestamp=(
                    "2026-10-03T15:30:00+05:30"
                )
            )
        ],
    )

    event = TelemetryEventReader(path).read()[0]

    assert event["timestamp"] == (
        "2026-10-03T10:00:00+00:00"
    )


def test_read_ignores_blank_lines(tmp_path: Path):
    path = tmp_path / "events.jsonl"

    path.write_text(
        "\n"
        + json.dumps(make_record())
        + "\n\n"
        + json.dumps(
            make_record(
                event="service_stopped"
            )
        )
        + "\n",
        encoding="utf-8",
    )

    events = TelemetryEventReader(path).read()

    assert len(events) == 2


def test_filter_by_event(tmp_path: Path):
    path = tmp_path / "events.jsonl"

    write_events(
        path,
        [
            make_record(
                event="service_started",
            ),
            make_record(
                event="message_recorded",
            ),
            make_record(
                event="service_started",
            ),
        ],
    )

    events = TelemetryEventReader(path).filter(
        event="service_started"
    )

    assert len(events) == 2
    assert all(
        record["event"] == "service_started"
        for record in events
    )


def test_filter_by_level_case_insensitive(
    tmp_path: Path,
):
    path = tmp_path / "events.jsonl"

    write_events(
        path,
        [
            make_record(level="info"),
            make_record(
                event="message_failed",
                level="error",
            ),
            make_record(
                event="message_delayed",
                level="warning",
            ),
        ],
    )

    events = TelemetryEventReader(path).filter(
        level="ERROR"
    )

    assert len(events) == 1
    assert events[0]["event"] == "message_failed"
    assert events[0]["level"] == "error"


def test_filter_by_time_range(tmp_path: Path):
    path = tmp_path / "events.jsonl"

    write_events(
        path,
        [
            make_record(
                timestamp=(
                    "2026-10-03T10:00:00+00:00"
                )
            ),
            make_record(
                timestamp=(
                    "2026-10-03T10:05:00+00:00"
                ),
                event="message_recorded",
            ),
            make_record(
                timestamp=(
                    "2026-10-03T10:10:00+00:00"
                ),
                event="service_stopped",
            ),
        ],
    )

    events = TelemetryEventReader(path).filter(
        start=datetime(
            2026,
            10,
            3,
            10,
            5,
            tzinfo=timezone.utc,
        ),
        end=datetime(
            2026,
            10,
            3,
            10,
            10,
            tzinfo=timezone.utc,
        ),
    )

    assert len(events) == 2
    assert [
        record["event"] for record in events
    ] == [
        "message_recorded",
        "service_stopped",
    ]


def test_filter_combines_all_conditions(
    tmp_path: Path,
):
    path = tmp_path / "events.jsonl"

    write_events(
        path,
        [
            make_record(
                timestamp=(
                    "2026-10-03T10:00:00+00:00"
                ),
                event="message_recorded",
                level="info",
            ),
            make_record(
                timestamp=(
                    "2026-10-03T10:01:00+00:00"
                ),
                event="message_recorded",
                level="error",
            ),
            make_record(
                timestamp=(
                    "2026-10-03T10:02:00+00:00"
                ),
                event="other",
                level="error",
            ),
        ],
    )

    events = TelemetryEventReader(path).filter(
        event="message_recorded",
        level="error",
        start=datetime(
            2026,
            10,
            3,
            10,
            1,
            tzinfo=timezone.utc,
        ),
    )

    assert len(events) == 1
    assert events[0]["event"] == "message_recorded"
    assert events[0]["level"] == "error"


def test_summary_counts_events_and_levels(
    tmp_path: Path,
):
    path = tmp_path / "events.jsonl"

    write_events(
        path,
        [
            make_record(
                event="service_started",
                level="info",
            ),
            make_record(
                event="message_recorded",
                level="info",
            ),
            make_record(
                event="message_recorded",
                level="warning",
            ),
            make_record(
                event="message_failed",
                level="error",
            ),
        ],
    )

    summary = TelemetryEventReader(path).summary()

    assert summary == {
        "total_events": 4,
        "by_event": {
            "message_failed": 1,
            "message_recorded": 2,
            "service_started": 1,
        },
        "by_level": {
            "error": 1,
            "info": 2,
            "warning": 1,
        },
    }


def test_reader_requires_jsonl_suffix(tmp_path: Path):
    with pytest.raises(ValueError):
        TelemetryEventReader(tmp_path / "events.json")


def test_missing_file_raises_file_not_found(
    tmp_path: Path,
):
    reader = TelemetryEventReader(
        tmp_path / "missing.jsonl"
    )

    with pytest.raises(FileNotFoundError):
        reader.read()


def test_invalid_json_is_rejected(tmp_path: Path):
    path = tmp_path / "events.jsonl"
    path.write_text(
        '{"timestamp":\n',
        encoding="utf-8",
    )

    with pytest.raises(
        TelemetryEventReadError,
        match="Line 1 is not valid JSON",
    ):
        TelemetryEventReader(path).read()


def test_non_object_record_is_rejected(
    tmp_path: Path,
):
    path = tmp_path / "events.jsonl"
    path.write_text(
        '["not", "an", "object"]\n',
        encoding="utf-8",
    )

    with pytest.raises(
        TelemetryEventReadError,
        match="must contain a JSON object",
    ):
        TelemetryEventReader(path).read()


def test_invalid_timestamp_is_rejected(
    tmp_path: Path,
):
    path = tmp_path / "events.jsonl"

    write_events(
        path,
        [
            make_record(timestamp="invalid"),
        ],
    )

    with pytest.raises(
        TelemetryEventReadError,
        match="not valid ISO-8601",
    ):
        TelemetryEventReader(path).read()


def test_naive_timestamp_is_rejected(
    tmp_path: Path,
):
    path = tmp_path / "events.jsonl"

    write_events(
        path,
        [
            make_record(
                timestamp="2026-10-03T10:00:00"
            ),
        ],
    )

    with pytest.raises(
        TelemetryEventReadError,
        match="must include a timezone",
    ):
        TelemetryEventReader(path).read()


@pytest.mark.parametrize(
    "event",
    [
        "",
        "   ",
        1,
        None,
    ],
)
def test_invalid_event_is_rejected(
    tmp_path: Path,
    event,
):
    path = tmp_path / "events.jsonl"

    write_events(
        path,
        [
            make_record(event=event),
        ],
    )

    with pytest.raises(
        TelemetryEventReadError,
        match="event must be a non-empty string",
    ):
        TelemetryEventReader(path).read()


@pytest.mark.parametrize(
    "level",
    [
        "",
        "invalid",
        1,
        None,
    ],
)
def test_invalid_level_is_rejected(
    tmp_path: Path,
    level,
):
    path = tmp_path / "events.jsonl"

    write_events(
        path,
        [
            make_record(level=level),
        ],
    )

    with pytest.raises(
        TelemetryEventReadError,
        match=(
            "level must be a non-empty string"
            "|level is not supported"
        ),
    ):
        TelemetryEventReader(path).read()


def test_non_mapping_details_are_rejected(
    tmp_path: Path,
):
    path = tmp_path / "events.jsonl"

    write_events(
        path,
        [
            make_record(
                details=["not", "an", "object"]
            ),
        ],
    )

    with pytest.raises(
        TelemetryEventReadError,
        match="details must be an object",
    ):
        TelemetryEventReader(path).read()


def test_invalid_event_filter_is_rejected(
    tmp_path: Path,
):
    path = tmp_path / "events.jsonl"
    write_events(path, [make_record()])

    with pytest.raises(ValueError):
        TelemetryEventReader(path).filter(event="")


def test_invalid_level_filter_is_rejected(
    tmp_path: Path,
):
    path = tmp_path / "events.jsonl"
    write_events(path, [make_record()])

    with pytest.raises(ValueError):
        TelemetryEventReader(path).filter(
            level="invalid"
        )


def test_non_datetime_filter_is_rejected(
    tmp_path: Path,
):
    path = tmp_path / "events.jsonl"
    write_events(path, [make_record()])

    with pytest.raises(TypeError):
        TelemetryEventReader(path).filter(
            start="2026-10-03T10:00:00+00:00"
        )


def test_naive_filter_is_rejected(
    tmp_path: Path,
):
    path = tmp_path / "events.jsonl"
    write_events(path, [make_record()])

    with pytest.raises(ValueError):
        TelemetryEventReader(path).filter(
            start=datetime(2026, 10, 3, 10, 0)
        )


def test_inverted_time_range_is_rejected(
    tmp_path: Path,
):
    path = tmp_path / "events.jsonl"
    write_events(path, [make_record()])

    with pytest.raises(
        ValueError,
        match="start must not be later than end",
    ):
        TelemetryEventReader(path).filter(
            start=datetime(
                2026,
                10,
                3,
                11,
                0,
                tzinfo=timezone.utc,
            ),
            end=datetime(
                2026,
                10,
                3,
                10,
                0,
                tzinfo=timezone.utc,
            ),
        )