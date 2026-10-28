import time
import pytest
import numpy as np
from pettingzoo.test import parallel_api_test, parallel_seed_test

from env import (
    SwarmRLParallelEnv,
    WORLD_X_MIN,
    WORLD_X_MAX,
    WORLD_Y_MIN,
    WORLD_Y_MAX,
    WORLD_Z_MIN,
    WORLD_Z_MAX,
    DEFAULT_NUM_AGENTS,
    DEFAULT_MAX_STEPS,
)
from sensors.cone_sensor import ConeSensor, ConeSensorConfig
from sensors.exploration import ExplorationMap, ExplorationConfig
from sensors.rewards import RewardConfig, calculate_reward
from sensors.scenario import scenario_preset, ScenarioLevel


def test_reset_gives_50_valid_81_observations():
    env = SwarmRLParallelEnv(num_agents=50)
    obs, infos = env.reset(seed=42)
    assert len(obs) == 50
    assert len(infos) == 50
    for agent_id, agent_obs in obs.items():
        assert agent_obs.shape == (81,)
        assert agent_obs.dtype == np.float32
        assert np.all(np.isfinite(agent_obs))


def test_random_action_run_500_steps_stays_in_bounds():
    env = SwarmRLParallelEnv(num_agents=50, max_steps=500)
    obs, _ = env.reset(seed=123)
    rng = np.random.default_rng(123)

    for _ in range(500):
        actions = {
            agent: rng.uniform(-1.0, 1.0, size=(4,)).astype(np.float32)
            for agent in env.possible_agents
        }
        obs, rewards, terminations, truncations, infos = env.step(actions)
        for i in range(env.swarm_size):
            pos = env.positions[i]
            assert WORLD_X_MIN <= pos[0] <= WORLD_X_MAX
            assert WORLD_Y_MIN <= pos[1] <= WORLD_Y_MAX
            assert WORLD_Z_MIN <= pos[2] <= WORLD_Z_MAX
        if not env.agents:
            break


def test_action_clipping():
    env = SwarmRLParallelEnv(num_agents=5)
    env.reset(seed=42)

    extreme_actions = {
        agent: np.array([10.0, -20.0, 50.0, 99.0], dtype=np.float32)
        for agent in env.agents
    }
    # Step should clip actions to [-1.0, 1.0] and not explode
    obs, rewards, terminations, truncations, infos = env.step(extreme_actions)
    for agent, o in obs.items():
        assert np.all(np.isfinite(o))


def test_heading_convention():
    env = SwarmRLParallelEnv(num_agents=1)
    env.reset(seed=42)
    # Heading 0 points along +X in X-Z plane, +Y is up
    env.headings[0] = 0.0
    env.positions[0] = np.array([0.0, 5.0, 0.0], dtype=np.float32)

    # Action [1, 0, 0, 0] commands vx=+10 m/s (along +X)
    actions = {"drone_0": np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)}
    env.step(actions)
    assert env.positions[0][0] > 0.5  # Moved along +X
    assert env.positions[0][1] == pytest.approx(5.0)  # Y unchanged
    assert env.positions[0][2] == pytest.approx(0.0)  # Z unchanged


def test_neighbor_distances_handbuilt():
    env = SwarmRLParallelEnv(num_agents=3)
    env.reset(seed=42)

    env.positions[0] = np.array([0.0, 5.0, 0.0], dtype=np.float32)
    env.positions[1] = np.array([3.0, 5.0, 4.0], dtype=np.float32)  # dist = 5.0
    env.positions[2] = np.array([0.0, 5.0, 10.0], dtype=np.float32) # dist = 10.0

    obs = env._build_all_observations()
    obs_0 = obs["drone_0"]
    # 9 ego features, then neighbors starting at index 9
    # Neighbor 1 dx, dy, dz normalized by world span [100, 20, 100]
    # dx = 3.0 / 100 = 0.03, dy = 0.0, dz = 4.0 / 100 = 0.04
    np.testing.assert_allclose(obs_0[9:12], [0.03, 0.0, 0.04], atol=1e-5)


def test_sensor_cone_hit_miss_limits():
    sensor = ConeSensor(ConeSensorConfig(range=15.0, half_angle=np.pi / 6.0))
    pos = np.array([0.0, 5.0, 0.0], dtype=np.float32)
    heading = 0.0  # looking along +X

    # Object straight ahead within range (10m) -> HIT
    hit_obj = [{"id": "t1", "type": "target", "position": np.array([10.0, 5.0, 0.0], dtype=np.float32)}]
    res = sensor.detect(pos, heading, hit_obj)
    assert len(res) == 1
    assert res[0]["id"] == "t1"

    # Object straight ahead beyond range (16m) -> MISS
    out_of_range = [{"id": "t2", "type": "target", "position": np.array([16.0, 5.0, 0.0], dtype=np.float32)}]
    res = sensor.detect(pos, heading, out_of_range)
    assert len(res) == 0

    # Object inside range but outside half angle (angle = 45 deg > 30 deg) -> MISS
    out_of_angle = [{"id": "t3", "type": "target", "position": np.array([10.0, 5.0, 10.0], dtype=np.float32)}]
    res = sensor.detect(pos, heading, out_of_angle)
    assert len(res) == 0


