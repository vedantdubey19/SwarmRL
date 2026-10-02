from ray.rllib.algorithms.ppo import PPOConfig
from ray.rllib.env.wrappers.pettingzoo_env import ParallelPettingZooEnv
from ray.tune.registry import register_env

from environment.drone_env import SwarmSearchRescueEnv


def env_creator(env_config):
    return ParallelPettingZooEnv(
        SwarmSearchRescueEnv(env_config)
    )


register_env("swarm_search_rescue", env_creator)


def build_training_config():
    config = (
        PPOConfig()
        .environment(
            env="swarm_search_rescue",
            env_config={
                "num_agents": 50,
            },
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
            policies={f"policy_{i}" for i in range(50)},
            policy_mapping_fn=lambda agent_id, *args, **kwargs: f"policy_{agent_id.split('_')[1]}",
        )
    )

    return config


if __name__ == "__main__":
    config = build_training_config()
    print("Ray RLlib training infrastructure configured successfully.")
    print(config)
