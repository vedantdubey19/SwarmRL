import functools

import numpy as np
from gymnasium import spaces
from pettingzoo import ParallelEnv


class SwarmSearchRescueEnv(ParallelEnv):
    metadata = {"name": "swarm_search_rescue_v0"}

    def __init__(self, env_config=None, num_agents=50, grid_size=20, max_cycles=500):
        if isinstance(env_config, dict):
            num_agents = env_config.get("num_agents", num_agents)
            grid_size = env_config.get("grid_size", grid_size)
            max_cycles = env_config.get("max_cycles", max_cycles)

        self._num_agents = num_agents
        self.grid_size = grid_size
        self.max_cycles = max_cycles

        self.possible_agents = [
            f"drone_{i}" for i in range(self._num_agents)
        ]
        self.agents = self.possible_agents[:]

        self.observation_spaces = {
            agent: spaces.Box(
                low=0.0,
                high=1.0,
                shape=(81,),
                dtype=np.float32,
            )
            for agent in self.possible_agents
        }

        self.action_spaces = {
            agent: spaces.Discrete(5)
            for agent in self.possible_agents
        }

        self.positions = {}
        self.explored_cells = set()
        self.target_found = False
        self.target_position = None
        self.collision_count = 0
        self.team_cells = 0
        self.team_target_found = 0
        self.current_step = 0

    @functools.lru_cache(maxsize=None)
    def observation_space(self, agent):
        return self.observation_spaces[agent]

    @functools.lru_cache(maxsize=None)
    def action_space(self, agent):
        return self.action_spaces[agent]

    def reset(self, seed=None, options=None):
        if seed is not None:
            np.random.seed(seed)

        self.agents = self.possible_agents[:]
        self.current_step = 0
        self.collision_count = 0
        self.target_found = False
        self.team_target_found = 0
        self.explored_cells = set()

        self.target_position = (
            self.grid_size // 2,
            self.grid_size // 2,
        )

        self.positions = {}

        for agent in self.agents:
            position = (
                np.random.randint(0, self.grid_size),
                np.random.randint(0, self.grid_size),
            )
            self.positions[agent] = position
            self.explored_cells.add(position)

        self.team_cells = len(self.explored_cells)

        observations = {
            agent: self._get_observation(agent)
            for agent in self.agents
        }

        infos = {
            agent: self._get_info()
            for agent in self.agents
        }

        return observations, infos

    def step(self, actions):
        self.current_step += 1

        previous_positions = self.positions.copy()
        collision_agents = set()

        for agent, action in actions.items():
            self.positions[agent] = self._move(
                previous_positions[agent],
                action,
            )

        occupied = {}

        for agent, position in self.positions.items():
            occupied.setdefault(position, []).append(agent)

        for agents_at_position in occupied.values():
            if len(agents_at_position) > 1:
                collision_agents.update(agents_at_position)

        self.collision_count += len(collision_agents)

        previous_cells = len(self.explored_cells)

        for position in self.positions.values():
            self.explored_cells.add(position)

        self.team_cells = len(self.explored_cells)
        new_explored_cells = self.team_cells - previous_cells

        for position in self.positions.values():
            if position == self.target_position:
                self.target_found = True
                self.team_target_found = 1
                break

        observations = {
            agent: self._get_observation(agent)
            for agent in self.agents
        }

        rewards = {}

        for agent in self.agents:
            reward = 0.0

            if new_explored_cells > 0:
                reward += 1.0

            if agent in collision_agents:
                reward -= 100.0

            rewards[agent] = reward

        terminated = self.target_found
        truncated = self.current_step >= self.max_cycles

        terminations = {
            agent: terminated
            for agent in self.agents
        }

        truncations = {
            agent: truncated
            for agent in self.agents
        }

        infos = {
            agent: self._get_info()
            for agent in self.agents
        }

        return (
            observations,
            rewards,
            terminations,
            truncations,
            infos,
        )

    def _move(self, position, action):
        row, col = position

        if action == 1:
            row -= 1
        elif action == 2:
            row += 1
        elif action == 3:
            col -= 1
        elif action == 4:
            col += 1

        row = max(0, min(self.grid_size - 1, row))
        col = max(0, min(self.grid_size - 1, col))

        return row, col

    def _get_observation(self, agent):
        observation = np.zeros(81, dtype=np.float32)

        row, col = self.positions[agent]

        observation[0] = row / max(1, self.grid_size - 1)
        observation[1] = col / max(1, self.grid_size - 1)

        target_row, target_col = self.target_position

        observation[2] = target_row / max(1, self.grid_size - 1)
        observation[3] = target_col / max(1, self.grid_size - 1)
        observation[4] = float(self.target_found)

        return observation

    def _get_info(self):
        return {
            "collision_count": self.collision_count,
            "team_cells": self.team_cells,
            "team_target_found": self.team_target_found,
        }

    def render(self):
        print(
            f"Step={self.current_step}, "
            f"Explored={self.team_cells}, "
            f"TargetFound={self.team_target_found}, "
            f"Collisions={self.collision_count}"
        )

    def close(self):
        pass