import json
import logging

import pytest

from sensors.metrics import (
    AgentMetrics,
    MetricsTracker,
    SwarmMetrics,
    build_agent_metrics,
    metrics_from_payload,
)


def make_agent_metrics() -> dict[str, AgentMetrics]:
    return {
        "drone_000": AgentMetrics(
            reward=2.0,
            new_cells=3,
            visible_targets=1,
            visible_obstacles=2,
            visible_drones=1,
            target_found=True,
        ),
        "drone_001": AgentMetrics(
            reward=-5.0,
            new_cells=1,
            visible_targets=0,
            visible_obstacles=1,
            visible_drones=1,
            drone_collision=True,
            boundary_violation=True,
        ),
    }


def test_agent_metrics_to_dict():
    metrics = AgentMetrics(
        reward=1.5,
        new_cells=2,
        visible_targets=1,
        target_found=True,
    )

    result = metrics.to_dict()

    assert result["reward"] == pytest.approx(1.5)
    assert result["new_cells"] == 2
    assert result["visible_targets"] == 1
    assert result["target_found"] is True


def test_agent_metrics_rejects_negative_new_cells():
    with pytest.raises(ValueError):
        AgentMetrics(new_cells=-1)


def test_agent_metrics_rejects_negative_visibility_counts():
    with pytest.raises(ValueError):
        AgentMetrics(visible_targets=-1)

    with pytest.raises(ValueError):
        AgentMetrics(visible_obstacles=-1)

    with pytest.raises(ValueError):
        AgentMetrics(visible_drones=-1)


def test_swarm_metrics_aggregates_agent_values():
    metrics = SwarmMetrics(
        step=4,
        episode=2,
        explored_fraction=0.25,
        agent_metrics=make_agent_metrics(),
    )

    assert metrics.active_agents == 2
    assert metrics.total_reward == pytest.approx(-3.0)
    assert metrics.mean_reward == pytest.approx(-1.5)
    assert metrics.newly_explored_cells == 4
    assert metrics.drone_collisions == 1
    assert metrics.obstacle_collisions == 0
    assert metrics.targets_found == 1
    assert metrics.boundary_violations == 1
    assert metrics.visible_targets == 1
    assert metrics.visible_obstacles == 3
    assert metrics.visible_drones == 2


def test_swarm_metrics_to_dict_includes_agents():
    metrics = SwarmMetrics(
        step=1,
        explored_fraction=0.1,
        agent_metrics=make_agent_metrics(),
    )

    result = metrics.to_dict()

    assert result["step"] == 1
    assert result["active_agents"] == 2
    assert result["agents"]["drone_000"]["new_cells"] == 3
    assert result["agents"]["drone_001"]["drone_collision"] is True


def test_swarm_metrics_to_dict_can_hide_agents():
    metrics = SwarmMetrics(
        step=1,
        explored_fraction=0.1,
        agent_metrics=make_agent_metrics(),
    )

    result = metrics.to_dict(include_agents=False)

    assert "agents" not in result
    assert result["active_agents"] == 2


def test_swarm_metrics_is_json_serializable():
    metrics = SwarmMetrics(
        step=1,
        explored_fraction=0.1,
        agent_metrics=make_agent_metrics(),
    )

    encoded = metrics.to_json()

    assert isinstance(encoded, str)
    assert json.loads(encoded)["active_agents"] == 2


def test_swarm_metrics_rejects_invalid_step():
    with pytest.raises(ValueError):
        SwarmMetrics(step=-1)


def test_swarm_metrics_rejects_invalid_episode():
    with pytest.raises(ValueError):
        SwarmMetrics(step=1, episode=-1)


def test_swarm_metrics_rejects_invalid_explored_fraction():
    with pytest.raises(ValueError):
        SwarmMetrics(
            step=1,
            explored_fraction=1.1,
        )


def test_tracker_records_and_exposes_latest(caplog):
    tracker = MetricsTracker()

    with caplog.at_level(logging.INFO):
        first = tracker.record(
            step=1,
            episode=0,
            explored_fraction=0.1,
            agent_metrics=make_agent_metrics(),
        )

    assert tracker.total_steps == 1
    assert tracker.latest is first
    assert "Recorded swarm metrics" in caplog.text


