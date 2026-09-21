import json
from datetime import datetime, timezone
from typing import Any

import numpy as np

from sensors.observation import SensorObservation


def _json_value(value: Any) -> Any:
    """Convert common NumPy values into JSON-compatible values."""
    if isinstance(value, np.ndarray):
        return value.tolist()

    if isinstance(value, np.integer):
        return int(value)

    if isinstance(value, np.floating):
        return float(value)

    if isinstance(value, np.bool_):
        return bool(value)

    if isinstance(value, dict):
        return {
            str(key): _json_value(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]

    return value


def validate_event_flags(
    event_flags: dict[str, bool],
) -> dict[str, bool]:
    """Validate and normalize event flags."""
    required_flags = {
        "drone_collision",
        "obstacle_collision",
        "target_found",
        "boundary_violation",
    }

    missing_flags = required_flags - set(event_flags)

    if missing_flags:
        missing_text = ", ".join(sorted(missing_flags))
        raise ValueError(
            f"Missing event flags: {missing_text}"
        )

    return {
        flag: bool(event_flags[flag])
        for flag in sorted(required_flags)
    }


def build_sensor_payload(
    observation: SensorObservation,
    reward: float = 0.0,
    reward_components: dict[str, Any] | None = None,
    event_flags: dict[str, bool] | None = None,
    step: int = 0,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Build one JSON-compatible drone sensor payload."""
    if step < 0:
        raise ValueError("Step must not be negative.")

    if timestamp is None:
        timestamp = datetime.now(
            timezone.utc
        ).isoformat()

    payload = observation.to_dict()

    payload["version"] = 1
    payload["step"] = int(step)
    payload["timestamp"] = str(timestamp)
    payload["reward"] = float(reward)
    payload["reward_components"] = _json_value(
        reward_components or {}
    )

    if event_flags is None:
        event_flags = {
            "drone_collision": False,
            "obstacle_collision": False,
            "target_found": False,
            "boundary_violation": False,
        }

    payload["event_flags"] = validate_event_flags(
        event_flags
    )

    return _json_value(payload)


def build_swarm_payload(
    observations: dict[str, SensorObservation],
    rewards: dict[str, float] | None = None,
    reward_components: dict[str, dict[str, Any]]
    | None = None,
    event_flags: dict[str, dict[str, bool]]
    | None = None,
    step: int = 0,
    timestamp: str | None = None,
    explored_fraction: float = 0.0,
    explored_grid: list[list[int]] | np.ndarray | None = None,
) -> dict[str, Any]:
    """Build one JSON-compatible payload for the full swarm."""
    if step < 0:
        raise ValueError("Step must not be negative.")

    if not 0.0 <= explored_fraction <= 1.0:
        raise ValueError(
            "Explored fraction must be between 0 and 1."
        )

    rewards = rewards or {}
    reward_components = reward_components or {}
    event_flags = event_flags or {}

    if timestamp is None:
        timestamp = datetime.now(
            timezone.utc
        ).isoformat()

    agents = []

    for agent_id, observation in observations.items():
        agents.append(
            build_sensor_payload(
                observation=observation,
                reward=rewards.get(agent_id, 0.0),
                reward_components=reward_components.get(
                    agent_id,
                    {},
                ),
                event_flags=event_flags.get(
                    agent_id,
                    {
                        "drone_collision": False,
                        "obstacle_collision": False,
                        "target_found": False,
                        "boundary_violation": False,
                    },
                ),
                step=step,
                timestamp=timestamp,
            )
        )

    payload = {
        "version": 1,
        "step": int(step),
        "timestamp": str(timestamp),
        "agents": agents,
        "map": {
            "explored_fraction": float(
                explored_fraction
            ),
            "grid": _json_value(
                explored_grid
                if explored_grid is not None
                else []
            ),
        },
    }

    return _json_value(payload)


def ensure_json_serializable(payload: dict[str, Any]) -> str:
    """Validate a payload by encoding it as JSON."""
    return json.dumps(payload)