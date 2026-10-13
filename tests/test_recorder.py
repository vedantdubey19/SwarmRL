import csv
import json
import tempfile
from pathlib import Path

import pytest

from sensors.consumer import TelemetryMessageError
from sensors.recorder import CSV_FIELDS, TelemetryRecorder


def make_message(step: int = 1) -> dict:
    return {
        "type": "swarm_metrics",
        "metrics": {
            "step": step,
            "episode": 2,
            "active_agents": 3,
            "explored_fraction": 0.35,
            "total_reward": 4.5,
            "mean_reward": 1.5,
            "newly_explored_cells": 5,
            "drone_collisions": 1,
            "obstacle_collisions": 2,
            "targets_found": 3,
            "boundary_violations": 4,
            "visible_targets": 5,
            "visible_obstacles": 6,
            "visible_drones": 7,
        },
    }


def test_recorder_writes_jsonl_file(tmp_path: Path):
    json_path = tmp_path / "metrics.jsonl"

    recorder = TelemetryRecorder(json_path)

    recorder.open()
    recorder.record(make_message(1))
    recorder.record(make_message(2))
    recorder.close()

    lines = json_path.read_text(
        encoding="utf-8"
    ).splitlines()

    assert len(lines) == 2

    first = json.loads(lines[0])
    second = json.loads(lines[1])

    assert first["type"] == "swarm_metrics"
    assert first["metrics"]["step"] == 1
    assert second["metrics"]["step"] == 2


def test_recorder_appends_to_existing_jsonl(tmp_path: Path):
    json_path = tmp_path / "metrics.jsonl"

    recorder = TelemetryRecorder(json_path)

    recorder.open()
    recorder.record(make_message(1))
    recorder.close()

    recorder2 = TelemetryRecorder(json_path)

    recorder2.open()
    recorder2.record(make_message(2))
    recorder2.close()

    lines = json_path.read_text(
        encoding="utf-8"
    ).splitlines()

    assert len(lines) == 2
    assert json.loads(lines[0])["metrics"]["step"] == 1
    assert json.loads(lines[1])["metrics"]["step"] == 2


def test_recorder_writes_csv_file(tmp_path: Path):
    json_path = tmp_path / "metrics.jsonl"
    csv_path = tmp_path / "metrics.csv"

    recorder = TelemetryRecorder(
        json_path,
        csv_path=csv_path,
    )

    recorder.open()
    recorder.record(make_message(1))
    recorder.record(make_message(2))
    recorder.close()

    with csv_path.open(
        newline="",
        encoding="utf-8",
    ) as file:
        rows = list(csv.DictReader(file))

    assert len(rows) == 2
    assert list(rows[0].keys()) == CSV_FIELDS
    assert rows[0]["step"] == "1"
    assert rows[1]["step"] == "2"
    assert rows[0]["explored_fraction"] == "0.35"
    assert rows[0]["targets_found"] == "3"


def test_recorder_creates_parent_directories(tmp_path: Path):
    json_path = (
        tmp_path / "nested" / "metrics.jsonl"
    )

    recorder = TelemetryRecorder(json_path)
    recorder.open()
    recorder.record(make_message())
    recorder.close()

    assert json_path.exists()


def test_invalid_json_path_suffix_is_rejected(tmp_path: Path):
    with pytest.raises(ValueError):
        TelemetryRecorder(tmp_path / "metrics.json")


def test_invalid_csv_path_suffix_is_rejected(tmp_path: Path):
    with pytest.raises(ValueError):
        TelemetryRecorder(
            tmp_path / "metrics.jsonl",
            csv_path=tmp_path / "metrics.txt",
        )


def test_non_mapping_message_is_rejected(tmp_path: Path):
    json_path = tmp_path / "metrics.jsonl"

    recorder = TelemetryRecorder(json_path)
    recorder.open()

    with pytest.raises(TelemetryMessageError):
        recorder.record(["not", "a", "mapping"])

    recorder.close()


def test_wrong_message_type_is_rejected(tmp_path: Path):
    json_path = tmp_path / "metrics.jsonl"

    recorder = TelemetryRecorder(json_path)
    recorder.open()

    with pytest.raises(TelemetryMessageError):
        recorder.record(
            {
                "type": "other",
                "metrics": {
                    "step": 1,
                },
            }
        )

    recorder.close()


def test_missing_metrics_is_rejected(tmp_path: Path):
    json_path = tmp_path / "metrics.jsonl"

    recorder = TelemetryRecorder(json_path)
    recorder.open()

    with pytest.raises(TelemetryMessageError):
        recorder.record(
            {
                "type": "swarm_metrics",
            }
        )

    recorder.close()


def test_non_mapping_metrics_is_rejected(tmp_path: Path):
    json_path = tmp_path / "metrics.jsonl"

    recorder = TelemetryRecorder(json_path)
    recorder.open()

    with pytest.raises(TelemetryMessageError):
        recorder.record(
            {
                "type": "swarm_metrics",
                "metrics": ["not", "a", "mapping"],
            }
        )

    recorder.close()


def test_invalid_metrics_step_is_rejected(tmp_path: Path):
    json_path = tmp_path / "metrics.jsonl"

    recorder = TelemetryRecorder(json_path)
    recorder.open()

    for step in [None, "1", True]:
        with pytest.raises(TelemetryMessageError):
            recorder.record(
                {
                    "type": "swarm_metrics",
                    "metrics": {
                        "step": step,
                    },
                }
            )

    recorder.close()


def test_unopened_recorder_cannot_record(tmp_path: Path):
    json_path = tmp_path / "metrics.jsonl"

    recorder = TelemetryRecorder(json_path)

    with pytest.raises(RuntimeError):
        recorder.record(make_message())


def test_double_open_is_rejected(tmp_path: Path):
    json_path = tmp_path / "metrics.jsonl"

    recorder = TelemetryRecorder(json_path)
    recorder.open()

    with pytest.raises(RuntimeError):
        recorder.open()

    recorder.close()


def test_context_manager_opens_and_closes(tmp_path: Path):
    json_path = tmp_path / "metrics.jsonl"

    with TelemetryRecorder(json_path) as recorder:
        recorder.record(make_message())

    assert not recorder._json_file


def test_csv_header_is_written_once(tmp_path: Path):
    json_path = tmp_path / "metrics.jsonl"
    csv_path = tmp_path / "metrics.csv"

    recorder = TelemetryRecorder(
        json_path,
        csv_path=csv_path,
    )

    recorder.open()
    recorder.record(make_message(1))
    recorder.close()

    recorder2 = TelemetryRecorder(
        json_path,
        csv_path=csv_path,
    )

    recorder2.open()
    recorder2.record(make_message(2))
    recorder2.close()

    with csv_path.open(
        newline="",
        encoding="utf-8",
    ) as file:
        lines = file.readlines()

    header = lines[0].strip()
    expected_header = ",".join(CSV_FIELDS)

    assert header == expected_header

    with csv_path.open(
        newline="",
        encoding="utf-8",
    ) as file:
        rows = list(csv.DictReader(file))

    assert len(rows) == 2