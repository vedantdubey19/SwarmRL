"""tests/test_bridge.py
Unit tests for sensors/bridge.py Python-to-WebSocket telemetry bridge.
"""

import json
import subprocess
import numpy as np
import pytest

from env import SwarmRLParallelEnv
from sensors.bridge import (
    SCHEMA_VERSION,
    build_telemetry_drone_state,
    build_telemetry_frame_from_env,
    build_telemetry_target_state,
    create_registration_message,
    format_telemetry_json,
    heading_to_rotation_quat,
)


def test_heading_to_rotation_quat():
    # At heading 0 (East / +X), Three.js yaw rotation is +pi/2
    q0 = heading_to_rotation_quat(0.0)
    assert q0[0] == 0.0
    assert q0[2] == 0.0
    assert pytest.approx(q0[1], abs=1e-3) == np.sin(np.pi / 4.0)
    assert pytest.approx(q0[3], abs=1e-3) == np.cos(np.pi / 4.0)
    # Unit quaternion magnitude
    assert pytest.approx(q0[1] ** 2 + q0[3] ** 2, abs=1e-5) == 1.0

    # At heading pi/2 (South / +Z), Three.js yaw rotation is 0
    q_south = heading_to_rotation_quat(np.pi / 2.0)
    assert pytest.approx(q_south[1], abs=1e-4) == 0.0
    assert pytest.approx(q_south[3], abs=1e-4) == 1.0


def test_drone_state_status_mapping():
    env = SwarmRLParallelEnv(num_agents=5)
    env.reset(seed=42)

    drone = env.drones["drone_0"]

    # Active
    d_active = build_telemetry_drone_state("drone_0", drone)
    assert d_active["id"] == 0
    assert d_active["agent_id"] == "drone_0"
    assert d_active["status"] == "active"
    assert len(d_active["pos"]) == 3
    assert len(d_active["vel"]) == 3
    assert len(d_active["rot"]) == 4

    # Collided drone
    d_drone_col = build_telemetry_drone_state(
        "drone_0", drone, event_flags={"drone_collision": True}
    )
    assert d_drone_col["status"] == "collided_drone"

    # Collided obstacle
    d_obs_col = build_telemetry_drone_state(
        "drone_0", drone, event_flags={"obstacle_collision": True}
    )
    assert d_obs_col["status"] == "collided_obstacle"

    # Boundary violation
    d_bounds = build_telemetry_drone_state(
        "drone_0", drone, event_flags={"boundary_violation": True}
    )
    assert d_bounds["status"] == "out_of_bounds"

    # Dead drone
    drone.alive = False
    d_dead = build_telemetry_drone_state("drone_0", drone)
    assert d_dead["status"] == "collided_drone"


def test_telemetry_frame_structure_and_metrics():
    env = SwarmRLParallelEnv(num_agents=50)
    env.reset(seed=123)

    frame = build_telemetry_frame_from_env(env)

    assert frame["version"] == SCHEMA_VERSION
    assert frame["type"] == "frame"
    assert frame["step"] == 0
    assert frame["sim_time"] == 0.0
    assert isinstance(frame["timestamp"], (int, float))

    metrics = frame["metrics"]
    assert metrics["active_drones"] == 50
    assert metrics["total_targets"] == len(env.targets)
    assert metrics["targets_found"] == 0
    assert 0.0 <= metrics["explored_fraction"] <= 1.0

    assert len(frame["drones"]) == 50
    assert len(frame["targets"]) == len(env.targets)


def test_telemetry_frame_after_step():
    env = SwarmRLParallelEnv(num_agents=5)
    env.reset(seed=1)

    actions = {a: np.array([0.5, 0.0, -0.5, 0.1], dtype=np.float32) for a in env.agents}
    obs, rewards, terminations, truncations, infos = env.step(actions)

    reward_sum = sum(rewards.values())
    frame = build_telemetry_frame_from_env(
        env, infos=infos, step_reward_sum=reward_sum
    )

    assert frame["step"] == 1
    assert pytest.approx(frame["sim_time"]) == 0.05
    assert frame["metrics"]["step_reward_sum"] == pytest.approx(reward_sum, abs=1e-3)
    assert len(frame["drones"]) == 5


def test_registration_message():
    pub = create_registration_message("publisher")
    assert pub == {"type": "register", "role": "publisher"}

    sub = create_registration_message("subscriber")
    assert sub == {"type": "register", "role": "subscriber"}

    with pytest.raises(ValueError, match="Invalid role"):
        create_registration_message("spectator")


def test_telemetry_frame_validation_against_node_schema():
    env = SwarmRLParallelEnv(num_agents=50)
    env.reset(seed=42)

    actions = {a: np.zeros(4, dtype=np.float32) for a in env.agents}
    obs, rewards, terminations, truncations, infos = env.step(actions)

    frame = build_telemetry_frame_from_env(
        env, infos=infos, step_reward_sum=sum(rewards.values())
    )
    raw_json = format_telemetry_json(frame)

    # Validate against schema.js isValidTelemetryFrame using node subprocess
    node_script = f"""
    const {{ isValidTelemetryFrame }} = require('./schema');
    const frame = {raw_json};
    const valid = isValidTelemetryFrame(frame);
    if (!valid) {{
        console.error('Frame failed isValidTelemetryFrame validation');
        process.exit(1);
    }}
    process.exit(0);
    """
    res = subprocess.run(
        ["node", "-e", node_script],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"Schema validation error: {res.stderr}"
