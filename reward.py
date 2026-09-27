"""QUARANTINED STUB MODULE.

DO NOT USE: This stub previously bypassed multi-agent reward shaping,
collision penalties, and proximity repulsion.
Use `sensors.rewards.calculate_reward` instead.
"""

import warnings


def unexplored_reward(is_unexplored: bool) -> float:
    warnings.warn(
        "reward.unexplored_reward is deprecated and quarantined. "
        "Use sensors.rewards.calculate_reward instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return 1.0 if is_unexplored else 0.0
