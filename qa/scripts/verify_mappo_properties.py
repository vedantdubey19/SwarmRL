#!/usr/bin/env python3
import os
import sys
import tempfile
import torch
import numpy as np

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from training.rl_module import SwarmCentralizedCriticRLModule
from training.curriculum import CurriculumManager
from training.evaluate import load_actor_from_checkpoint, run_evaluation


def test_mappo_decoupling():
    print("--- E.1 MAPPO Actor-Critic Decoupling Verification ---")
    module = SwarmCentralizedCriticRLModule(observation_space=None, action_space=None, model_config={})
    module.eval()

    obs_fixed = torch.randn(5, 81)
    state_a = torch.randn(5, 471)
    state_b = torch.randn(5, 471) * 5.0 + 2.0  # Completely different global state

    batch_a = {"obs": {"obs": obs_fixed, "state": state_a}}
    batch_b = {"obs": {"obs": obs_fixed, "state": state_b}}

    # Actor policy output must depend ONLY on local 81-dim obs
    out_a = module._forward_inference(batch_a)
    out_b = module._forward_inference(batch_b)
    action_diff = torch.max(torch.abs(out_a["action_dist_inputs"] - out_b["action_dist_inputs"])).item()
    assert action_diff == 0.0, f"Actor policy leaked global state! Action diff: {action_diff}"
    print("  Actor output invariance to global state: PASS (action diff = 0.0)")

    # Centralized critic value MUST change when global state changes
    val_a = module.compute_values(batch_a)
    val_b = module.compute_values(batch_b)
    val_diff = torch.max(torch.abs(val_a - val_b)).item()
    assert val_diff > 1e-3, "Centralized critic failed to respond to global state change"
    print(f"  Critic response to global state change: PASS (value diff = {val_diff:.4f})")


def test_checkpoint_resilience():
    print("\n--- E.2 Checkpoint Loading & Corruption Resilience ---")
    ckpt_best = os.path.join(REPO_ROOT, "checkpoints", "best_checkpoint")
    assert os.path.exists(ckpt_best), "best_checkpoint directory does not exist!"

    # 1. Load best checkpoint and evaluate with ONLY 81-dim observations
    summary = run_evaluation(checkpoint_path=ckpt_best, num_episodes=2, max_steps=50)
    assert summary["num_episodes"] == 2
    assert summary["mean_reward"] > 0.0, "Trained policy failed to score positive reward"
    print(f"  Best checkpoint clean inference: PASS (Mean reward: {summary['mean_reward']:.2f})")

    # 2. Missing checkpoint raises clear error or falls back with notice
    missing_dir = os.path.join(REPO_ROOT, "checkpoints", "non_existent_ckpt_123")
    actor_missing = load_actor_from_checkpoint(missing_dir)
    # Actor returns fresh initialized model
    assert actor_missing is not None
    print("  Missing checkpoint handled safely: PASS")

    # 3. Corrupted checkpoint file raises clear error
    tmp = tempfile.mkdtemp()
    corrupt_pt = os.path.join(tmp, "actor_weights.pt")
    with open(corrupt_pt, "wb") as f:
        f.write(b"NOT_A_VALID_PYTORCH_STATE_DICT_GARBAGE_BYTES")

    corrupted_handled = False
    try:
        load_actor_from_checkpoint(tmp)
    except Exception as e:
        corrupted_handled = True
        print(f"  Corrupted checkpoint raised clear error: PASS ({type(e).__name__})")
    assert corrupted_handled, "Corrupted checkpoint did not raise exception!"


def test_curriculum_rules():
    print("\n--- E.3 Curriculum Promotion Integrity ---")
    cm = CurriculumManager(initial_difficulty=0, k_consecutive=3, reward_threshold=50.0, max_difficulty=4)

    # 2 successes (not enough for promotion)
    cm.check_and_update(60.0)
    cm.check_and_update(70.0)
    assert cm.current_difficulty == 0
    assert cm.consecutive_successes == 2

    # Drop below threshold resets consecutive counter
    cm.check_and_update(40.0)
    assert cm.current_difficulty == 0
    assert cm.consecutive_successes == 0

    # 3 consecutive successes promotes exactly 1 level (never skips)
    cm.check_and_update(80.0)
    cm.check_and_update(85.0)
    promoted = cm.check_and_update(90.0)
    assert promoted is True
    assert cm.current_difficulty == 1, f"Expected difficulty 1, got {cm.current_difficulty}"
    assert cm.consecutive_successes == 0
    print("  Curriculum K=3 promotion & no-skip logic: PASS")


if __name__ == "__main__":
    test_mappo_decoupling()
    test_checkpoint_resilience()
    test_curriculum_rules()
    print("\nLevel E Validation: PASS")
