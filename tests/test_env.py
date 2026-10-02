import time
import numpy as np
import pytest

from env import (
    DEFAULT_NUM_AGENTS,
    EXPLORATION_CELL_SIZE,
    MAX_HORIZ_VEL,
    MAX_VERT_VEL,
    WORLD_X_MAX,
    WORLD_Y_MAX,
    WORLD_Z_MAX,
    SwarmRLParallelEnv,
)


def test_env_initialization():
    env = SwarmRLParallelEnv(num_agents=50)
    assert len(env.possible_agents) == 50
    assert len(env.agents) == 50

    for agent in env.possible_agents:
        act_space = env.action_space(agent)
        assert act_space.shape == (4,)
        assert act_space.dtype == np.float32

        obs_space = env.observation_space(agent)
        assert obs_space.shape == (81,)
        assert obs_space.dtype == np.float32


def test_env_reset():
    env = SwarmRLParallelEnv(num_agents=50)
    obs, infos = env.reset(seed=42)

    assert len(obs) == 50
    assert len(infos) == 50

    for agent_id, agent_obs in obs.items():
        assert agent_obs.shape == (81,)
        assert agent_obs.dtype == np.float32
        assert np.all(np.isfinite(agent_obs))


def test_env_step_contract_and_reward_unpack():
    env = SwarmRLParallelEnv(num_agents=50)
    obs, _ = env.reset(seed=42)

    actions = {
        agent: np.random.uniform(-1.0, 1.0, size=(4,)).astype(np.float32)
        for agent in env.agents
    }

    next_obs, rewards, terminations, truncations, infos = env.step(actions)

    for agent_id in env.possible_agents:
        if agent_id in rewards:
            # Reward must be scalar float, NOT tuple
            assert isinstance(rewards[agent_id], float)
            assert not isinstance(rewards[agent_id], tuple)

            # Info must contain reward_breakdown
            assert "reward_breakdown" in infos[agent_id]
            breakdown = infos[agent_id]["reward_breakdown"]
            assert isinstance(breakdown, dict)
            assert "new_area" in breakdown
            assert "team_new_area" in breakdown
            assert "proximity_penalty" in breakdown
            assert "total" in breakdown

            assert isinstance(terminations[agent_id], bool)
            assert isinstance(truncations[agent_id], bool)

            if agent_id in next_obs:
                assert next_obs[agent_id].shape == (81,)
                assert next_obs[agent_id].dtype == np.float32

    # Raw PettingZoo contract: keyed by agent only. RLlib's wrapper adds __all__ itself.
    assert set(terminations) == set(actions)
    assert set(truncations) == set(actions)


def test_rllib_dict_observation_mode():
    env = SwarmRLParallelEnv(num_agents=50, include_global_state=True)
    obs, _ = env.reset(seed=42)

    for agent_id in env.possible_agents:
        space = env.observation_space(agent_id)
        assert "obs" in space.spaces
        assert "state" in space.spaces
        assert space.spaces["obs"].shape == (81,)
        assert space.spaces["state"].shape == (471,)

        agent_obs = obs[agent_id]
        assert isinstance(agent_obs, dict)
        assert agent_obs["obs"].shape == (81,)
        assert agent_obs["obs"].dtype == np.float32
        assert agent_obs["state"].shape == (471,)
        assert agent_obs["state"].dtype == np.float32


def test_centralized_critic_state():
    env = SwarmRLParallelEnv(num_agents=50)
    env.reset(seed=42)

    global_state = env.state()
    assert isinstance(global_state, np.ndarray)
    assert global_state.dtype == np.float32
    assert global_state.ndim == 1
    # 50 drones * 9 + 5 targets * 4 + 1 exploration fraction = 450 + 20 + 1 = 471
    assert global_state.shape == (471,)
    assert np.all(np.isfinite(global_state))


def test_env_step_throughput_sustains_20hz():
    env = SwarmRLParallelEnv(num_agents=50)
    env.reset(seed=123)

    num_steps = 100
    start_time = time.perf_counter()

    for _ in range(num_steps):
        actions = {
            agent: np.random.uniform(-0.5, 0.5, size=(4,)).astype(np.float32)
            for agent in env.agents
        }
        env.step(actions)
        if len(env.agents) == 0:
            env.reset()

    elapsed = time.perf_counter() - start_time
    fps = num_steps / elapsed

    print(f"\n[Throughput Benchmark] 50 agents x {num_steps} steps took {elapsed:.3f}s ({fps:.1f} Hz)")
    assert fps >= 20.0, f"Throughput {fps:.1f} Hz is below required 20 Hz"


