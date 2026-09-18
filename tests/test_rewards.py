from sensors.rewards import calculate_reward


def test_new_area_reward_is_positive():
    reward, components = calculate_reward(
        agent_id="drone_000",
        new_cells=3,
        previously_explored=False,
        target_found=False,
        drone_collision=False,
        obstacle_collision=False,
        boundary_violation=False,
    )

    assert reward > 0
    assert components["new_area"] == 3.0


def test_collision_penalty_is_negative():
    reward, components = calculate_reward(
        agent_id="drone_000",
        new_cells=0,
        previously_explored=False,
        target_found=False,
        drone_collision=True,
        obstacle_collision=False,
        boundary_violation=False,
    )

    assert reward < 0
    assert components["drone_collision"] == -100.0


def test_target_reward_is_positive():
    reward, components = calculate_reward(
        agent_id="drone_000",
        new_cells=0,
        previously_explored=False,
        target_found=True,
        drone_collision=False,
        obstacle_collision=False,
        boundary_violation=False,
    )

    assert components["target_found"] == 20.0
    assert reward > 0