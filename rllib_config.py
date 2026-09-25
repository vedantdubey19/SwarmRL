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
        world_size=cfg.get("world_size", (100.0, 100.0)),
        include_global_state=cfg.get("include_global_state", False),
    )


def build_training_config(include_global_state: bool = False):
    """Build Ray RLlib PPOConfig wired to SwarmRLParallelEnv with shared multi-agent policy."""
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

    config = (
        PPOConfig()
        .environment(
            env=env_name,
            env_config={"num_agents": DEFAULT_NUM_AGENTS, "include_global_state": include_global_state},
        )
        .framework("torch")
        .debugging(log_level="INFO")
        .checkpointing()
        .env_runners(num_env_runners=2)
        .multi_agent(
            policies={
                "shared_policy": (None, obs_space, act_space, {}),
            },
            policy_mapping_fn=lambda agent_id, *args, **kwargs: "shared_policy",
        )
    )

    return config


if __name__ == "__main__":
    config = build_training_config()
    print("Ray RLlib training infrastructure configured successfully.")
    print(config)
