import logging
from typing import Any, Optional

from ray.rllib.callbacks.callbacks import RLlibCallback

logger = logging.getLogger(__name__)


class CurriculumManager:
    """Manages adaptive difficulty progression (levels 0-4) with remote env confirmation."""

    def __init__(
        self,
        initial_difficulty: int = 0,
        k_consecutive: int = 3,
        reward_threshold: float = 30.0,
        max_difficulty: int = 4,
    ):
        self.current_difficulty = initial_difficulty
        self.k_consecutive = k_consecutive
        self.reward_threshold = reward_threshold
        self.max_difficulty = max_difficulty
        self.consecutive_successes = 0

    def check_and_update(self, mean_reward: float, algorithm: Optional[Any] = None) -> bool:
        """Evaluate performance and promote difficulty if threshold held for K iterations.

        Never skips a level. Confirms change reached remote env runners.
        """
        if mean_reward >= self.reward_threshold:
            self.consecutive_successes += 1
        else:
            self.consecutive_successes = 0

        if (
            self.consecutive_successes >= self.k_consecutive
            and self.current_difficulty < self.max_difficulty
        ):
            new_level = self.current_difficulty + 1
            self.current_difficulty = new_level
            self.consecutive_successes = 0

            # Propagate to env runners if algorithm provided
            if algorithm is not None and hasattr(algorithm, "env_runner_group"):
                self.propagate_to_runners(algorithm, new_level)

            logger.info(
                f"[CurriculumManager] Promoted to difficulty {self.current_difficulty} "
                f"(Threshold: {self.reward_threshold}, held {self.k_consecutive} iters)"
            )
            return True

        return False

    def propagate_to_runners(self, algorithm: Any, target_difficulty: int) -> bool:
        """Broadcast difficulty update to all remote env runners and confirm receipt."""
        def _set_difficulty(runner):
            res = []
            if hasattr(runner, "env") and hasattr(runner.env, "envs"):
                for sub_env in runner.env.envs:
                    raw = getattr(sub_env, "par_env", getattr(sub_env, "unwrapped", sub_env))
                    if hasattr(raw, "set_difficulty"):
                        raw.set_difficulty(target_difficulty)
                    res.append(getattr(raw, "difficulty", target_difficulty))
            elif hasattr(runner, "foreach_env"):
                def _set(e):
                    raw = getattr(e, "par_env", getattr(e, "unwrapped", e))
                    if hasattr(raw, "set_difficulty"):
                        raw.set_difficulty(target_difficulty)
                    return getattr(raw, "difficulty", target_difficulty)
                res = runner.foreach_env(_set)
            return res

        confirmed_diffs = algorithm.env_runner_group.foreach_env_runner(_set_difficulty)
        for runner_results in confirmed_diffs:
            for env_diff in runner_results:
                if env_diff != target_difficulty:
                    raise RuntimeError(
                        f"Difficulty update failed to propagate! Expected {target_difficulty}, got {env_diff}"
                    )
        return True


class CurriculumCallback(RLlibCallback):
    """RLlib callback wrapping CurriculumManager."""

    def __init__(
        self,
        initial_difficulty: int = 0,
        k_consecutive: int = 3,
        reward_threshold: float = 30.0,
        max_difficulty: int = 4,
    ):
        super().__init__()
        self.manager = CurriculumManager(
            initial_difficulty=initial_difficulty,
            k_consecutive=k_consecutive,
            reward_threshold=reward_threshold,
            max_difficulty=max_difficulty,
        )

    def on_train_result(self, *, algorithm, result: dict, **kwargs) -> None:
        mean_reward = float(result.get("env_runners", {}).get("episode_return_mean", 0.0) or 0.0)
        promoted = self.manager.check_and_update(mean_reward, algorithm=algorithm)
        result["curriculum_difficulty"] = self.manager.current_difficulty
        result["curriculum_consecutive_successes"] = self.manager.consecutive_successes
        if promoted:
            print(f"\n[Curriculum] >>> Advanced to Difficulty {self.manager.current_difficulty} <<<")
