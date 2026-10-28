import datetime
import json
import os
import subprocess
from typing import Any, Optional

from ray.rllib.callbacks.callbacks import RLlibCallback


def get_git_commit() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
        return out.decode().strip()
    except Exception:
        return "unknown"


class SwarmTrainingCallback(RLlibCallback):
    """Logs iteration metrics to JSON and manages checkpoints with manifest.json."""

    def __init__(self, checkpoint_dir: str = "./checkpoints", log_dir: str = "./runs"):
        super().__init__()
        self.checkpoint_dir = os.path.abspath(checkpoint_dir)
        self.log_dir = os.path.abspath(log_dir)
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        os.makedirs(self.log_dir, exist_ok=True)

        self.summary_file = os.path.join(self.log_dir, "training_summary.jsonl")
        self.best_reward = -float("inf")
        self.best_checkpoint_path = None

    def on_train_result(self, *, algorithm, result: dict, **kwargs) -> None:
        iteration = int(result.get("training_iteration", 0))

        env_runners_info = result.get("env_runners", {})
        ep_return_mean = float(env_runners_info.get("episode_return_mean", 0.0) or 0.0)
        ep_len_mean = float(env_runners_info.get("episode_len_mean", 0.0) or 0.0)
        env_steps_s = float(result.get("num_env_steps_sampled_throughput_per_sec", 0.0) or 0.0)

        # Learner metrics
        learner_info = result.get("learners", {}).get("shared_policy", {})
        policy_loss = float(learner_info.get("policy_loss", 0.0) or 0.0)
        vf_loss = float(learner_info.get("vf_loss", 0.0) or 0.0)
        entropy = float(learner_info.get("entropy", 0.0) or 0.0)

        # Swarm SAR custom metrics
        custom_metrics = env_runners_info.get("custom_metrics", {})
        collisions_per_1000 = float(custom_metrics.get("collisions_per_1000_mean", 0.0) or 0.0)
        explored_frac = float(custom_metrics.get("explored_fraction_mean", 0.0) or 0.0)
        team_cells = float(custom_metrics.get("team_cells_mean", 0.0) or 0.0)
        team_target_found_rate = float(custom_metrics.get("team_target_found_rate_mean", 0.0) or 0.0)
        active_agents = float(custom_metrics.get("active_agents_mean", 50.0) or 50.0)

        iter_summary = {
            "iteration": iteration,
            "timestamp": datetime.datetime.now().isoformat(),
            "episode_reward": round(ep_return_mean, 3),
            "episode_len": round(ep_len_mean, 2),
            "env_steps_per_sec": round(env_steps_s, 1),
            "policy_loss": round(policy_loss, 5),
            "value_loss": round(vf_loss, 5),
            "entropy": round(entropy, 4),
            "collisions_per_1000": round(collisions_per_1000, 2),
            "explored_fraction": round(explored_frac, 4),
            "team_cells": round(team_cells, 1),
            "team_target_found_rate": round(team_target_found_rate, 4),
            "active_agents": round(active_agents, 1),
        }

        # Write JSON line
        with open(self.summary_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(iter_summary) + "\n")

        # Save checkpoint every 10 iterations
        if iteration % 10 == 0:
            ckpt_path = os.path.join(self.checkpoint_dir, f"checkpoint_{iteration:04d}")
            algorithm.save_to_path(ckpt_path)
            self._write_manifest(ckpt_path, iteration, ep_return_mean, entropy, collisions_per_1000)

        # Save best checkpoint
        if ep_return_mean > self.best_reward and iteration >= 5:
            self.best_reward = ep_return_mean
            best_path = os.path.join(self.checkpoint_dir, "best_checkpoint")
            algorithm.save_to_path(best_path)
            self.best_checkpoint_path = best_path
            self._write_manifest(best_path, iteration, ep_return_mean, entropy, collisions_per_1000, is_best=True)

    def _write_manifest(
        self,
        checkpoint_path: str,
        iteration: int,
        reward: float,
        entropy: float,
        collisions: float,
        is_best: bool = False,
    ) -> None:
        manifest = {
            "iteration": iteration,
            "reward": round(reward, 4),
            "entropy": round(entropy, 4),
            "collisions": round(collisions, 2),
            "git_commit": get_git_commit(),
            "timestamp": datetime.datetime.now().isoformat(),
            "is_best": is_best,
        }
        manifest_file = os.path.join(checkpoint_path, "manifest.json")
        try:
            with open(manifest_file, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)
        except Exception:
            pass
