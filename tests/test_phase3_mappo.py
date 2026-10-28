import os
import shutil
import tempfile
import numpy as np
import pytest
import torch
import gymnasium as gym

from ray.rllib.core.rl_module.rl_module import RLModuleSpec
from ray.rllib.core.columns import Columns
from training.rl_module import SwarmCentralizedCriticRLModule
from training.curriculum import CurriculumManager
from training.evaluate import DecentralizedActor, run_evaluation


def test_actor_invariance_to_global_state():
    obs_space = gym.spaces.Dict({
        "obs": gym.spaces.Box(-1, 1, shape=(81,)),
        "state": gym.spaces.Box(-1, 1, shape=(471,)),
    })
    act_space = gym.spaces.Box(-1, 1, shape=(4,))
    spec = RLModuleSpec(module_class=SwarmCentralizedCriticRLModule, observation_space=obs_space, action_space=act_space)
    module = spec.build()

    local_obs = torch.randn(4, 81)
    state1 = torch.randn(4, 471)
    state2 = torch.randn(4, 471) + 10.0  # drastically different global states

    batch1 = {Columns.OBS: {"obs": local_obs, "state": state1}}
    batch2 = {Columns.OBS: {"obs": local_obs, "state": state2}}

    out1 = module.forward_inference(batch1)
    out2 = module.forward_inference(batch2)

    # Actor output must be strictly identical regardless of global state
    torch.testing.assert_close(
        out1[Columns.ACTION_DIST_INPUTS],
        out2[Columns.ACTION_DIST_INPUTS],
        rtol=1e-6,
        atol=1e-6,
    )


def test_critic_sensitivity_to_global_state():
    obs_space = gym.spaces.Dict({
        "obs": gym.spaces.Box(-1, 1, shape=(81,)),
        "state": gym.spaces.Box(-1, 1, shape=(471,)),
    })
    act_space = gym.spaces.Box(-1, 1, shape=(4,))
    spec = RLModuleSpec(module_class=SwarmCentralizedCriticRLModule, observation_space=obs_space, action_space=act_space)
    module = spec.build()

    local_obs = torch.randn(4, 81)
    state1 = torch.randn(4, 471)
    state2 = torch.randn(4, 471) + 5.0

    batch1 = {Columns.OBS: {"obs": local_obs, "state": state1}}
    batch2 = {Columns.OBS: {"obs": local_obs, "state": state2}}

    val1 = module.compute_values(batch1)
    val2 = module.compute_values(batch2)

    # Critic values MUST change when global state changes
    assert not torch.allclose(val1, val2, atol=1e-3)


def test_curriculum_manager_promotion_and_no_skip():
    cm = CurriculumManager(initial_difficulty=0, k_consecutive=3, reward_threshold=50.0, max_difficulty=4)

    # Reward below threshold -> no promotion
    assert cm.check_and_update(mean_reward=30.0) is False
    assert cm.current_difficulty == 0
    assert cm.consecutive_successes == 0

    # 1 success
    assert cm.check_and_update(mean_reward=60.0) is False
    assert cm.current_difficulty == 0
    assert cm.consecutive_successes == 1

    # Interrupted by failure
    assert cm.check_and_update(mean_reward=40.0) is False
    assert cm.current_difficulty == 0
    assert cm.consecutive_successes == 0

    # 3 consecutive successes -> promote to level 1 (never skip to 2)
    assert cm.check_and_update(mean_reward=70.0) is False
    assert cm.check_and_update(mean_reward=80.0) is False
    assert cm.check_and_update(mean_reward=90.0) is True  # Promoted!
    assert cm.current_difficulty == 1
    assert cm.consecutive_successes == 0


def test_checkpoint_save_load_and_inference_observations_only():
    tmp_dir = tempfile.mkdtemp()
    try:
        actor = DecentralizedActor()
        # Save actor weights directly
        save_path = os.path.join(tmp_dir, "actor_weights.pt")
        torch.save(actor.state_dict(), save_path)

        # Evaluate using only local observations
        summary = run_evaluation(
            checkpoint_path=tmp_dir,
            num_episodes=1,
            max_steps=10,
            difficulty=0,
            publish=False,
        )

        assert summary["num_episodes"] == 1
        assert summary["mean_length"] == 10
        assert 0.0 <= summary["mean_explored_fraction"] <= 1.0
    finally:
        shutil.rmtree(tmp_dir)


def test_one_full_training_iteration_50_agents_2_runners():
    from training.train import build_algo_config

    cfg = {
        "num_agents": 50,
        "max_steps": 100,
        "dt": 0.1,
        "lr": 3e-4,
        "gamma": 0.99,
        "lambda": 0.95,
        "clip_param": 0.2,
        "entropy_coeff": 0.01,
        "train_batch_size": 1000,
        "minibatch_size": 256,
        "num_epochs": 1,
        "num_env_runners": 2,
        "num_envs_per_env_runner": 1,
    }

    ppo_cfg = build_algo_config(cfg)
    algo = ppo_cfg.build_algo()

    try:
        # Check runner count
        assert algo.env_runner_group.num_remote_env_runners() == 2

        # Test runner propagation and confirmation
        cm = CurriculumManager()
        propagated = cm.propagate_to_runners(algo, target_difficulty=2)
        assert propagated is True

        # Run 1 full training iteration
        res = algo.train()
        sampled = res.get("num_env_steps_sampled_lifetime", 0)
        assert sampled >= 1000, f"Expected at least 1000 sampled steps, got {sampled}"
    finally:
        algo.stop()

