import csv
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from sensors.consumer import TelemetryMessageError


CSV_FIELDS = [
    "step",
    "episode",
    "active_agents",
    "explored_fraction",
    "total_reward",
    "mean_reward",
    "newly_explored_cells",
    "drone_collisions",
    "obstacle_collisions",
    "targets_found",
    "boundary_violations",
    "visible_targets",
    "visible_obstacles",
    "visible_drones",
]


class TelemetryRecorder:
    """Record telemetry messages to JSON-lines and optional CSV."""

    def __init__(
        self,
        json_path: Path | str,
        csv_path: Path | str | None = None,
    ) -> None:
        json_path = Path(json_path)

        if json_path.suffix.lower() != ".jsonl":
            raise ValueError(
                "json_path must have a .jsonl suffix."
            )

        if csv_path is not None:
            csv_path = Path(csv_path)

            if csv_path.suffix.lower() != ".csv":
                raise ValueError(
                    "csv_path must have a .csv suffix."
                )

        self.json_path = json_path
        self.csv_path = csv_path
        self._json_file = None
        self._csv_file = None
        self._csv_writer = None

    def open(self) -> None:
        """Open output files and write CSV headers if applicable."""
        if self._json_file is not None:
            raise RuntimeError(
                "TelemetryRecorder is already open."
            )

        self.json_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._json_file = self.json_path.open(
            "a",
            encoding="utf-8",
            newline="",
        )

        if self.csv_path is not None:
            self.csv_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            self._csv_file = self.csv_path.open(
                "a",
                encoding="utf-8",
                newline="",
            )

            self._csv_writer = csv.DictWriter(
                self._csv_file,
                fieldnames=CSV_FIELDS,
            )

            if self.csv_path.stat().st_size == 0:
                self._csv_writer.writeheader()

    def close(self) -> None:
        """Flush and close output files."""
        if self._json_file is not None:
            self._json_file.flush()
            self._json_file.close()
            self._json_file = None

        if self._csv_file is not None:
            self._csv_file.flush()
            self._csv_file.close()
            self._csv_file = None
            self._csv_writer = None

    def record(self, message: Mapping[str, Any]) -> None:
        """Append a telemetry message to JSON and optional CSV."""
        if self._json_file is None:
            raise RuntimeError(
                "TelemetryRecorder must be opened before recording."
            )

        if not isinstance(message, Mapping):
            raise TelemetryMessageError(
                "Telemetry message must be a mapping."
            )

        if message.get("type") != "swarm_metrics":
            raise TelemetryMessageError(
                "Telemetry message type must be 'swarm_metrics'."
            )

        metrics = message.get("metrics")

        if not isinstance(metrics, Mapping):
            raise TelemetryMessageError(
                "Telemetry message metrics must be a mapping."
            )

        step = metrics.get("step")

        if isinstance(step, bool) or not isinstance(step, int):
            raise TelemetryMessageError(
                "Telemetry metrics step must be an integer."
            )

        json.dump(message, self._json_file, separators=(",", ":"))
        self._json_file.write("\n")
        self._json_file.flush()

        if self._csv_writer is not None:
            row = {
                "step": int(metrics["step"]),
                "episode": int(
                    metrics.get("episode", 0)
                ),
                "active_agents": int(
                    metrics.get("active_agents", 0)
                ),
                "explored_fraction": float(
                    metrics.get("explored_fraction", 0.0)
                ),
                "total_reward": float(
                    metrics.get("total_reward", 0.0)
                ),
                "mean_reward": float(
                    metrics.get("mean_reward", 0.0)
                ),
                "newly_explored_cells": int(
                    metrics.get("newly_explored_cells", 0)
                ),
                "drone_collisions": int(
                    metrics.get("drone_collisions", 0)
                ),
                "obstacle_collisions": int(
                    metrics.get("obstacle_collisions", 0)
                ),
                "targets_found": int(
                    metrics.get("targets_found", 0)
                ),
                "boundary_violations": int(
                    metrics.get("boundary_violations", 0)
                ),
                "visible_targets": int(
                    metrics.get("visible_targets", 0)
                ),
                "visible_obstacles": int(
                    metrics.get("visible_obstacles", 0)
                ),
                "visible_drones": int(
                    metrics.get("visible_drones", 0)
                ),
            }

            self._csv_writer.writerow(row)
            self._csv_file.flush()

    def __enter__(self):
        if self._json_file is not None:
            raise RuntimeError(
                "TelemetryRecorder is already open."
            )

        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()