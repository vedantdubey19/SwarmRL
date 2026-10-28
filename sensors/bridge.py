from __future__ import annotations
import base64
import json
import time
from typing import Any, Optional, TYPE_CHECKING
import numpy as np

if TYPE_CHECKING:
    from env import SwarmRLParallelEnv

SCHEMA_VERSION = 1


def heading_to_rotation_quat(heading: float) -> list[float]:
    """Convert env yaw heading (radians) to Three.js compatible quaternion [qx, qy, qz, qw].
    In env: heading 0 rad points along +X, +Y up, rotation around Y is:
        rotation_y = -heading + pi / 2
    """
    yaw = -float(heading) + (np.pi / 2.0)
    half_yaw = yaw * 0.5
    qy = float(np.sin(half_yaw))
    qw = float(np.cos(half_yaw))
    return [0.0, round(qy, 6), 0.0, round(qw, 6)]


def _parse_drone_index(agent_id: str) -> int:
    if agent_id.startswith("drone_"):
        try:
            return int(agent_id.split("_", 1)[1])
        except ValueError:
            pass
    return 0


def build_world_message(env: Any) -> dict[str, Any]:
    from env import WORLD_X_MIN, WORLD_X_MAX, WORLD_Y_MIN, WORLD_Y_MAX, WORLD_Z_MIN, WORLD_Z_MAX

    obstacles_payload = []
    for obs in env.obstacles:
        pos = [round(float(c), 3) for c in (obs.position if hasattr(obs, "position") else obs["position"])]
        rad = round(float(obs.radius if hasattr(obs, "radius") else obs["radius"]), 3)
        h = round(float(obs.height if hasattr(obs, "height") else obs.get("height", 20.0)), 3)
        obs_id = obs.id if hasattr(obs, "id") else obs["id"]
        obstacles_payload.append({
            "id": str(obs_id),
            "type": "obstacle",
            "position": pos,
            "radius": rad,
            "height": h,
        })

    targets_payload = []
    for t in env.targets:
        pos = [round(float(c), 3) for c in (t.position if hasattr(t, "position") else t["position"])]
        t_id = t.id if hasattr(t, "id") else t["id"]
        found = bool(t.found if hasattr(t, "found") else t["found"])
        targets_payload.append({
            "id": str(t_id),
            "type": "target",
            "position": pos,
            "radius": 1.0,
            "found": found,
        })

    return {
        "type": "world",
        "bounds": {
            "x_min": float(WORLD_X_MIN),
            "x_max": float(WORLD_X_MAX),
            "y_min": float(WORLD_Y_MIN),
            "y_max": float(WORLD_Y_MAX),
            "z_min": float(WORLD_Z_MIN),
            "z_max": float(WORLD_Z_MAX),
        },
        "obstacles": obstacles_payload,
        "targets": targets_payload,
    }


def build_telemetry_drone_state(
    agent_id: str,
    drone: Any,
    event_flags: Optional[dict[str, bool]] = None,
    detections: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
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
    quat = heading_to_rotation_quat(drone.heading)

    formatted_detections: list[dict[str, Any]] = []
    if detections:
        for det in detections[:8]:
            formatted_detections.append({
                "id": str(det.get("id", "")),
                "type": str(det.get("type", "target")),
                "distance": round(float(det.get("dist", det.get("distance", 0.0))), 3),
                "bearing_x": round(float(det.get("bearing_x", 0.0)), 4),
                "bearing_y": round(float(det.get("bearing_y", 0.0)), 4),
                "angle": round(float(det.get("angle", 0.0)), 4),
            })

    return {
        "id": drone_idx,
        "agent_id": agent_id,
        "position": pos,
        "pos": pos,
        "velocity": vel,
        "vel": vel,
        "quaternion": quat,
        "rot": quat,
        "heading": heading,
        "status": status,
        "detections": formatted_detections,
    }


def build_telemetry_target_state(target: Any, target_idx: int) -> dict[str, Any]:
    pos = [round(float(c), 3) for c in (target.position if hasattr(target, "position") else target["position"])]
    found = bool(target.found if hasattr(target, "found") else target["found"])
    return {
        "id": target_idx,
        "pos": pos,
        "found": found,
    }


def build_frame_message(
    env: Any,
    infos: Optional[dict[str, Any]] = None,
    step_reward_sum: float = 0.0,
    timestamp: Optional[float] = None,
) -> dict[str, Any]:
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

    active_count = sum(1 for d in drones_payload if d["status"] == "active")
    explored_frac = round(float(env.exploration_map.explored_fraction), 4)

    return {
        "version": SCHEMA_VERSION,
        "type": "frame",
        "step": int(env.step_count),
        "timestamp": ts_ms,
        "sim_time": sim_time,
        "drones": drones_payload,
        "metrics": {
            "explored_fraction": explored_frac,
            "collision_totals": {
                "drone": int(env.collision_totals.get("drone", 0)),
                "obstacle": int(env.collision_totals.get("obstacle", 0)),
                "boundary": int(env.collision_totals.get("boundary", 0)),
                "total": int(env.collision_totals.get("total", 0)),
            },
            "targets_found": int(env.targets_found_count),
            "total_targets": len(env.targets),
            "active_agents": active_count,
            "active_drones": active_count,
            "difficulty": int(getattr(env, "difficulty", 0)),
            "step_reward_sum": round(float(step_reward_sum), 3),
        },
    }


def build_telemetry_frame_from_env(
    env: Any,
    infos: Optional[dict[str, Any]] = None,
    step_reward_sum: float = 0.0,
    timestamp: Optional[float] = None,
) -> dict[str, Any]:
    """Alias for backwards compatibility with tests."""
    msg = build_frame_message(env, infos=infos, step_reward_sum=step_reward_sum, timestamp=timestamp)
    targets_payload = []
    for idx, target in enumerate(env.targets):
        targets_payload.append(build_telemetry_target_state(target, idx))
    msg["targets"] = targets_payload
    return msg


def build_grid_snapshot_message(env: Any) -> dict[str, Any]:
    grid = env.exploration_map.grid  # (50, 50) bool
    packed = np.packbits(grid.flatten()).tobytes()
    b64 = base64.b64encode(packed).decode("ascii")
    return {
        "type": "grid_snapshot",
        "step": int(env.step_count),
        "width": int(env.exploration_map.width),
        "height": int(env.exploration_map.height),
        "bitmask": b64,
    }


def build_grid_delta_message(step: int, newly_explored_indices: list[int]) -> dict[str, Any]:
    return {
        "type": "grid_delta",
        "step": int(step),
        "new_cells": [int(idx) for idx in newly_explored_indices],
    }


def create_registration_message(role: str = "publisher") -> dict[str, str]:
    if role not in ("publisher", "subscriber"):
        raise ValueError(f"Invalid role '{role}'. Must be 'publisher' or 'subscriber'.")
    return {
        "type": "register",
        "role": role,
    }


def format_telemetry_json(frame: dict[str, Any]) -> str:
    return json.dumps(frame, separators=(",", ":"))
