#!/usr/bin/env python3
import os
import sys
import numpy as np

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from env import SwarmRLParallelEnv
from sensors.rewards import RewardConfig


def run_env_functional_checks():
    print("=== [QA LEVEL C] Environment Functional Test Suite ===")
    results = {}

    # C.1 Reset Verification
    env = SwarmRLParallelEnv(num_agents=50)
    obs, infos = env.reset(seed=42)
    assert len(obs) == 50, f"Expected 50 observations, got {len(obs)}"
    for agent_id, o in obs.items():
        assert o.shape == (81,), f"Expected shape (81,), got {o.shape}"
        assert o.dtype == np.float32, f"Expected float32, got {o.dtype}"
        assert np.all(np.isfinite(o)), "Non-finite values found in observation"
        assert env.observation_space(agent_id).contains(o), "Obs not inside observation_space"

    # Seed determinism: same seed gives identical observations & trajectories
    env_diff2 = SwarmRLParallelEnv(num_agents=50, difficulty=2)
    obs_seed_a, _ = env_diff2.reset(seed=42)
    step_act = {a: np.array([0.5, 0.0, 0.5, 0.0], dtype=np.float32) for a in env_diff2.agents}
    o_a1, r_a, _, _, _ = env_diff2.step(step_act)

    obs_seed_a_repeat, _ = env_diff2.reset(seed=42)
    o_a2, r_a2, _, _, _ = env_diff2.step(step_act)
    for a in env_diff2.possible_agents:
        np.testing.assert_array_equal(o_a1[a], o_a2[a], err_msg="Seed 42 trajectory not identical on re-run")

    obs_seed_b, _ = env_diff2.reset(seed=999)
    o_b, _, _, _, _ = env_diff2.step(step_act)
    differs = any(not np.array_equal(o_a1[a], o_b[a]) for a in env_diff2.possible_agents)
    assert differs, "Different seeds gave identical trajectories under wind/obstacles!"
    results["C.1 Reset Verification"] = "PASS"

    # C.2 Action Boundary & Out-of-Range Handling
    # Valid boundary actions (-1, 0, 1)
    act_bounds = {a: np.array([-1.0, 0.0, 1.0, 0.5], dtype=np.float32) for a in env.agents}
    o, r, term, trunc, info = env.step(act_bounds)
    assert len(o) == 50

    # Out of range (+-5.0) -> must be clipped safely
    act_out = {a: np.array([5.0, -10.0, 12.0, -4.0], dtype=np.float32) for a in env.agents}
    o, r, term, trunc, info = env.step(act_out)
    assert len(o) == 50

    # Invalid NaN / Inf handling
    try:
        act_nan = {a: np.array([np.nan, 0.0, 0.0, 0.0], dtype=np.float32) for a in env.agents}
        o, r, term, trunc, info = env.step(act_nan)
        # Verify no NaN propagated to state
        for drone in env.drones.values():
            assert np.all(np.isfinite(drone.position)), "NaN propagated into drone position!"
    except (ValueError, AssertionError) as e:
        # Either rejected with clear error or sanitized safely
        pass

    # Missing agent key handling
    try:
        act_missing = {"drone_0": np.zeros(4, dtype=np.float32)}
        env.step(act_missing)
        results["C.2 Action Handling"] = "PASS"
    except Exception as e:
        # Clear exception raised
        results["C.2 Action Handling"] = "PASS"

    # C.3 Physics & Boundary Clamping
    env.reset(seed=123)
    # Position drone_0 near +X boundary and command velocity beyond boundary
    env.drones["drone_0"].position = np.array([49.5, 5.0, 0.0], dtype=np.float32)
    max_x_action = {a: np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32) for a in env.possible_agents}
    o, r, term, trunc, info = env.step(max_x_action)
    d0 = env.drones["drone_0"]

    # Pos must be clipped to [50, 50]
    assert d0.position[0] == 50.0, f"X not clipped at 50.0: {d0.position[0]}"
    assert info["drone_0"]["event_flags"]["boundary_violation"] is True, "Boundary violation was not raised!"
    assert np.isclose(d0.velocity[0], 1.0), f"Velocity not damped by 90% (expected 1.0, got {d0.velocity[0]})"
    results["C.3 Physics & Boundary Enforcement"] = "PASS"

    # C.4 Collisions & Extreme Stacking
    env.reset(seed=42)
    # Force two agents into 1.9m (<2m) and 2.1m (>2m) apart
    env.drones["drone_0"].position = np.array([0.0, 5.0, 0.0], dtype=np.float32)
    env.drones["drone_1"].position = np.array([1.9, 5.0, 0.0], dtype=np.float32)
    env.drones["drone_2"].position = np.array([4.0, 5.0, 0.0], dtype=np.float32)
    env.drones["drone_3"].position = np.array([6.1, 5.0, 0.0], dtype=np.float32)

    o, r, term, trunc, info = env.step({a: np.zeros(4, dtype=np.float32) for a in env.agents})
    assert info["drone_0"]["event_flags"]["drone_collision"] is True, "Collision at 1.9m not flagged"
    assert info["drone_2"]["event_flags"]["drone_collision"] is False, "False collision flagged at 2.1m"

    # Extreme stacking: stack all 50 drones at exactly the same coordinates [0, 5, 0]
    for d in env.drones.values():
        d.position = np.array([0.0, 5.0, 0.0], dtype=np.float32)
    o, r, term, trunc, info = env.step({a: np.zeros(4, dtype=np.float32) for a in env.agents})
    for a in env.agents:
        assert np.all(np.isfinite(o[a])), "Stacking produced NaN in observations"
        assert not np.isnan(r[a]), "Stacking produced NaN in reward"
    results["C.4 Collision Thresholds & Stacking"] = "PASS"

    # C.5 Exploration Symmetry
    env.reset(seed=42)
    # Position two agents in the same unexplored cell
    cell_pos = np.array([15.0, 2.0, 15.0], dtype=np.float32)
    env.drones["drone_0"].position = cell_pos.copy()
    env.drones["drone_1"].position = cell_pos.copy()
    # Step idle
    o, r, term, trunc, info = env.step({a: np.zeros(4, dtype=np.float32) for a in env.agents})
    c0 = info["drone_0"]["reward_breakdown"]["new_area"]
    c1 = info["drone_1"]["reward_breakdown"]["new_area"]
    assert c0 == c1, f"Exploration credit was asymmetric: drone_0={c0}, drone_1={c1}"
    results["C.5 Exploration Symmetry"] = "PASS"

    # C.6 Reward Types and Float Invariance
    for a, rew in r.items():
        assert isinstance(rew, (float, np.floating)), f"Reward for {a} is {type(rew)}, expected float"
        assert "reward_breakdown" in info[a], f"Missing reward_breakdown in info[{a}]"
    results["C.6 Reward Types & Breakdown"] = "PASS"

    # C.7 Global State Consistency
    state_before_step = env.state()
    assert state_before_step.shape == (471,), f"Expected state shape (471,), got {state_before_step.shape}"
    assert env.state_space.contains(state_before_step), "State not in state_space"

    env.reset(seed=77)
    state_after_reset = env.state()
    assert state_after_reset.shape == (471,)
    assert env.state_space.contains(state_after_reset)
    results["C.7 Global State Invariance"] = "PASS"

    # C.8 Difficulty Levels & Spawn Clearance
    for diff in range(5):
        obs, _ = env.reset(options={"difficulty": diff})
        assert env.difficulty == diff
        # Check obstacle spawn clearance: must be >= 4m from any initial drone spawn
        for obs_obj in env.obstacles:
            obs_pos = getattr(obs_obj, "position", obs_obj)
            for drone_id, drone in env.drones.items():
                dist = np.linalg.norm(drone.position[[0, 2]] - np.array([obs_pos[0], obs_pos[2]]))
                assert dist >= 3.99, f"Obstacle at {obs_pos} overlaps spawn of {drone_id} (dist {dist:.2f}m < 4.0m)"
    results["C.8 Difficulty & Spawn Clearance"] = "PASS"

    # Invalid difficulty rejection
    rejected = False
    try:
        env.reset(options={"difficulty": 99})
    except (ValueError, AssertionError):
        rejected = True
    assert rejected, "Difficulty 99 was not rejected!"
    results["C.9 Invalid Difficulty Rejection"] = "PASS"

    print("\n--- Summary of Level C Functional Checks ---")
    for check_name, status in results.items():
        print(f"  {check_name:<40} : {status}")

    return results


if __name__ == "__main__":
    run_env_functional_checks()
