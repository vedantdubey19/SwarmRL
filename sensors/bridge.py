"""sensors/bridge.py
Bridge module connecting SwarmRLParallelEnv physical simulation state to
the WebSocket wire protocol and 3D rendering viewport.

Conforms to schema.js (SCHEMA_VERSION = 1) and docs/websocket_streaming_protocol.md.
"""

from __future__ import annotations

import json
import time
from typing import Any, Optional

import numpy as np

from env import SwarmRLParallelEnv, DroneState, ArenaObject


SCHEMA_VERSION = 1


def heading_to_rotation_quat(heading: float) -> list[float]:
    """Convert env yaw heading (radians) to Three.js compatible quaternion [qx, qy, qz, qw].

    In the environment, right-handed Y-up coordinate frame is used where heading 0
    points along +X and increases counter-clockwise in the horizontal X-Z plane.
    In Three.js, rotation around Y is related by:
        rotation_y = -heading + pi / 2
    The corresponding pure Y-axis rotation quaternion is:
        qx = 0.0
        qy = sin(rotation_y / 2)
        qz = 0.0
        qw = cos(rotation_y / 2)
    """
    yaw = -float(heading) + (np.pi / 2.0)
    half_yaw = yaw * 0.5
    qy = float(np.sin(half_yaw))
    qw = float(np.cos(half_yaw))
    return [0.0, round(qy, 6), 0.0, round(qw, 6)]


def _parse_drone_index(agent_id: str) -> int:
    """Extract integer id from agent string (e.g. 'drone_7' -> 7)."""
    if agent_id.startswith("drone_"):
        try:
            return int(agent_id.split("_", 1)[1])
        except ValueError:
            pass
    return 0


def build_telemetry_drone_state(
    agent_id: str,
    drone: DroneState,
    event_flags: Optional[dict[str, bool]] = None,
    detections: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Construct an individual drone telemetry state dictionary conforming to schema.js."""
    drone_idx = _parse_drone_index(agent_id)

    status = "active"
    if event_flags:
        if event_flags.get("drone_collision", False):
            status = "collided_drone"
        elif event_flags.get("obstacle_collision", False):
            status = "collided_obstacle"
        elif event_flags.get("boundary_violation", False):
            status = "out_of_bounds"
        elif not drone.alive:
            status = "collided_drone"
    elif not drone.alive:
        status = "collided_drone"

    pos = [round(float(coord), 3) for coord in drone.position]
    vel = [round(float(v), 3) for v in drone.velocity]
    heading = round(float(drone.heading), 4)
    rot = heading_to_rotation_quat(drone.heading)

    formatted_detections: list[dict[str, Any]] = []
    if detections:
        for det in detections:
            formatted_detections.append({
                "id": str(det.get("id", "")),
                "type": str(det.get("type", "target")),
                "dist": round(float(det.get("dist", det.get("distance", 0.0))), 3),
                "angle": round(float(det.get("angle", 0.0)), 4),
            })

    return {
        "id": drone_idx,
        "agent_id": agent_id,
        "pos": pos,
        "vel": vel,
        "heading": heading,
        "rot": rot,
        "status": status,
        "detections": formatted_detections,
    }


def build_telemetry_target_state(target: ArenaObject, target_idx: int) -> dict[str, Any]:
    """Construct a target entry dictionary conforming to schema.js."""
    return {
        "id": target_idx,
        "pos": [round(float(c), 3) for c in target.position],
        "found": bool(target.found),
    }


def build_telemetry_frame_from_env(
    env: SwarmRLParallelEnv,
    infos: Optional[dict[str, Any]] = None,
    step_reward_sum: float = 0.0,
    timestamp: Optional[float] = None,
) -> dict[str, Any]:
    """Construct an atomic multi-agent telemetry frame packet from SwarmRLParallelEnv.

    Parameters:
        env: Instantiated and initialized SwarmRLParallelEnv.
        infos: Optional infos dictionary returned from env.step().
        step_reward_sum: Sum of rewards obtained across all agents in the current step.
        timestamp: Optional epoch timestamp in milliseconds (defaults to current time).

    Returns:
        JSON-serializable telemetry frame dictionary complying with schema.js.
    """
    ts_ms = timestamp if timestamp is not None else round(time.time() * 1000.0, 3)
    sim_time = round(float(env.step_count * env.dt), 3)

    drones_payload: list[dict[str, Any]] = []
    for agent_id in env.possible_agents:
        if agent_id in env.drones:
            drone = env.drones[agent_id]
            agent_info = infos.get(agent_id, {}) if infos else {}
            event_flags = agent_info.get("event_flags")
            detections = agent_info.get("sensor_detections")
            drones_payload.append(
                build_telemetry_drone_state(
                    agent_id,
                    drone,
                    event_flags=event_flags,
                    detections=detections,
                )
            )

    targets_payload: list[dict[str, Any]] = []
    for idx, target in enumerate(env.targets):
        targets_payload.append(build_telemetry_target_state(target, idx))

    explored_frac = round(float(env.exploration_map.explored_fraction), 4)
    active_count = sum(1 for d in drones_payload if d["status"] == "active")
    found_count = sum(1 for t in targets_payload if t["found"])

    return {
        "version": SCHEMA_VERSION,
        "type": "frame",
        "step": int(env.step_count),
        "timestamp": ts_ms,
        "sim_time": sim_time,
        "metrics": {
            "explored_fraction": explored_frac,
            "active_drones": active_count,
            "targets_found": found_count,
            "total_targets": len(targets_payload),
            "step_reward_sum": round(float(step_reward_sum), 3),
        },
        "drones": drones_payload,
        "targets": targets_payload,
    }


def create_registration_message(role: str = "publisher") -> dict[str, str]:
    """Create a client registration handshake message."""
    if role not in ("publisher", "subscriber"):
        raise ValueError(f"Invalid role '{role}'. Must be 'publisher' or 'subscriber'.")
    return {
        "type": "register",
        "role": role,
    }


def format_telemetry_json(frame: dict[str, Any]) -> str:
    """Format frame dictionary into a compact JSON string."""
    return json.dumps(frame, separators=(",", ":"))
