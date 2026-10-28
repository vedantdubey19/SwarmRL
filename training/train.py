import argparse
import datetime
import os
import sys
import time
from typing import Any, Optional
import yaml
import numpy as np
import torch

# Ensure local storage paths inside workspace
workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)
local_ray_results = os.path.join(workspace_dir, "runs", "ray_results")
os.makedirs(local_ray_results, exist_ok=True)

os.environ["RAY_AIR_LOCAL_CACHE_DIR"] = local_ray_results
os.environ["TUNE_RESULT_DIR"] = local_ray_results
os.environ["RAY_AUTH_MODE"] = "disabled"

import ray.train.constants
import ray.tune.trainable.trainable
ray.train.constants.DEFAULT_STORAGE_PATH = local_ray_results
ray.tune.trainable.trainable.DEFAULT_STORAGE_PATH = local_ray_results

import datetime
import json
import ray
from ray.rllib.algorithms.ppo import PPOConfig
from ray.rllib.core.rl_module.rl_module import RLModuleSpec
from ray.rllib.core.rl_module.multi_rl_module import MultiRLModuleSpec
from ray.rllib.env.wrappers.pettingzoo_env import ParallelPettingZooEnv
from ray.tune.registry import register_env

from env import SwarmRLParallelEnv
from training.rl_module import SwarmCentralizedCriticRLModule
from training.callbacks import SwarmTrainingCallback, get_git_commit
from training.curriculum import CurriculumCallback


def _write_checkpoint_manifest(checkpoint_path: str, iteration: int, reward: float, is_best: bool = False) -> None:
    manifest = {
        "iteration": iteration,
        "reward": round(reward, 4),
        "git_commit": get_git_commit(),
        "timestamp": datetime.datetime.now().isoformat(),
        "is_best": is_best,
    }
    try:
        with open(os.path.join(checkpoint_path, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
    except Exception:
        pass


def build_algo_config(config_dict: dict):
    env_name = "swarmrl_pettingzoo_v0"
    num_agents = config_dict.get("num_agents", 50)
    max_steps = config_dict.get("max_steps", 500)
    dt = config_dict.get("dt", 0.1)

    register_env(
        env_name,
        lambda cfg: ParallelPettingZooEnv(
            SwarmRLParallelEnv(
                num_agents=num_agents,
                max_steps=max_steps,
                dt=dt,
                include_global_state=True,
            )
        ),
    )

    # Multi-agent RLModuleSpec with single shared policy
    module_spec = MultiRLModuleSpec(
        rl_module_specs={
            "shared_policy": RLModuleSpec(
                module_class=SwarmCentralizedCriticRLModule,
                model_config={"initial_log_std": config_dict.get("initial_log_std", -0.5)},
            )
        }
    )

    ppo_config = (
        PPOConfig()
        .api_stack(enable_rl_module_and_learner=True, enable_env_runner_and_connector_v2=True)
        .environment(env_name)
        .framework("torch")
        .training(
            lr=float(config_dict.get("lr", 3e-4)),
            gamma=float(config_dict.get("gamma", 0.99)),
            lambda_=float(config_dict.get("lambda", 0.95)),
            clip_param=float(config_dict.get("clip_param", 0.2)),
            entropy_coeff=float(config_dict.get("entropy_coeff", 0.01)),
            train_batch_size=int(config_dict.get("train_batch_size", 4000)),
            minibatch_size=int(config_dict.get("minibatch_size", 256)),
            num_epochs=int(config_dict.get("num_epochs", 10)),
        )
        .env_runners(
            num_env_runners=int(config_dict.get("num_env_runners", 2)),
            num_envs_per_env_runner=int(config_dict.get("num_envs_per_env_runner", 1)),
        )
        .multi_agent(
            policies={"shared_policy"},
            policy_mapping_fn=lambda aid, *args, **kwargs: "shared_policy",
        )
        .rl_module(rl_module_spec=module_spec)
        .callbacks(SwarmTrainingCallback)
    )

    return ppo_config


def train(iterations: int = 20, config_path: Optional[str] = None):
    cfg_file = config_path or os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(cfg_file, "r") as f:
        config_dict = yaml.safe_load(f)

    checkpoint_dir = os.path.abspath(config_dict.get("checkpoint_dir", "./checkpoints"))
    os.makedirs(checkpoint_dir, exist_ok=True)

    print(f"=== SwarmRL True MAPPO Training ({iterations} Iterations) ===")
    print(f"Num Runners:   {config_dict.get('num_env_runners', 2)}")
    print(f"Batch Size:    {config_dict.get('train_batch_size', 4000)}")
    print(f"Minibatch:     {config_dict.get('minibatch_size', 256)}")
    print(f"CheckpointDir: {checkpoint_dir}")

    ppo_config = build_algo_config(config_dict)
    algo = ppo_config.build_algo()

    start_time = time.time()
    best_reward = -float("inf")

    for iter_idx in range(1, iterations + 1):
        t0 = time.time()
        result = algo.train()
        t1 = time.time()

        env_runners = result.get("env_runners", {})
        ep_ret = env_runners.get("episode_return_mean", 0.0) or 0.0
        ep_len = env_runners.get("episode_len_mean", 0.0) or 0.0
        fps = result.get("num_env_steps_sampled_throughput_per_sec", 0.0) or 0.0

        print(
            f"Iter {iter_idx:03d}/{iterations:03d} | "
            f"Reward: {ep_ret:7.2f} | "
            f"EpLen: {ep_len:5.1f} | "
            f"Throughput: {fps:6.1f} steps/s | "
            f"Time: {t1 - t0:5.2f}s"
        )

        # Periodic checkpoint
        if iter_idx % 10 == 0 or iter_idx == iterations:
            ckpt_path = os.path.join(checkpoint_dir, f"checkpoint_{iter_idx:04d}")
            algo.save_to_path(ckpt_path)
            # Save raw actor weights for fast decentralized evaluation
            try:
                module = algo.get_module("shared_policy")
                if hasattr(module, "actor_net"):
                    torch.save(module.actor_net.state_dict(), os.path.join(ckpt_path, "actor_weights.pt"))
            except Exception:
                pass
            _write_checkpoint_manifest(ckpt_path, iter_idx, ep_ret, is_best=False)

        if ep_ret > best_reward:
            best_reward = ep_ret
            best_path = os.path.join(checkpoint_dir, "best_checkpoint")
            algo.save_to_path(best_path)
            try:
                module = algo.get_module("shared_policy")
                if hasattr(module, "actor_net"):
                    torch.save(module.actor_net.state_dict(), os.path.join(best_path, "actor_weights.pt"))
            except Exception:
                pass
            _write_checkpoint_manifest(best_path, iter_idx, ep_ret, is_best=True)

    total_time = time.time() - start_time
    print(f"\nTraining completed in {total_time:.2f}s! Best Reward: {best_reward:.2f}")

    algo.stop()
    return checkpoint_dir


def main():
    parser = argparse.ArgumentParser(description="SwarmRL MAPPO Training")
    parser.add_argument("--iterations", type=int, default=20, help="Number of training iterations")
    parser.add_argument("--config", type=str, default=None, help="Path to config.yaml")
    args = parser.parse_args()

    train(iterations=args.iterations, config_path=args.config)


if __name__ == "__main__":
    main()
