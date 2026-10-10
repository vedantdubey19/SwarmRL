import numpy as np
import pytest

from env import (
    MAX_HORIZ_VEL,
    MAX_VERT_VEL,
    WORLD_X_MAX,
    WORLD_X_MIN,
    WORLD_Y_MAX,
    WORLD_Y_MIN,
    WORLD_Z_MAX,
    WORLD_Z_MIN,
    SwarmRLParallelEnv,
)

# Each case starts a drone just inside one face of the world and commands full speed
# outward. Starts are kept clear of the spawn grid and obstacles (|x|, |z| <= 38).
# One step at dt=0.05 moves 0.5 m horizontally or 0.15 m vertically.
BOUNDARY_CASES = {
    "x_max": ([49.8, 5.0, 45.0], [1.0, 0.0, 0.0, 0.0], 0, WORLD_X_MAX),
    "x_min": ([-49.8, 5.0, 45.0], [-1.0, 0.0, 0.0, 0.0], 0, WORLD_X_MIN),
    "z_max": ([45.0, 5.0, 49.8], [0.0, 0.0, 1.0, 0.0], 2, WORLD_Z_MAX),
    "z_min": ([45.0, 5.0, -49.8], [0.0, 0.0, -1.0, 0.0], 2, WORLD_Z_MIN),
    "ceiling": ([45.0, 19.9, 45.0], [0.0, 1.0, 0.0, 0.0], 1, WORLD_Y_MAX),
    "floor": ([45.0, 0.1, 45.0], [0.0, -1.0, 0.0, 0.0], 1, WORLD_Y_MIN),
}

COMMANDED_SPEED = {0: MAX_HORIZ_VEL, 1: MAX_VERT_VEL, 2: MAX_HORIZ_VEL}


def step_drone_0(env, start, action):
    env.drones["drone_0"].position = np.array(start, dtype=np.float32)
    actions = {a: np.zeros(4, dtype=np.float32) for a in env.agents}
    actions["drone_0"] = np.array(action, dtype=np.float32)
    return env.step(actions)


@pytest.mark.parametrize("case", BOUNDARY_CASES, ids=list(BOUNDARY_CASES))
def test_boundary_hit_clips_flags_damps_and_penalizes(case):
    start, action, axis, limit = BOUNDARY_CASES[case]
    env = SwarmRLParallelEnv(num_agents=5)
    env.reset(seed=10)

    _, _, terminations, _, infos = step_drone_0(env, start, action)
    drone = env.drones["drone_0"]

    assert drone.position[axis] == limit
    other_axes = [i for i in range(3) if i != axis]
    np.testing.assert_allclose(drone.position[other_axes], np.array(start)[other_axes], atol=1e-5)

    commanded = np.sign(action[axis]) * COMMANDED_SPEED[axis]
    assert drone.velocity[axis] == pytest.approx(0.1 * commanded)

    assert infos["drone_0"]["event_flags"]["boundary_violation"] is True
    assert infos["drone_0"]["reward_breakdown"]["boundary_violation"] == pytest.approx(-5.0)
    assert terminations["drone_0"] is False
    assert drone.alive


@pytest.mark.parametrize("case", BOUNDARY_CASES, ids=list(BOUNDARY_CASES))
def test_stopping_short_of_boundary_is_not_a_violation(case):
    start, action, axis, limit = BOUNDARY_CASES[case]
    inside = list(start)
    inside[axis] = limit - np.sign(action[axis]) * 1.0
    env = SwarmRLParallelEnv(num_agents=5)
    env.reset(seed=10)

    _, _, _, _, infos = step_drone_0(env, inside, action)
    drone = env.drones["drone_0"]

    assert infos["drone_0"]["event_flags"]["boundary_violation"] is False
    assert infos["drone_0"]["reward_breakdown"]["boundary_violation"] == 0.0
    assert drone.velocity[axis] == pytest.approx(np.sign(action[axis]) * COMMANDED_SPEED[axis])


def test_terminate_on_boundary_kills_the_drone():
    start, action, axis, limit = BOUNDARY_CASES["x_max"]
    env = SwarmRLParallelEnv(num_agents=5, terminate_on_boundary=True)
    env.reset(seed=10)

    _, _, terminations, _, _ = step_drone_0(env, start, action)

    assert terminations["drone_0"] is True
    assert "drone_0" not in env.agents
    assert env.drones["drone_0"].position[axis] == limit
