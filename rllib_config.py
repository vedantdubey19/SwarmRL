from ray.rllib.algorithms.ppo import PPOConfig


def build_training_config():
    config = (
        PPOConfig()
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
