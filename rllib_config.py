from ray.rllib.algorithms.ppo import PPOConfig


def build_training_config():
    config = (
        PPOConfig()
        .framework("torch")
        .env_runners(num_env_runners=0)
    )

    return config


if __name__ == "__main__":
    config = build_training_config()
    print("Ray RLlib training infrastructure configured successfully.")
    print(config)