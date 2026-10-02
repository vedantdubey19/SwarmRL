import os
from datetime import datetime

import ray

from rllib_config import build_training_config

NUM_ITERATIONS = 100
CHECKPOINT_EVERY = 10


def main():
    ray.init()

    # The centralized-critic model in rllib_config is a ModelV2 custom model, which
    # RLlib's new API stack ignores, so the Dict obs mode can't build yet. Train on
    # local 81-dim obs with the shared policy until that model is ported to an RLModule.
    config = build_training_config(include_global_state=False)
    algo = config.build_algo()

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    checkpoint_dir = os.path.abspath(os.path.join("training", "checkpoints", run_id))
    os.makedirs(checkpoint_dir, exist_ok=True)
    print(f"Checkpoint directory: {checkpoint_dir}")

    for iteration in range(1, NUM_ITERATIONS + 1):
        result = algo.train()
        runners = result.get("env_runners", {})

        print(
            f"iter {iteration:3d} | "
            f"return_mean={runners.get('episode_return_mean')} | "
            f"len_mean={runners.get('episode_len_mean')} | "
            f"episodes={runners.get('num_episodes')} | "
            f"env_steps={runners.get('num_env_steps_sampled')}"
        )

        if iteration % CHECKPOINT_EVERY == 0:
            path = algo.save(checkpoint_dir)
            print(f"Checkpoint saved: {path}")

    algo.stop()
    ray.shutdown()


if __name__ == "__main__":
    main()