def test_event_flags_raise_and_clear():
    env = SwarmRLParallelEnv(num_agents=2)
    env.reset(seed=42)

    # 1. Drone collision (< 2m)
    env.positions[0] = np.array([0.0, 5.0, 0.0], dtype=np.float32)
    env.positions[1] = np.array([1.0, 5.0, 0.0], dtype=np.float32)
    _, _, _, _, infos = env.step({a: np.zeros(4, dtype=np.float32) for a in env.agents})
    assert infos["drone_0"]["event_flags"]["drone_collision"] is True

    # Drone collision clear (> 2m)
    env.positions[0] = np.array([0.0, 5.0, 0.0], dtype=np.float32)
    env.positions[1] = np.array([10.0, 5.0, 0.0], dtype=np.float32)
    _, _, _, _, infos = env.step({a: np.zeros(4, dtype=np.float32) for a in env.agents})
    assert infos["drone_0"]["event_flags"]["drone_collision"] is False


def test_mark_explored_per_agent_symmetry():
    expl_map = ExplorationMap(config=ExplorationConfig(world_size=(100.0, 100.0), cell_size=2.0, exploration_radius=2.0))
    expl_map.reset()

    # Two agents at the exact same location in the same step
    pos_dict = {
        "drone_0": np.array([10.0, 0.0, 10.0], dtype=np.float32),
        "drone_1": np.array([10.0, 0.0, 10.0], dtype=np.float32),
    }
    per_agent, total = expl_map.mark_explored_per_agent(pos_dict)
    # Both agents get full symmetric credit for the newly explored cells
    assert per_agent["drone_0"] > 0
    assert per_agent["drone_0"] == per_agent["drone_1"]
    assert total == per_agent["drone_0"]


def test_reward_breakdown_scenario():
    cfg = RewardConfig()
    tot, details = calculate_reward(
        agent_id="drone_0",
        new_cells=3,
        previously_explored=False,
        target_found=True,
        drone_collision=True,
        obstacle_collision=True,
        boundary_violation=True,
        config=cfg,
        team_cells=5,
        team_target_found=True,
        min_neighbor_dist=1.5,
    )
    assert details["new_area"] == 3.0 * cfg.new_area
    assert details["team_new_area"] == 5.0 * cfg.team_new_area
    assert details["target_found"] == cfg.target_found
    assert details["team_target_found"] == cfg.team_target_found
    assert details["drone_collision"] == cfg.drone_collision
    assert details["obstacle_collision"] == cfg.obstacle_collision
    assert details["boundary_violation"] == cfg.boundary_violation
    assert details["proximity_penalty"] < 0.0
    assert details["total"] == pytest.approx(tot)


def test_state_shape_constant_before_and_after_reset():
    env = SwarmRLParallelEnv(num_agents=50)
    # Before reset
    st_before = env.state()
    assert st_before.shape == (471,)
    assert st_before.dtype == np.float32

    # After reset
    env.reset(seed=42)
    st_after = env.state()
    assert st_after.shape == (471,)
    assert st_after.dtype == np.float32

    # Mid episode
    env.step({a: np.zeros(4, dtype=np.float32) for a in env.agents})
    st_mid = env.state()
    assert st_mid.shape == (471,)
    assert st_mid.dtype == np.float32


def test_wind_zero_identical_trajectory():
    env1 = SwarmRLParallelEnv(num_agents=10, difficulty=0)
    env2 = SwarmRLParallelEnv(num_agents=10, difficulty=0)

    obs1, _ = env1.reset(seed=999)
    obs2, _ = env2.reset(seed=999)

    rng = np.random.default_rng(999)
    for _ in range(20):
        actions = {a: rng.uniform(-1.0, 1.0, size=(4,)).astype(np.float32) for a in env1.agents}
        env1.step(actions)
        env2.step(actions)
        np.testing.assert_allclose(env1.positions, env2.positions, atol=1e-6)
        np.testing.assert_allclose(env1.headings, env2.headings, atol=1e-6)


def test_obstacles_never_overlap_spawns_at_all_difficulties():
    for diff in range(5):
        env = SwarmRLParallelEnv(num_agents=50, difficulty=diff)
        env.reset(seed=42 + diff)

        spawn_positions = env.positions.copy()
        for obs in env.obstacles:
            dists = np.hypot(spawn_positions[:, 0] - obs.position[0], spawn_positions[:, 2] - obs.position[2])
            # Minimum clearance 4.0m
            assert np.all(dists >= (obs.radius + 4.0)), f"Overlap found at difficulty {diff}"


def test_pettingzoo_parallel_api_and_seed():
    env = SwarmRLParallelEnv(num_agents=DEFAULT_NUM_AGENTS)
    parallel_api_test(env, num_cycles=200)
    parallel_seed_test(lambda: SwarmRLParallelEnv(num_agents=DEFAULT_NUM_AGENTS))


def test_rllib_check_multiagent_environments():
    from ray.rllib.env.wrappers.pettingzoo_env import ParallelPettingZooEnv
    from ray.rllib.utils.pre_checks.env import check_multiagent_environments

    raw_env = SwarmRLParallelEnv(num_agents=10, max_steps=5)
    wrapped = ParallelPettingZooEnv(raw_env)
    check_multiagent_environments(wrapped)


def test_step_throughput_at_least_100hz():
    for diff, name in [(0, "Diff 0 (No wind)"), (4, "Diff 4 (Wind on)")]:
        env = SwarmRLParallelEnv(num_agents=50, difficulty=diff)
        env.reset(seed=42)

        actions = {a: np.array([0.5, 0.1, -0.5, 0.2], dtype=np.float32) for a in env.agents}
        num_steps = 300
        start = time.perf_counter()
        for _ in range(num_steps):
            env.step(actions)
            if not env.agents:
                env.reset(seed=42)

        elapsed = time.perf_counter() - start
        fps = num_steps / elapsed
        print(f"\n[Throughput {name}] 50 agents: {fps:.1f} steps/s (elapsed {elapsed:.3f}s for {num_steps} steps)")
        assert fps >= 100.0, f"Throughput {fps:.1f} steps/s is below required 100 steps/s for {name}"
