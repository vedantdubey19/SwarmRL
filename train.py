import csv
import os
from datetime import datetime

import ray

from rllib_config import build_training_config


def find_entropy_values(data):
    values = []

    if isinstance(data, dict):
        for key, value in data.items():
            if key in ("entropy", "policy_entropy"):
                if isinstance(value, (int, float)):
                    values.append(float(value))
            else:
                values.extend(find_entropy_values(value))

    elif isinstance(data, list):
        for item in data:
            values.extend(find_entropy_values(item))

    return values


def main():
    ray.init()

    algo = None

    try:
        config = build_training_config()
        algo = config.build_algo()

        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        checkpoint_dir = os.path.abspath(
            os.path.join("training", "checkpoints", run_id)
        )
        metrics_dir = os.path.abspath(
            os.path.join("training", "metrics")
        )

        os.makedirs(checkpoint_dir, exist_ok=True)
        os.makedirs(metrics_dir, exist_ok=True)

        metrics_file = os.path.join(
            metrics_dir,
            f"training_metrics_{run_id}.csv",
        )

        fieldnames = [
            "iteration",
            "episode_return_mean",
            "episode_len_mean",
            "num_episodes",
            "num_env_steps_sampled",
            "policy_entropy",
            "collision_count",
            "team_cells",
            "team_target_found",
        ]

        print("PPO training run starting...")
        print(f"Checkpoint directory: {checkpoint_dir}")
        print(f"Metrics file: {metrics_file}")

        with open(
            metrics_file,
            "w",
            newline="",
            encoding="utf-8",
        ) as csv_file:
            writer = csv.DictWriter(
                csv_file,
                fieldnames=fieldnames,
            )
            writer.writeheader()
            csv_file.flush()

            for iteration in range(1, 101):
                result = algo.train()

                env_metrics = result.get("env_runners", {})
                entropy_values = find_entropy_values(result)

                policy_entropy = (
                    sum(entropy_values) / len(entropy_values)
                    if entropy_values
                    else None
                )

                metrics = {
                    "iteration": iteration,
                    "episode_return_mean": env_metrics.get(
                        "episode_return_mean"
                    ),
                    "episode_len_mean": env_metrics.get(
                        "episode_len_mean"
                    ),
                    "num_episodes": env_metrics.get(
                        "num_episodes"
                    ),
                    "num_env_steps_sampled": env_metrics.get(
                        "num_env_steps_sampled"
                    ),
                    "policy_entropy": policy_entropy,
                    "collision_count": env_metrics.get(
                        "collision_count"
                    ),
                    "team_cells": env_metrics.get("team_cells"),
                    "team_target_found": env_metrics.get(
                        "team_target_found"
                    ),
                }

                writer.writerow(metrics)
                csv_file.flush()

                print(f"\nTRAINING ITERATION: {iteration}")
                for name, value in metrics.items():
                    print(f"{name}: {value}")

                if iteration % 10 == 0:
                    checkpoint_path = algo.save(checkpoint_dir)
                    print(f"CHECKPOINT SAVED: {checkpoint_path}")

        print("\nTraining completed.")
        print(f"Training metrics saved to: {metrics_file}")

    finally:
        if algo is not None:
            algo.stop()

        ray.shutdown()


if __name__ == "__main__":
    main()
