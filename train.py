import os
from datetime import datetime

import ray

from rllib_config import build_training_config


def main():
    ray.init()

    config = build_training_config()
    algo = config.build_algo()

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    checkpoint_dir = os.path.abspath(
    os.path.join(
        "training",
        "checkpoints",
        run_id,
    )
)

    os.makedirs(checkpoint_dir, exist_ok=True)

    print("PPO training run started successfully.")
    print(f"Checkpoint directory: {checkpoint_dir}")

    for iteration in range(1, 101):
        result = algo.train()

        env = result.get("env_runners", {})

        print(f"TRAINING ITERATION: {iteration}")
        print(
            "EPISODE RETURN MEAN:",
            env.get("episode_return_mean"),
        )
        print(
            "EPISODE LENGTH MEAN:",
            env.get("episode_len_mean"),
        )
        print(
            "EPISODES:",
            env.get("num_episodes"),
        )
        print(
            "ENV STEPS:",
            env.get("num_env_steps_sampled"),
        )

        if iteration % 10 == 0:
            checkpoint_path = algo.save(checkpoint_dir)
            print(f"CHECKPOINT SAVED: {checkpoint_path}")

    algo.stop()
    ray.shutdown()


if __name__ == "__main__":
    main()