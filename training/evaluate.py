import argparse
import os
import sys
import time
from typing import Any, Optional

workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

import numpy as np
import torch
import torch.nn as nn

from env import SwarmRLParallelEnv
from sensors.bridge import build_world_message, build_frame_message, build_grid_snapshot_message
from sensors.ws_publisher import SwarmPublisher


class DecentralizedActor(nn.Module):
    """Pure PyTorch decentralized actor consuming 81-dim local observation."""

    def __init__(self):
        super().__init__()
        self.actor_net = nn.Sequential(
            nn.Linear(81, 256),
            nn.Tanh(),
            nn.Linear(256, 256),
            nn.Tanh(),
            nn.Linear(256, 4),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.actor_net(x)

    def act(self, obs: np.ndarray) -> np.ndarray:
        t = torch.as_tensor(obs, dtype=torch.float32)
        single = (t.ndim == 1)
        if single:
            t = t.unsqueeze(0)
        with torch.no_grad():
            action = self.actor_net(t)
        if single:
            return action.squeeze(0).cpu().numpy()
        return action.cpu().numpy()


def load_actor_from_checkpoint(checkpoint_path: str, allow_untrained: bool = False) -> DecentralizedActor:
    """Load decentralized actor weights from RLlib checkpoint directory."""
    if not os.path.exists(checkpoint_path):
        if allow_untrained:
            actor = DecentralizedActor()
            actor.eval()
            return actor
        raise FileNotFoundError(f"Checkpoint path does not exist: {checkpoint_path}")

    actor = DecentralizedActor()
    actor.eval()

    # Check for direct PyTorch state dict file
    direct_pt = os.path.join(checkpoint_path, "actor_weights.pt")
    if os.path.exists(direct_pt):
        sd = torch.load(direct_pt, map_location="cpu")
        if any(k.startswith("actor_net.") for k in sd.keys()):
            actor.load_state_dict(sd)
        elif any(k.startswith("0.") for k in sd.keys()):
            actor.actor_net.load_state_dict(sd)
        else:
            actor.load_state_dict(sd, strict=False)
        return actor

    # Search inside RLlib checkpoint directory
    found_weights = False
    for root, _, files in os.walk(checkpoint_path):
        for f in files:
            if f.endswith(".pt") or f.endswith(".bin") or f == "module_state":
                full_p = os.path.join(root, f)
                try:
                    state_dict = torch.load(full_p, map_location="cpu", weights_only=False)
                    if isinstance(state_dict, dict):
                        # Filter actor weights
                        actor_weights = {}
                        for k, v in state_dict.items():
                            if "actor_net" in k:
                                clean_k = k.split("actor_net.")[-1]
                                actor_weights[f"actor_net.{clean_k}"] = v
                        if actor_weights:
                            actor.load_state_dict(actor_weights, strict=False)
                            found_weights = True
                            break
                except Exception:
                    pass
        if found_weights:
            break

    if not found_weights:
        if allow_untrained:
            return actor
        raise FileNotFoundError(f"No valid actor weights found in checkpoint directory: {checkpoint_path}")

    return actor


def run_evaluation(
    actor: Optional[DecentralizedActor] = None,
    checkpoint_path: Optional[str] = None,
    allow_untrained: bool = False,
    num_episodes: int = 10,
    difficulty: int = 0,
    max_steps: int = 500,
    publish: bool = False,
    ws_url: Optional[str] = None,
    seed: int = 42,
    use_random: bool = False,
) -> dict[str, Any]:
    """Run evaluation episodes using strictly 81-dim local observations."""
    if not use_random and actor is None:
        if checkpoint_path is not None:
            actor = load_actor_from_checkpoint(checkpoint_path, allow_untrained=allow_untrained)
        else:
            if not allow_untrained:
                raise FileNotFoundError("No checkpoint path provided. Use --checkpoint <path> or --allow-untrained.")
            actor = DecentralizedActor()
            actor.eval()

    env = SwarmRLParallelEnv(
        num_agents=50,
        max_steps=max_steps,
        difficulty=difficulty,
        include_global_state=False,
    )

    publisher = None
    if publish:
        publisher = SwarmPublisher(ws_url=ws_url, target_hz=30.0)
        publisher.start()
        time.sleep(0.5)

    all_rewards = []
    all_lengths = []
    all_explored = []
    all_collisions = []
    all_targets_found = []
    all_speeds = []

    for ep in range(num_episodes):
        obs, infos = env.reset(seed=seed + ep)

        if publisher:
            publisher.publish(build_world_message(env))
            publisher.publish(build_grid_snapshot_message(env))

        ep_reward = 0.0
        step = 0
        ep_speeds = []

        while step < max_steps and env.agents:
            step += 1

            # Decentralized inference using only 81-dim observation
            if use_random:
                actions = {
                    agent_id: np.random.uniform(-1.0, 1.0, size=4).astype(np.float32)
                    for agent_id in obs.keys()
                }
            elif actor is not None:
                agent_ids = list(obs.keys())
                obs_batch = np.stack([obs[aid][:81] for aid in agent_ids])
                acts = actor.act(obs_batch)
                actions = {aid: np.clip(acts[idx], -1.0, 1.0) for idx, aid in enumerate(agent_ids)}
            else:
                actions = {agent_id: np.zeros(4, dtype=np.float32) for agent_id in obs.keys()}

            obs, rewards, terminations, truncations, infos = env.step(actions)
            step_rew = sum(rewards.values())
            ep_reward += step_rew

            # Record agent speed
            alive_mask = env.alive > 0.5
            if np.any(alive_mask):
                speeds = np.linalg.norm(env.velocities[alive_mask], axis=-1)
                ep_speeds.append(float(np.mean(speeds)))
            else:
                ep_speeds.append(0.0)

            if publisher:
                frame_msg = build_frame_message(env, infos=infos, step_reward_sum=step_rew)
                publisher.publish(frame_msg)
                time.sleep(1.0 / 30.0)

        all_rewards.append(ep_reward)
        all_lengths.append(step)
        all_explored.append(float(env.exploration_map.explored_fraction))
        cols_total = env.collision_totals["total"]
        cols_per_1000 = (cols_total / max(1, step * 50)) * 1000.0
        all_collisions.append(cols_per_1000)
        all_targets_found.append(env.targets_found_count)
        all_speeds.append(float(np.mean(ep_speeds)) if ep_speeds else 0.0)

    if publisher:
        publisher.stop()

    summary = {
        "num_episodes": num_episodes,
        "difficulty": difficulty,
        "mean_reward": float(np.mean(all_rewards)),
        "std_reward": float(np.std(all_rewards)),
        "mean_length": float(np.mean(all_lengths)),
        "mean_explored_fraction": float(np.mean(all_explored)),
        "mean_collisions_per_1000": float(np.mean(all_collisions)),
        "mean_targets_found": float(np.mean(all_targets_found)),
        "mean_agent_speed": float(np.mean(all_speeds)),
        "std_agent_speed": float(np.std(all_speeds)),
    }
    return summary


def main():
    parser = argparse.ArgumentParser(description="Evaluate SwarmRL Policy")
    parser.add_argument("--checkpoint", type=str, default=None, help="Path to checkpoint directory")
    parser.add_argument("--allow-untrained", action="store_true", help="Allow fallback to untrained initialized policy")
    parser.add_argument("--episodes", type=int, default=10, help="Number of evaluation episodes")
    parser.add_argument("--difficulty", type=int, default=0, help="Difficulty level 0-4")
    parser.add_argument("--publish", action="store_true", help="Stream evaluation live over WebSocket")
    parser.add_argument("--ws-url", type=str, default=None, help="WebSocket relay URL")
    parser.add_argument("--benchmark", action="store_true", help="Compare checkpoint vs random baseline")
    parser.add_argument("--random", action="store_true", help="Run random action baseline")
    args = parser.parse_args()

    if args.benchmark:
        print(f"=== SwarmRL Benchmark: Trained Policy vs Random Baseline ({args.episodes} episodes) ===")
        print("Evaluating Random Baseline...")
        rand_res = run_evaluation(
            use_random=True,
            num_episodes=args.episodes,
            difficulty=args.difficulty,
        )
        print("Evaluating Trained Policy...")
        policy_res = run_evaluation(
            checkpoint_path=args.checkpoint,
            allow_untrained=args.allow_untrained,
            num_episodes=args.episodes,
            difficulty=args.difficulty,
        )

        print("\n" + "=" * 65)
        print(f"{'Metric':<28} | {'Random Baseline':<16} | {'Trained Policy':<16}")
        print("-" * 65)
        print(f"{'Mean Return':<28} | {rand_res['mean_reward']:<16.2f} | {policy_res['mean_reward']:<16.2f}")
        print(f"{'Mean Episode Length':<28} | {rand_res['mean_length']:<16.1f} | {policy_res['mean_length']:<16.1f}")
        print(f"{'Collisions / 1000 Steps':<28} | {rand_res['mean_collisions_per_1000']:<16.2f} | {policy_res['mean_collisions_per_1000']:<16.2f}")
        print(f"{'Mean Explored Fraction':<28} | {rand_res['mean_explored_fraction']*100:<15.1f}% | {policy_res['mean_explored_fraction']*100:<15.1f}%")
        print(f"{'Mean Targets Found':<28} | {rand_res['mean_targets_found']:<16.2f} | {policy_res['mean_targets_found']:<16.2f}")
        print(f"{'Mean Agent Speed (m/s)':<28} | {rand_res['mean_agent_speed']:<16.2f} | {policy_res['mean_agent_speed']:<16.2f}")
        print("=" * 65)

        exp_beat = policy_res['mean_explored_fraction'] >= rand_res['mean_explored_fraction']
        col_beat = policy_res['mean_collisions_per_1000'] <= rand_res['mean_collisions_per_1000']
        print(f"Policy beats random on explored fraction: {exp_beat}")
        print(f"Policy beats random on collisions:        {col_beat}")
        return

    print(f"=== SwarmRL Policy Evaluation (Difficulty {args.difficulty}) ===")
    summary = run_evaluation(
        checkpoint_path=args.checkpoint,
        allow_untrained=args.allow_untrained,
        num_episodes=args.episodes,
        difficulty=args.difficulty,
        publish=args.publish,
        ws_url=args.ws_url,
        use_random=args.random,
    )
    print(f"Mean Reward:             {summary['mean_reward']:.2f} +/- {summary['std_reward']:.2f}")
    print(f"Mean Explored Fraction:  {summary['mean_explored_fraction'] * 100.0:.2f}%")
    print(f"Collisions / 1000 Steps: {summary['mean_collisions_per_1000']:.2f}")
    print(f"Mean Targets Found:      {summary['mean_targets_found']:.2f}")
    print(f"Mean Agent Speed:        {summary['mean_agent_speed']:.2f} m/s")


if __name__ == "__main__":
    main()
