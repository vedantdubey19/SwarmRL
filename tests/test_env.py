import time
import numpy as np
import pytest

from env import SwarmRLParallelEnv, DEFAULT_NUM_AGENTS


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
