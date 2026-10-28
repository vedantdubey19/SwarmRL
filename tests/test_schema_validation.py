import json
import os
import jsonschema
import numpy as np
import pytest

from env import SwarmRLParallelEnv
from sensors.bridge import (
    build_world_message,
    build_frame_message,
    build_grid_snapshot_message,
    build_grid_delta_message,
    create_registration_message,
)

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "server", "schema.json")


@pytest.fixture(scope="module")
def schema():
    with open(SCHEMA_PATH, "r") as f:
        return json.load(f)


def test_schema_validates_registration(schema):
    pub_msg = create_registration_message("publisher")
    jsonschema.validate(instance=pub_msg, schema=schema)

    sub_msg = create_registration_message("subscriber")
    jsonschema.validate(instance=sub_msg, schema=schema)


def test_schema_validates_world_message(schema):
    env = SwarmRLParallelEnv(num_agents=50, difficulty=2)
    env.reset(seed=42)

    world_msg = build_world_message(env)
    jsonschema.validate(instance=world_msg, schema=schema)


def test_schema_validates_real_50_agent_frames(schema):
    env = SwarmRLParallelEnv(num_agents=50, difficulty=3)
    obs, infos = env.reset(seed=42)

    # Initial frame at step 0
    f0 = build_frame_message(env, infos=infos)
    jsonschema.validate(instance=f0, schema=schema)

    # Step frame
    actions = {a: np.random.uniform(-0.5, 0.5, size=(4,)).astype(np.float32) for a in env.agents}
    obs, rewards, terminations, truncations, infos = env.step(actions)
    f1 = build_frame_message(env, infos=infos, step_reward_sum=sum(rewards.values()))
    jsonschema.validate(instance=f1, schema=schema)
    assert len(f1["drones"]) == 50


def test_schema_validates_grid_snapshot_and_delta(schema):
    env = SwarmRLParallelEnv(num_agents=50)
    env.reset(seed=42)

    snap = build_grid_snapshot_message(env)
    jsonschema.validate(instance=snap, schema=schema)

    delta = build_grid_delta_message(step=1, newly_explored_indices=[12, 13, 50, 105])
    jsonschema.validate(instance=delta, schema=schema)
