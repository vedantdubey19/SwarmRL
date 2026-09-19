import numpy as np

from sensors.exploration import ExplorationMap


def test_exploration_map_starts_empty():
    exploration = ExplorationMap(
        world_size=(20.0, 20.0),
        cell_size=2.0,
    )

    assert exploration.explored_fraction == 0.0


def test_marking_position_increases_exploration():
    exploration = ExplorationMap(
        world_size=(20.0, 20.0),
        cell_size=2.0,
    )

    new_cells = exploration.mark_explored(
        [np.array([0.0, 0.0, 0.0])],
        radius=2.0,
    )

    assert new_cells > 0
    assert exploration.explored_fraction > 0.0


def test_repeating_position_adds_no_new_cells():
    exploration = ExplorationMap(
        world_size=(20.0, 20.0),
        cell_size=2.0,
    )

    position = np.array([0.0, 0.0, 0.0])

    first = exploration.mark_explored([position], radius=2.0)
    second = exploration.mark_explored([position], radius=2.0)

    assert first > 0
    assert second == 0


def test_mark_explored_per_agent_distinct_cells():
    exploration = ExplorationMap(
        world_size=(40.0, 40.0),
        cell_size=2.0,
    )

    positions = {
        "drone_0": np.array([-10.0, 0.0, -10.0]),
        "drone_1": np.array([10.0, 0.0, 10.0]),
    }

    per_agent, total_new = exploration.mark_explored_per_agent(positions, radius=2.0)

    assert per_agent["drone_0"] > 0
    assert per_agent["drone_1"] > 0
    assert per_agent["drone_0"] == per_agent["drone_1"]
    assert total_new == per_agent["drone_0"] + per_agent["drone_1"]


def test_mark_explored_per_agent_overlapping_symmetric_credit():
    exploration = ExplorationMap(
        world_size=(40.0, 40.0),
        cell_size=2.0,
    )

    # Both drones are close to each other at the frontier
    positions = {
        "drone_0": np.array([0.0, 0.0, 0.0]),
        "drone_1": np.array([1.0, 0.0, 0.0]),
    }

    per_agent, total_new = exploration.mark_explored_per_agent(positions, radius=2.0)

    # Both drones get symmetric positive credit without order bias
    assert per_agent["drone_0"] > 0
    assert per_agent["drone_1"] > 0
    # Because of overlap, total new is less than the raw sum of both footprints
    assert total_new < per_agent["drone_0"] + per_agent["drone_1"]

    # In next step, repeated position awards 0 new cells
    per_agent_next, total_new_next = exploration.mark_explored_per_agent(positions, radius=2.0)
    assert per_agent_next["drone_0"] == 0
    assert per_agent_next["drone_1"] == 0
    assert total_new_next == 0