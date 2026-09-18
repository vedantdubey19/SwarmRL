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