def test_reward_breakdown_diagnostic_wiring_and_target_discovery():
    env = SwarmRLParallelEnv(num_agents=50)
    env.reset(seed=42)

    # Place drone_0 and drone_1 directly over target_0 at cruise altitude y=5.0
    target_pos = env.targets[0].position.copy()
    env.drones["drone_0"].position = np.array([target_pos[0], 5.0, target_pos[2]], dtype=np.float32)
    env.drones["drone_1"].position = np.array([target_pos[0] + 2.2, 5.0, target_pos[2]], dtype=np.float32)

    actions = {a: np.zeros(4, dtype=np.float32) for a in env.agents}
    _, rewards, terminations, _, infos = env.step(actions)

    rb0 = infos["drone_0"]["reward_breakdown"]
    rb1 = infos["drone_1"]["reward_breakdown"]

    # Both drones at y=5.0 should symmetrically discover target_0 at y=0.5
    assert rb0["target_found"] == pytest.approx(10.0)
    assert rb1["target_found"] == pytest.approx(10.0)
    assert rb0["team_target_found"] == pytest.approx(0.2)
    assert rb0["team_target_found_flag"] is True
    assert rb0["min_neighbor_dist"] is not None
    assert rb0["min_neighbor_dist"] == pytest.approx(2.2, abs=1e-3)
    assert rb0["proximity_penalty"] < 0.0
    assert "team_cells" in rb0
    assert "event_flags" in infos["drone_0"]
    assert infos["drone_0"]["event_flags"]["team_target_found"] is True


def test_all_targets_found_terminates_all_active_agents():
    env = SwarmRLParallelEnv(num_agents=10)
    env.reset(seed=7)

    # Mark first 4 targets found, place drone_0 over 5th target
    for t in env.targets[:-1]:
        t.found = True
    last_t = env.targets[-1].position
    env.drones["drone_0"].position = np.array([last_t[0], 5.0, last_t[2]], dtype=np.float32)

    actions = {a: np.zeros(4, dtype=np.float32) for a in env.agents}
    _, _, terminations, _, _ = env.step(actions)

    assert len(terminations) == 10
    for agent_id, term in terminations.items():
        assert term is True, f"Agent {agent_id} should terminate when all_targets_found is True"
    assert len(env.agents) == 0


def test_random_actions_n_steps_bounds_and_shapes():
    env = SwarmRLParallelEnv(num_agents=50)
    obs, infos = env.reset(seed=42)
    assert len(obs) == 50

    for step_idx in range(25):
        actions = {
            agent: np.random.uniform(-1.0, 1.0, size=(4,)).astype(np.float32)
            for agent in env.agents
        }
        obs, rewards, terminations, truncations, infos = env.step(actions)
        for agent_id, a_obs in obs.items():
            assert a_obs.shape == (81,)
            assert a_obs.dtype == np.float32
            assert np.all(np.isfinite(a_obs))
            drone = env.drones[agent_id]
            assert -50.0 <= drone.position[0] <= 50.0
            assert 0.0 <= drone.position[1] <= 20.0
            assert -50.0 <= drone.position[2] <= 50.0

        if not env.agents:
            break


def test_boundary_collision_response_and_dampening():
    env = SwarmRLParallelEnv(num_agents=5, terminate_on_boundary=False)
    env.reset(seed=10)

    # Place drone_0 at the positive X boundary moving outward at max velocity
    env.drones["drone_0"].position = np.array([49.8, 5.0, 0.0], dtype=np.float32)
    actions = {
        "drone_0": np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32),
        "drone_1": np.zeros(4, dtype=np.float32),
        "drone_2": np.zeros(4, dtype=np.float32),
        "drone_3": np.zeros(4, dtype=np.float32),
        "drone_4": np.zeros(4, dtype=np.float32),
    }

    obs, rewards, terminations, truncations, infos = env.step(actions)

    rb0 = infos["drone_0"]["reward_breakdown"]
    assert infos["drone_0"]["event_flags"]["boundary_violation"] is True
    assert rb0["boundary_violation"] == pytest.approx(-5.0)

    drone0 = env.drones["drone_0"]
    # Position corrected to boundary limit
    assert drone0.position[0] == pytest.approx(50.0)
    # Velocity dampened
    assert np.abs(drone0.velocity[0]) <= 1.0


def test_edge_case_zero_active_agents():
    env = SwarmRLParallelEnv(num_agents=5)
    env.reset(seed=11)

    # Force all agents dead
    for drone in env.drones.values():
        drone.alive = False
    env.agents.clear()

    obs, rewards, terminations, truncations, infos = env.step({})
    assert len(obs) == 0
    assert len(rewards) == 0
    assert terminations == {}
    assert truncations == {}
    assert len(env.agents) == 0


