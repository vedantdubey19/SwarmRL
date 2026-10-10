import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from sensors.event_logger import TelemetryEventLogger


def fixed_clock() -> datetime:
    return datetime(
        2026,
        10,
        2,
        12,
        30,
        45,
        tzinfo=timezone.utc,
    )


def test_logger_writes_jsonl_event(tmp_path: Path):
    path = tmp_path / "events.jsonl"
    logger = TelemetryEventLogger(
        path,
        clock=fixed_clock,
    )

    logger.open()

    record = logger.log(
        "service_started",
        details={
            "session_id": "demo-001",
            "step": 4,
        },
    )

    logger.close()

    lines = path.read_text(
        encoding="utf-8"
    ).splitlines()

    assert len(lines) == 1

    stored = json.loads(lines[0])

    assert record == stored
    assert stored == {
        "timestamp": "2026-10-02T12:30:45+00:00",
        "event": "service_started",
        "level": "info",
        "details": {
            "session_id": "demo-001",
            "step": 4,
        },
    }


def test_logger_appends_events(tmp_path: Path):
    path = tmp_path / "events.jsonl"

    with TelemetryEventLogger(
        path,
        clock=fixed_clock,
    ) as logger:
        logger.log("service_started")
        logger.log(
            "message_recorded",
            level="warning",
            details={"step": 5},
        )

    lines = path.read_text(
        encoding="utf-8"
    ).splitlines()

    assert len(lines) == 2
    assert json.loads(lines[0])["event"] == "service_started"
    assert json.loads(lines[1])["event"] == "message_recorded"
    assert json.loads(lines[1])["level"] == "warning"


def test_logger_creates_parent_directories(tmp_path: Path):
    path = tmp_path / "nested" / "logs" / "events.jsonl"

    with TelemetryEventLogger(
        path,
        clock=fixed_clock,
    ) as logger:
        logger.log("service_started")

    assert path.exists()


def test_logger_normalizes_level_to_lowercase(
    tmp_path: Path,
):
    path = tmp_path / "events.jsonl"

    with TelemetryEventLogger(
        path,
        clock=fixed_clock,
    ) as logger:
        record = logger.log(
            "service_started",
            level="WARNING",
        )

    assert record["level"] == "warning"


def test_logger_requires_jsonl_suffix(tmp_path: Path):
    with pytest.raises(ValueError):
        TelemetryEventLogger(
            tmp_path / "events.json"
        )


def test_logger_rejects_double_open(tmp_path: Path):
    logger = TelemetryEventLogger(
        tmp_path / "events.jsonl",
        clock=fixed_clock,
    )

    logger.open()

    with pytest.raises(RuntimeError):
        logger.open()

    logger.close()


def test_logger_rejects_logging_before_open(
    tmp_path: Path,
):
    logger = TelemetryEventLogger(
        tmp_path / "events.jsonl",
        clock=fixed_clock,
    )

    with pytest.raises(RuntimeError):
        logger.log("service_started")


def test_logger_close_is_idempotent(tmp_path: Path):
    logger = TelemetryEventLogger(
        tmp_path / "events.jsonl",
        clock=fixed_clock,
    )

    logger.open()
    logger.close()
    logger.close()

    assert logger.is_open is False


@pytest.mark.parametrize(
    "event",
    [
        "",
        "   ",
        1,
        None,
    ],
)
def test_logger_rejects_invalid_event(
    tmp_path: Path,
    event,
):
    with TelemetryEventLogger(
        tmp_path / "events.jsonl",
        clock=fixed_clock,
    ) as logger:
        with pytest.raises(ValueError):
            logger.log(event)


@pytest.mark.parametrize(
    "level",
    [
        "",
        "invalid",
        1,
        None,
    ],
)
def test_logger_rejects_invalid_level(
    tmp_path: Path,
    level,
):
    with TelemetryEventLogger(
        tmp_path / "events.jsonl",
        clock=fixed_clock,
    ) as logger:
        with pytest.raises(ValueError):
            logger.log(
                "service_started",
                level=level,
            )


def test_logger_rejects_non_mapping_details(
    tmp_path: Path,
):
    with TelemetryEventLogger(
        tmp_path / "events.jsonl",
        clock=fixed_clock,
    ) as logger:
        with pytest.raises(TypeError):
            logger.log(
                "service_started",
                details=["not", "a", "mapping"],
            )


def test_logger_rejects_non_serializable_details(
    tmp_path: Path,
):
    with TelemetryEventLogger(
        tmp_path / "events.jsonl",
        clock=fixed_clock,
    ) as logger:
        with pytest.raises(
            TypeError,
            match="JSON serializable",
        ):
            logger.log(
                "service_started",
                details={"invalid": {1, 2}},
            )


def test_logger_rejects_non_datetime_clock_value(
    tmp_path: Path,
):
    logger = TelemetryEventLogger(
        tmp_path / "events.jsonl",
        clock=lambda: "not a datetime",
    )

    logger.open()

    with pytest.raises(TypeError):
        logger.log("service_started")

    logger.close()


def test_logger_rejects_naive_clock_value(
    tmp_path: Path,
):
    logger = TelemetryEventLogger(
        tmp_path / "events.jsonl",
        clock=lambda: datetime(2026, 10, 2, 12, 0, 0),
    )

    logger.open()

    with pytest.raises(ValueError):
        logger.log("service_started")

    logger.close()


def test_context_manager_closes_logger(tmp_path: Path):
    logger = TelemetryEventLogger(
        tmp_path / "events.jsonl",
        clock=fixed_clock,
    )

    with logger:
        assert logger.is_open is True
        logger.log("service_started")

    assert logger.is_open is False