def test_tracker_summary_aggregates_history():
    tracker = MetricsTracker()

    tracker.record(
        step=1,
        explored_fraction=0.1,
        agent_metrics={
            "drone_000": AgentMetrics(
                reward=1.0,
                new_cells=2,
                target_found=True,
            )
        },
    )

    tracker.record(
        step=2,
        explored_fraction=0.3,
        agent_metrics={
            "drone_000": AgentMetrics(
                reward=-2.0,
                new_cells=1,
                drone_collision=True,
            )
        },
    )

    summary = tracker.summary()

    assert summary["total_steps"] == 2
    assert summary["final_explored_fraction"] == pytest.approx(
        0.3
    )
    assert summary["cumulative_reward"] == pytest.approx(-1.0)
    assert summary["cumulative_new_cells"] == 3
    assert summary["total_drone_collisions"] == 1
    assert summary["total_targets_found"] == 1


def test_empty_tracker_returns_empty_summary():
    tracker = MetricsTracker()

    assert tracker.summary() == {
        "total_steps": 0,
        "final_explored_fraction": 0.0,
        "cumulative_reward": 0.0,
        "cumulative_new_cells": 0,
        "total_drone_collisions": 0,
        "total_obstacle_collisions": 0,
        "total_targets_found": 0,
        "total_boundary_violations": 0,
    }


def test_tracker_reset_clears_history():
    tracker = MetricsTracker()

    tracker.record(step=1)
    assert tracker.total_steps == 1

    tracker.reset()

    assert tracker.total_steps == 0
    assert tracker.latest is None


def test_build_agent_metrics_uses_sensor_and_event_data():
    metrics = build_agent_metrics(
        reward=2.5,
        new_cells=4,
        sensor_summary={
            "visible_targets": 1,
            "visible_obstacles": 2,
            "visible_drones": 3,
        },
        event_flags={
            "drone_collision": True,
            "target_found": True,
        },
    )

    assert metrics.reward == pytest.approx(2.5)
    assert metrics.new_cells == 4
    assert metrics.visible_targets == 1
    assert metrics.visible_obstacles == 2
    assert metrics.visible_drones == 3
    assert metrics.drone_collision is True
    assert metrics.target_found is True
    assert metrics.obstacle_collision is False


def test_metrics_from_payload_builds_swarm_metrics():
    payload = {
        "step": 10,
        "map": {
            "explored_fraction": 0.4,
        },
        "agents": [
            {
                "agent_id": "drone_000",
                "reward": 1.5,
                "visible_targets": 1,
                "visible_obstacles": 2,
                "visible_drones": 3,
                "reward_components": {
                    "new_area": 2,
                },
                "event_flags": {
                    "drone_collision": False,
                    "obstacle_collision": False,
                    "target_found": True,
                    "boundary_violation": False,
                },
            }
        ],
    }

    metrics = metrics_from_payload(
        payload,
        episode=3,
    )

    assert metrics.step == 10
    assert metrics.episode == 3
    assert metrics.explored_fraction == pytest.approx(0.4)
    assert metrics.active_agents == 1
    assert metrics.total_reward == pytest.approx(1.5)
    assert metrics.newly_explored_cells == 2
    assert metrics.targets_found == 1


def test_metrics_from_payload_rejects_missing_step():
    with pytest.raises(ValueError):
        metrics_from_payload(
            {
                "agents": [],
            }
        )


def test_metrics_from_payload_rejects_missing_agent_id():
    with pytest.raises(ValueError):
        metrics_from_payload(
            {
                "step": 1,
                "agents": [
                    {
                        "reward": 0.0,
                    }
                ],
            }
        )


def test_summary_json_is_valid():
    tracker = MetricsTracker()
    tracker.record(step=1)

    encoded = tracker.summary_json()

    assert isinstance(encoded, str)
    assert json.loads(encoded)["total_steps"] == 1