def test_edge_case_identical_positions():
    env = SwarmRLParallelEnv(num_agents=5)
    env.reset(seed=12)

    # Place all 5 drones at the identical coordinate
    collinear_pos = np.array([0.0, 5.0, 0.0], dtype=np.float32)
    for drone in env.drones.values():
        drone.position = collinear_pos.copy()

    actions = {a: np.zeros(4, dtype=np.float32) for a in env.agents}
    obs, rewards, terminations, truncations, infos = env.step(actions)

    # All observations must remain finite (no division by zero or NaN)
    for a_id, a_obs in obs.items():
        assert np.all(np.isfinite(a_obs))
    # All drones should detect drone collision
    for a_id in env.possible_agents:
        if a_id in infos:
            assert infos[a_id]["event_flags"]["drone_collision"] is True


def test_edge_case_exact_boundary_positions():
    env = SwarmRLParallelEnv(num_agents=3)
    env.reset(seed=13)

    # Position on exact boundaries
    env.drones["drone_0"].position = np.array([50.0, 10.0, 0.0], dtype=np.float32)
    env.drones["drone_1"].position = np.array([0.0, 20.0, 0.0], dtype=np.float32)
    env.drones["drone_2"].position = np.array([0.0, 10.0, -50.0], dtype=np.float32)

    actions = {a: np.zeros(4, dtype=np.float32) for a in env.agents}
    obs, rewards, terminations, truncations, infos = env.step(actions)

    for a_id, a_obs in obs.items():
        assert np.all(np.isfinite(a_obs))


def test_edge_case_max_velocity_actions_every_step():
    env = SwarmRLParallelEnv(num_agents=10, terminate_on_boundary=False)
    env.reset(seed=14)

    max_actions = {a: np.array([1.0, 1.0, 1.0, 1.0], dtype=np.float32) for a in env.possible_agents}
    for _ in range(15):
        obs, rewards, terminations, truncations, infos = env.step(max_actions)
        for a_id, a_obs in obs.items():
            assert np.all(np.isfinite(a_obs))
            d = env.drones[a_id]
            assert -50.0 <= d.position[0] <= 50.0
            assert 0.0 <= d.position[1] <= 20.0
            assert -50.0 <= d.position[2] <= 50.0


def test_world_is_fixed_size():
    with pytest.raises(TypeError):
        SwarmRLParallelEnv(num_agents=5, world_size=(500.0, 500.0))

    env = SwarmRLParallelEnv(num_agents=5)
    assert (env.exploration_map.width, env.exploration_map.height) == (50, 50)
    assert env.exploration_map.config.cell_size == EXPLORATION_CELL_SIZE == 2.0


def test_observation_and_state_normalization_follow_world_constants():
    env = SwarmRLParallelEnv(num_agents=5)
    env.reset(seed=3)
    drone = env.drones["drone_0"]
    drone.position = np.array([25.0, 10.0, -40.0], dtype=np.float32)
    drone.velocity = np.array([5.0, -1.5, 2.0], dtype=np.float32)

    obs = env._get_observation("drone_0")
    expected = [25.0 / WORLD_X_MAX, 10.0 / WORLD_Y_MAX, -40.0 / WORLD_Z_MAX,
                5.0 / MAX_HORIZ_VEL, -1.5 / MAX_VERT_VEL, 2.0 / MAX_HORIZ_VEL]
    np.testing.assert_allclose(obs[:6], expected, rtol=1e-6)
    np.testing.assert_allclose(env.state()[:6], expected, rtol=1e-6)


@pytest.mark.filterwarnings("error")
def test_pettingzoo_parallel_api_without_warnings():
    from pettingzoo.test import parallel_api_test, parallel_seed_test

    parallel_api_test(SwarmRLParallelEnv(num_agents=DEFAULT_NUM_AGENTS), num_cycles=200)
    parallel_seed_test(lambda: SwarmRLParallelEnv(num_agents=DEFAULT_NUM_AGENTS))


def test_rllib_wrapper_supplies_all_key():
    pytest.importorskip("ray.rllib")
    from ray.rllib.env.wrappers.pettingzoo_env import ParallelPettingZooEnv

    env = ParallelPettingZooEnv(SwarmRLParallelEnv(num_agents=10, max_steps=3))
    env.reset(seed=0)
    actions = {f"drone_{i}": np.zeros(4, dtype=np.float32) for i in range(10)}
    for _ in range(3):
        _, _, terminations, truncations, _ = env.step(actions)
    assert terminations["__all__"] is False
    assert truncations["__all__"] is True
