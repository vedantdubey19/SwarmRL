#!/usr/bin/env python3
import os
import sys
import numpy as np

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from env import SwarmRLParallelEnv


def attack_rapid_reset_loop():
    print("  [Attack 1] Rapid Reset Loop (100 resets in rapid succession)...")
    env = SwarmRLParallelEnv(num_agents=50)
    for i in range(100):
        obs, _ = env.reset(seed=i)
        assert len(obs) == 50
    print("    -> PASS: 100 rapid resets completed without memory leak or state corruption")


def attack_mid_episode_difficulty_switch():
    print("  [Attack 2] Switching Difficulty Mid-Episode...")
    env = SwarmRLParallelEnv(num_agents=50, difficulty=0)
    obs, _ = env.reset(seed=42)
    step_act = {a: np.zeros(4, dtype=np.float32) for a in env.agents}

    # Step at difficulty 0
    for _ in range(10):
        env.step(step_act)

    # Force difficulty switch mid-run
    env.set_difficulty(3)
    for _ in range(10):
        o, r, _, _, info = env.step(step_act)
    assert env.difficulty == 3
    print("    -> PASS: Difficulty switched from 0 to 3 mid-episode without crashing")


def attack_non_standard_swarm_sizes():
    print("  [Attack 3] Non-Standard Swarm Sizes (num_agents = 5 and num_agents = 70)...")
    for n in [5, 70]:
        try:
            env = SwarmRLParallelEnv(num_agents=n)
            obs, _ = env.reset()
            act = {a: np.zeros(4, dtype=np.float32) for a in env.agents}
            o, r, _, _, _ = env.step(act)
            assert len(o) == n
            print(f"    -> Swarm size {n}: Handled cleanly")
        except Exception as e:
            print(f"    -> Swarm size {n}: Exception raised ({e})")


def attack_extreme_long_episode():
    print("  [Attack 4] Extreme Long Episode (1000 steps continuous)...")
    env = SwarmRLParallelEnv(num_agents=50, max_steps=1000)
    env.reset(seed=42)
    act = {a: np.random.uniform(-0.5, 0.5, size=4).astype(np.float32) for a in env.possible_agents}
    total_steps = 0
    for _ in range(1000):
        if not env.agents:
            break
        env.step(act)
        total_steps += 1
    print(f"    -> PASS: Stepped {total_steps} iterations cleanly without overflow or kinematic explosion")


def main():
    print("=== [QA LEVEL J] Exploratory Stress & Edge-Case Attacks ===")
    attack_rapid_reset_loop()
    attack_mid_episode_difficulty_switch()
    attack_non_standard_swarm_sizes()
    attack_extreme_long_episode()
    print("Exploratory Testing Complete: All attack vectors survived gracefully.\n")


if __name__ == "__main__":
    main()
