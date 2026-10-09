from ray.rllib.algorithms.ppo import PPOConfig
from ray.rllib.callbacks.callbacks import RLlibCallback
from ray.rllib.env.wrappers.pettingzoo_env import ParallelPettingZooEnv
from ray.tune.registry import register_env

from environment.drone_env import SwarmSearchRescueEnv


class SwarmMetricsCallback(RLlibCallback):
    def on_episode_end(
        self,
        *,
        episode,
        metrics_logger,
        **kwargs,
    ):
        try:
            infos = episode.get_infos(return_list=True)
        except (AttributeError, TypeError):
            return

        latest_info = None

        for step_infos in reversed(infos):
            if not isinstance(step_infos, dict):
                continue

            for info in step_infos.values():
                if isinstance(info, dict) and all(
                    key in info
                    for key in (
                        "collision_count",
                        "team_cells",
                        "team_target_found",
                    )
                ):
                    latest_info = info
                    break

            if latest_info is not None:
                break

        if latest_info is None or metrics_logger is None:
            return

        for metric in (
            "collision_count",
            "team_cells",
            "team_target_found",
        ):
            metrics_logger.log_value(
                metric,
                latest_info[metric],
                reduce="mean",
            )


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
            env_config={"num_agents": 50},
        )
        .framework("torch")
        .debugging(log_level="INFO")
        .checkpointing()
        .callbacks(SwarmMetricsCallback)
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
            policy_mapping_fn=lambda agent_id, *args, **kwargs: (
                f"policy_{agent_id.split('_')[1]}"
            ),
        )
    )

    return config


if __name__ == "__main__":
    config = build_training_config()

    print("Ray RLlib training infrastructure configured successfully.")
    print(config)