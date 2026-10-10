"""Ray RLlib MAPPO training configuration and environment adapter for SwarmRL."""

from typing import Any, Optional
import numpy as np

from env import SwarmRLParallelEnv, DEFAULT_NUM_AGENTS


def env_creator(env_config: Optional[dict[str, Any]] = None) -> SwarmRLParallelEnv:
    """Create a SwarmRLParallelEnv configured for Ray RLlib."""
    cfg = env_config or {}
    return SwarmRLParallelEnv(
        num_agents=cfg.get("num_agents", DEFAULT_NUM_AGENTS),
        max_steps=cfg.get("max_steps", 1000),
        dt=cfg.get("dt", 0.05),
        include_global_state=cfg.get("include_global_state", False),
    )


def extract_audit_metrics_from_infos(infos: dict[str, dict[str, Any]]) -> dict[str, float]:
    """Extract aggregated swarm reward-breakdown and event-flag diagnostics from step infos."""
    active_infos = [
        info["reward_breakdown"]
        for agent_id, info in infos.items()
        if agent_id != "__all__" and isinstance(info, dict) and "reward_breakdown" in info
    ]
    if not active_infos:
        return {
            "active_agents": 0.0,
            "team_cells": 0.0,
            "team_new_area_mean": 0.0,
            "team_target_found": 0.0,
            "min_neighbor_dist_mean": 0.0,
            "proximity_penalty_mean": 0.0,
            "drone_collisions": 0.0,
            "obstacle_collisions": 0.0,
        }

    min_dists = [
        float(rb["min_neighbor_dist"])
        for rb in active_infos
        if rb.get("min_neighbor_dist") is not None
    ]
    return {
        "active_agents": float(len(active_infos)),
        "team_cells": float(active_infos[0].get("team_cells", 0)),
        "team_new_area_mean": float(np.mean([rb.get("team_new_area", 0.0) for rb in active_infos])),
        "team_target_found": float(
            any(rb.get("team_target_found_flag", False) or rb.get("team_target_found", 0.0) > 0 for rb in active_infos)
        ),
        "min_neighbor_dist_mean": float(np.mean(min_dists)) if min_dists else 0.0,
        "proximity_penalty_mean": float(np.mean([rb.get("proximity_penalty", 0.0) for rb in active_infos])),
        "drone_collisions": float(sum(rb.get("drone_collision", 0.0) < 0 for rb in active_infos)),
        "obstacle_collisions": float(sum(rb.get("obstacle_collision", 0.0) < 0 for rb in active_infos)),
    }


def _register_centralized_critic_model() -> Optional[str]:
    """Register a CTDE TorchModelV2 where actor reads 81-dim obs and critic reads 471-dim state."""
    try:
        import torch
        import torch.nn as nn
        from ray.rllib.models import ModelCatalog
        from ray.rllib.models.torch.torch_modelv2 import TorchModelV2
    except ImportError:
        return None

    model_name = "swarmrl_ctde_mappo_model"

    class SwarmCentralizedCriticModel(TorchModelV2, nn.Module):
        def __init__(self, obs_space, action_space, num_outputs, model_config, name):
            TorchModelV2.__init__(self, obs_space, action_space, num_outputs, model_config, name)
            nn.Module.__init__(self)
            orig_space = getattr(obs_space, "original_space", obs_space)
            local_dim = orig_space["obs"].shape[0] if hasattr(orig_space, "spaces") else 81
            state_dim = orig_space["state"].shape[0] if hasattr(orig_space, "spaces") else 471

            self.actor_net = nn.Sequential(
                nn.Linear(local_dim, 256),
                nn.Tanh(),
                nn.Linear(256, 256),
                nn.Tanh(),
                nn.Linear(256, num_outputs),
            )
            self.critic_net = nn.Sequential(
                nn.Linear(state_dim, 256),
                nn.Tanh(),
                nn.Linear(256, 256),
                nn.Tanh(),
                nn.Linear(256, 1),
            )
            self._cur_value = None

        def forward(self, input_dict, state, seq_lens):
            obs = input_dict["obs"]
            if isinstance(obs, dict):
                local_obs = obs["obs"]
                global_state = obs["state"]
            else:
                local_obs = obs[:, :81]
                global_state = obs[:, 81:]
            logits = self.actor_net(local_obs)
            self._cur_value = self.critic_net(global_state).squeeze(-1)
            return logits, state

        def value_function(self):
            return self._cur_value

    ModelCatalog.register_custom_model(model_name, SwarmCentralizedCriticModel)
    return model_name


def build_training_config(include_global_state: bool = True):
    """Build Ray RLlib PPOConfig wired to SwarmRLParallelEnv with shared multi-agent CTDE policy."""
    from ray.rllib.algorithms.ppo import PPOConfig
    from ray.tune.registry import register_env

    env_name = "swarmrl_v0"
    sample_env = env_creator({"include_global_state": include_global_state})

    try:
        from ray.rllib.env.wrappers.pettingzoo_env import ParallelPettingZooEnv
        register_env(env_name, lambda cfg: ParallelPettingZooEnv(env_creator(cfg)))
    except ImportError:
        register_env(env_name, env_creator)

    first_agent = sample_env.possible_agents[0]
    obs_space = sample_env.observation_space(first_agent)
    act_space = sample_env.action_space(first_agent)

    policy_Spec_config: dict[str, Any] = {}
    if include_global_state:
        custom_model = _register_centralized_critic_model()
        if custom_model is not None:
            policy_Spec_config["model"] = {"custom_model": custom_model}

    config = (
        PPOConfig()
        .environment(
            env=env_name,
            env_config={"num_agents": DEFAULT_NUM_AGENTS, "include_global_state": include_global_state},
        )
        .framework("torch")
        .debugging(log_level="INFO")
        .checkpointing()
        .env_runners(
            num_env_runners=2,
            num_envs_per_env_runner=1,
            rollout_fragment_length=100,
        )
        .training(
            lr=3e-4,
            gamma=0.99,
            lambda_=0.95,
            clip_param=0.2,
            train_batch_size=4000,
            minibatch_size=256,
            num_epochs=10,
            entropy_coeff=0.01,
        )
        .multi_agent(
            policies={
                "shared_policy": (None, obs_space, act_space, policy_Spec_config),
            },
            policy_mapping_fn=lambda agent_id, *args, **kwargs: "shared_policy",
        )
    )

    return config


if __name__ == "__main__":
    config = build_training_config()
    print("Ray RLlib training infrastructure configured successfully.")
    print(config)
