import json
import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np


LOGGER = logging.getLogger(__name__)


@dataclass
class AgentMetrics:
    """Metrics collected for one agent during one step."""

    reward: float = 0.0
    new_cells: int = 0
    visible_targets: int = 0
    visible_obstacles: int = 0
    visible_drones: int = 0
    drone_collision: bool = False
    obstacle_collision: bool = False
    target_found: bool = False
    boundary_violation: bool = False

    def __post_init__(self) -> None:
        if self.new_cells < 0:
            raise ValueError(
                "Newly explored cells must not be negative."
            )

        if self.visible_targets < 0:
            raise ValueError(
                "Visible target count must not be negative."
            )

        if self.visible_obstacles < 0:
            raise ValueError(
                "Visible obstacle count must not be negative."
            )

        if self.visible_drones < 0:
            raise ValueError(
                "Visible drone count must not be negative."
            )

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-compatible agent metrics."""
        return {
            "reward": float(self.reward),
            "new_cells": int(self.new_cells),
            "visible_targets": int(
                self.visible_targets
            ),
            "visible_obstacles": int(
                self.visible_obstacles
            ),
            "visible_drones": int(
                self.visible_drones
            ),
            "drone_collision": bool(
                self.drone_collision
            ),
            "obstacle_collision": bool(
                self.obstacle_collision
            ),
            "target_found": bool(self.target_found),
            "boundary_violation": bool(
                self.boundary_violation
            ),
        }


@dataclass
class SwarmMetrics:
    """Aggregate metrics for one swarm simulation step."""

    step: int
    episode: int = 0
    explored_fraction: float = 0.0
    agent_metrics: dict[str, AgentMetrics] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if self.step < 0:
            raise ValueError("Step must not be negative.")

        if self.episode < 0:
            raise ValueError("Episode must not be negative.")

        if not 0.0 <= self.explored_fraction <= 1.0:
            raise ValueError(
                "Explored fraction must be between 0 and 1."
            )

    @property
    def active_agents(self) -> int:
        """Return number of agents represented in this step."""
        return len(self.agent_metrics)

    @property
    def total_reward(self) -> float:
        """Return total reward over all active agents."""
        return float(
            sum(
                metrics.reward
                for metrics in self.agent_metrics.values()
            )
        )

    @property
    def mean_reward(self) -> float:
        """Return average reward over all active agents."""
        if self.active_agents == 0:
            return 0.0

        return float(self.total_reward / self.active_agents)

    @property
    def newly_explored_cells(self) -> int:
        """Return total newly explored cells."""
        return int(
            sum(
                metrics.new_cells
                for metrics in self.agent_metrics.values()
            )
        )

    @property
    def drone_collisions(self) -> int:
        """Return number of agents with drone collisions."""
        return sum(
            metrics.drone_collision
            for metrics in self.agent_metrics.values()
        )

    @property
    def obstacle_collisions(self) -> int:
        """Return number of agents with obstacle collisions."""
        return sum(
            metrics.obstacle_collision
            for metrics in self.agent_metrics.values()
        )

    @property
    def targets_found(self) -> int:
        """Return number of agents finding a target."""
        return sum(
            metrics.target_found
            for metrics in self.agent_metrics.values()
        )

    @property
    def boundary_violations(self) -> int:
        """Return number of agents outside boundaries."""
        return sum(
            metrics.boundary_violation
            for metrics in self.agent_metrics.values()
        )

    @property
    def visible_targets(self) -> int:
        """Return total currently visible targets."""
        return sum(
            metrics.visible_targets
            for metrics in self.agent_metrics.values()
        )

    @property
    def visible_obstacles(self) -> int:
        """Return total currently visible obstacles."""
        return sum(
            metrics.visible_obstacles
            for metrics in self.agent_metrics.values()
        )

    @property
    def visible_drones(self) -> int:
        """Return total currently visible drones."""
        return sum(
            metrics.visible_drones
            for metrics in self.agent_metrics.values()
        )

    def to_dict(
        self,
        include_agents: bool = True,
    ) -> dict[str, Any]:
        """Return a JSON-compatible metric record."""
        payload = {
            "step": int(self.step),
            "episode": int(self.episode),
            "active_agents": int(self.active_agents),
            "explored_fraction": float(
                self.explored_fraction
            ),
            "total_reward": float(self.total_reward),
            "mean_reward": float(self.mean_reward),
            "newly_explored_cells": int(
                self.newly_explored_cells
            ),
            "drone_collisions": int(
                self.drone_collisions
            ),
            "obstacle_collisions": int(
                self.obstacle_collisions
            ),
            "targets_found": int(self.targets_found),
            "boundary_violations": int(
                self.boundary_violations
            ),
            "visible_targets": int(
                self.visible_targets
            ),
            "visible_obstacles": int(
                self.visible_obstacles
            ),
            "visible_drones": int(
                self.visible_drones
            ),
        }

        if include_agents:
            payload["agents"] = {
                agent_id: metrics.to_dict()
                for agent_id, metrics in self.agent_metrics.items()
            }

        return payload

    def to_json(
        self,
        include_agents: bool = True,
    ) -> str:
        """Encode the metric record as JSON."""
        return json.dumps(
            self.to_dict(include_agents=include_agents)
        )


class MetricsTracker:
    """Collect and export Saju module metrics over time."""

    def __init__(self) -> None:
        self.history: list[SwarmMetrics] = []

    @property
    def latest(self) -> SwarmMetrics | None:
        """Return latest metric record or None."""
        if not self.history:
            return None

        return self.history[-1]

    @property
    def total_steps(self) -> int:
        """Return number of recorded steps."""
        return len(self.history)

    def record(
        self,
        step: int,
        episode: int = 0,
        explored_fraction: float = 0.0,
        agent_metrics: dict[str, AgentMetrics] | None = None,
    ) -> SwarmMetrics:
        """Create and store a swarm metric record."""
        metrics = SwarmMetrics(
            step=step,
            episode=episode,
            explored_fraction=explored_fraction,
            agent_metrics=agent_metrics or {},
        )

        self.history.append(metrics)

        LOGGER.info(
            "Recorded swarm metrics: episode=%s step=%s "
            "agents=%s reward=%.4f explored=%.4f",
            metrics.episode,
            metrics.step,
            metrics.active_agents,
            metrics.total_reward,
            metrics.explored_fraction,
        )

        return metrics

    def reset(self) -> None:
        """Clear all recorded metrics."""
        self.history.clear()

    def summary(self) -> dict[str, Any]:
        """Return overall summary for all recorded steps."""
        if not self.history:
            return {
                "total_steps": 0,
                "final_explored_fraction": 0.0,
                "cumulative_reward": 0.0,
                "cumulative_new_cells": 0,
                "total_drone_collisions": 0,
                "total_obstacle_collisions": 0,
                "total_targets_found": 0,
                "total_boundary_violations": 0,
            }

        return {
            "total_steps": int(self.total_steps),
            "final_explored_fraction": float(
                self.latest.explored_fraction
            ),
            "cumulative_reward": float(
                sum(
                    record.total_reward
                    for record in self.history
                )
            ),
            "cumulative_new_cells": int(
                sum(
                    record.newly_explored_cells
                    for record in self.history
                )
            ),
            "total_drone_collisions": int(
                sum(
                    record.drone_collisions
                    for record in self.history
                )
            ),
            "total_obstacle_collisions": int(
                sum(
                    record.obstacle_collisions
                    for record in self.history
                )
            ),
            "total_targets_found": int(
                sum(
                    record.targets_found
                    for record in self.history
                )
            ),
            "total_boundary_violations": int(
                sum(
                    record.boundary_violations
                    for record in self.history
                )
            ),
        }

    def summary_json(self) -> str:
        """Encode overall metric summary as JSON."""
        return json.dumps(self.summary())


def build_agent_metrics(
    reward: float = 0.0,
    new_cells: int = 0,
    sensor_summary: dict[str, Any] | None = None,
    event_flags: dict[str, bool] | None = None,
) -> AgentMetrics:
    """Build agent metrics from sensor and event data."""
    sensor_summary = sensor_summary or {}
    event_flags = event_flags or {}

    return AgentMetrics(
        reward=float(reward),
        new_cells=int(new_cells),
        visible_targets=int(
            sensor_summary.get("visible_targets", 0)
        ),
        visible_obstacles=int(
            sensor_summary.get("visible_obstacles", 0)
        ),
        visible_drones=int(
            sensor_summary.get("visible_drones", 0)
        ),
        drone_collision=bool(
            event_flags.get("drone_collision", False)
        ),
        obstacle_collision=bool(
            event_flags.get("obstacle_collision", False)
        ),
        target_found=bool(
            event_flags.get("target_found", False)
        ),
        boundary_violation=bool(
            event_flags.get("boundary_violation", False)
        ),
    )


def metrics_from_payload(
    payload: dict[str, Any],
    episode: int = 0,
) -> SwarmMetrics:
    """Build SwarmMetrics from a JSON-friendly swarm payload."""
    if "step" not in payload:
        raise ValueError("Payload must contain step.")

    agents = payload.get("agents", [])
    agent_metrics: dict[str, AgentMetrics] = {}

    for agent in agents:
        agent_id = agent.get("agent_id")

        if not agent_id:
            raise ValueError(
                "Every agent payload must contain agent_id."
            )

        agent_metrics[agent_id] = build_agent_metrics(
            reward=agent.get("reward", 0.0),
            new_cells=agent.get(
                "reward_components",
                {},
            ).get("new_area", 0),
            sensor_summary=agent,
            event_flags=agent.get("event_flags", {}),
        )

    return SwarmMetrics(
        step=int(payload["step"]),
        episode=episode,
        explored_fraction=float(
            payload.get("map", {}).get(
                "explored_fraction",
                0.0,
            )
        ),
        agent_metrics=agent_metrics,
    )