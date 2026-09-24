def unexplored_reward(is_unexplored):
    return 1.0 if is_unexplored else 0.0


def collision_penalty(is_collision):
    return -100.0 if is_collision else 0.0
