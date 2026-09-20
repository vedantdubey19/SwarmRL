import json

import numpy as np
import pytest

from sensors.exploration import (
    ExplorationConfig,
    ExplorationMap,
    ExplorationSummary,
)


def test_default_map_starts_empty():
    exploration = ExplorationMap(
        world_size=(20.0, 20.0),
        cell_size=2.0,
    )

    assert exploration.total_cells == 100
    assert exploration.total_explored_cells == 0
    assert exploration.explored_fraction == 0.0
    assert not exploration.grid.any()


def test_marking_position_increases_exploration():
    exploration = ExplorationMap(
        world_size=(20.0, 20.0),
        cell_size=2.0,
    )

    new_cells = exploration.mark_explored(
        positions=[
            np.array([0.0, 0.0, 0.0]),
        ],
        radius=0.5,
    )

    assert new_cells == 1
    assert exploration.total_explored_cells == 1
    assert exploration.explored_fraction == pytest.approx(0.01)


def test_repeating_same_position_adds_no_new_cells():
    exploration = ExplorationMap(
        world_size=(20.0, 20.0),
        cell_size=2.0,
    )

    position = np.array([0.0, 0.0, 0.0])

    first_count = exploration.mark_explored(
        [position],
        radius=0.5,
    )
    second_count = exploration.mark_explored(
        [position],
        radius=0.5,
    )

    assert first_count == 1
    assert second_count == 0


def test_y_coordinate_does_not_change_ground_cell():
    exploration = ExplorationMap(
        world_size=(20.0, 20.0),
        cell_size=2.0,
    )

    first = exploration.mark_explored(
        [np.array([0.0, 0.0, 0.0])],
        radius=0.5,
    )

    second = exploration.mark_explored(
        [np.array([0.0, 50.0, 0.0])],
        radius=0.5,
    )

    assert first == 1
    assert second == 0


def test_positions_are_marked_independently():
    exploration = ExplorationMap(
        world_size=(20.0, 20.0),
        cell_size=2.0,
    )

    new_cells = exploration.mark_explored(
        positions=[
            np.array([-8.0, 0.0, -8.0]),
            np.array([8.0, 0.0, 8.0]),
        ],
        radius=0.5,
    )

    assert new_cells == 2


def test_agent_update_returns_per_agent_counts():
    exploration = ExplorationMap(
        world_size=(20.0, 20.0),
        cell_size=2.0,
    )

    counts = exploration.mark_explored_by_agent(
        positions={
            "drone_000": np.array([-8.0, 0.0, -8.0]),
            "drone_001": np.array([8.0, 0.0, 8.0]),
        },
        radius=0.5,
    )

    assert counts == {
        "drone_000": 1,
        "drone_001": 1,
    }
    assert sum(counts.values()) == 2


def test_same_cell_is_credited_only_once():
    exploration = ExplorationMap(
        world_size=(20.0, 20.0),
        cell_size=2.0,
    )

    counts = exploration.mark_explored_by_agent(
        positions={
            "drone_000": np.array([0.0, 0.0, 0.0]),
            "drone_001": np.array([0.0, 0.0, 0.0]),
        },
        radius=0.5,
    )

    assert counts["drone_000"] == 1
    assert counts["drone_001"] == 0
    assert sum(counts.values()) == 1


def test_outside_positions_do_not_mark_cells():
    exploration = ExplorationMap(
        world_size=(20.0, 20.0),
        cell_size=2.0,
    )

    new_cells = exploration.mark_explored(
        [np.array([100.0, 0.0, 100.0])],
        radius=0.5,
    )

    assert new_cells == 0
    assert exploration.total_explored_cells == 0


def test_update_returns_summary():
    exploration = ExplorationMap(
        world_size=(20.0, 20.0),
        cell_size=2.0,
    )

    summary = exploration.update(
        positions=[
            np.array([0.0, 0.0, 0.0]),
        ],
        radius=0.5,
    )

    assert isinstance(summary, ExplorationSummary)
    assert summary.newly_explored_cells == 1
    assert summary.total_explored_cells == 1
    assert summary.total_cells == 100
    assert summary.explored_fraction == pytest.approx(0.01)


def test_summary_is_json_serializable():
    summary = ExplorationSummary(
        newly_explored_cells=2,
        total_explored_cells=5,
        total_cells=100,
        explored_fraction=0.05,
    )

    encoded = json.dumps(summary.to_dict())

    assert isinstance(encoded, str)


def test_as_array_has_float_values():
    exploration = ExplorationMap(
        world_size=(10.0, 10.0),
        cell_size=2.0,
    )

    exploration.mark_explored(
        [np.array([0.0, 0.0, 0.0])],
        radius=0.5,
    )

    result = exploration.as_array()

    assert result.shape == (5, 5)
    assert result.dtype == np.float32
    assert set(np.unique(result)).issubset({0.0, 1.0})


def test_as_list_contains_integer_values():
    exploration = ExplorationMap(
        world_size=(10.0, 10.0),
        cell_size=2.0,
    )

    result = exploration.as_list()

    assert len(result) == 5
    assert len(result[0]) == 5
    assert set(value for row in result for value in row) == {0}


def test_reset_clears_map():
    exploration = ExplorationMap(
        world_size=(20.0, 20.0),
        cell_size=2.0,
    )

    exploration.mark_explored(
        [np.array([0.0, 0.0, 0.0])],
        radius=0.5,
    )

    assert exploration.total_explored_cells > 0

    exploration.reset()

    assert exploration.total_explored_cells == 0
    assert exploration.explored_fraction == 0.0
    assert not exploration.grid.any()


def test_custom_config_is_used():
    config = ExplorationConfig(
        world_size=(40.0, 20.0),
        cell_size=2.0,
        exploration_radius=1.0,
    )

    exploration = ExplorationMap(config=config)

    assert exploration.width == 20
    assert exploration.height == 10
    assert exploration.total_cells == 200


def test_invalid_world_size_is_rejected():
    with pytest.raises(ValueError):
        ExplorationConfig(world_size=(0.0, 20.0))


def test_invalid_cell_size_is_rejected():
    with pytest.raises(ValueError):
        ExplorationConfig(cell_size=0.0)


def test_invalid_radius_is_rejected():
    with pytest.raises(ValueError):
        ExplorationConfig(exploration_radius=-1.0)


def test_invalid_position_shape_is_rejected():
    exploration = ExplorationMap()

    with pytest.raises(ValueError):
        exploration.mark_explored(
            [np.array([0.0, 0.0])],
        )


def test_non_finite_position_is_rejected():
    exploration = ExplorationMap()

    with pytest.raises(ValueError):
        exploration.mark_explored(
            [np.array([np.nan, 0.0, 0.0])],
        )


def test_invalid_runtime_radius_is_rejected():
    exploration = ExplorationMap()

    with pytest.raises(ValueError):
        exploration.mark_explored(
            [np.zeros(3)],
            radius=0.0,
        )