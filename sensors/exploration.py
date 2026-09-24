from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ExplorationConfig:
    """Configuration for the explored-area grid."""

    world_size: tuple[float, float] = (100.0, 100.0)
    cell_size: float = 2.0
    exploration_radius: float = 2.0

    def __post_init__(self) -> None:
        if len(self.world_size) != 2:
            raise ValueError(
                "world_size must contain width and depth."
            )

        if any(size <= 0 for size in self.world_size):
            raise ValueError(
                "World dimensions must be positive."
            )

        if self.cell_size <= 0:
            raise ValueError(
                "Cell size must be positive."
            )

        if self.exploration_radius <= 0:
            raise ValueError(
                "Exploration radius must be positive."
            )

        if any(
            not np.isfinite(size)
            for size in self.world_size
        ):
            raise ValueError(
                "World dimensions must be finite."
            )


@dataclass(frozen=True)
class ExplorationSummary:
    """Summary of one exploration update."""

    newly_explored_cells: int
    total_explored_cells: int
    total_cells: int
    explored_fraction: float

    def to_dict(self) -> dict[str, float | int]:
        """Return a JSON-friendly summary."""
        return {
            "newly_explored_cells": int(
                self.newly_explored_cells
            ),
            "total_explored_cells": int(
                self.total_explored_cells
            ),
            "total_cells": int(self.total_cells),
            "explored_fraction": float(
                self.explored_fraction
            ),
        }


class ExplorationMap:
    """Track explored x-z map cells for the drone swarm."""

    def __init__(
        self,
        world_size: tuple[float, float] = (100.0, 100.0),
        cell_size: float = 2.0,
        exploration_radius: float = 2.0,
        config: ExplorationConfig | None = None,
    ):
        if config is not None:
            if (
                world_size != (100.0, 100.0)
                or cell_size != 2.0
                or exploration_radius != 2.0
            ):
                raise ValueError(
                    "Use either config or individual parameters."
                )

            self.config = config
        else:
            self.config = ExplorationConfig(
                world_size=world_size,
                cell_size=cell_size,
                exploration_radius=exploration_radius,
            )

        self.width = int(
            np.ceil(
                self.config.world_size[0]
                / self.config.cell_size
            )
        )
        self.height = int(
            np.ceil(
                self.config.world_size[1]
                / self.config.cell_size
            )
        )

        self.grid = np.zeros(
            (self.width, self.height),
            dtype=np.bool_,
        )

    @property
    def total_cells(self) -> int:
        """Return the total number of cells."""
        return int(self.grid.size)

    @property
    def total_explored_cells(self) -> int:
        """Return the number of explored cells."""
        return int(self.grid.sum())

    @property
    def explored_fraction(self) -> float:
        """Return explored cells divided by all cells."""
        if self.total_cells == 0:
            return 0.0

        return float(
            self.total_explored_cells / self.total_cells
        )

    def reset(self) -> None:
        """Clear the entire explored grid."""
        self.grid.fill(False)

    def _validate_position(
        self,
        position: np.ndarray | list[float],
    ) -> np.ndarray:
        """Validate a three-dimensional position."""
        result = np.asarray(position, dtype=np.float32)

        if result.shape != (3,):
            raise ValueError(
                "Position must contain x, y, and z."
            )

        if not np.all(np.isfinite(result)):
            raise ValueError(
                "Position values must be finite."
            )

        return result

    def _cell(
        self,
        position: np.ndarray | list[float],
    ) -> tuple[int, int] | None:
        """Convert an x-y-z position into an x-z grid cell."""
        validated = self._validate_position(position)

        x = float(validated[0])
        z = float(validated[2])

        column = int(
            np.floor(
                (
                    x + self.config.world_size[0] / 2
                ) / self.config.cell_size
            )
        )
        row = int(
            np.floor(
                (
                    z + self.config.world_size[1] / 2
                ) / self.config.cell_size
            )
        )

        if not (
            0 <= column < self.width
            and 0 <= row < self.height
        ):
            return None

        return column, row

    def _cell_center(
        self,
        column: int,
        row: int,
    ) -> tuple[float, float]:
        """Return the x-z center of a grid cell."""
        x = (
            -self.config.world_size[0] / 2
            + (column + 0.5) * self.config.cell_size
        )
        z = (
            -self.config.world_size[1] / 2
            + (row + 0.5) * self.config.cell_size
        )

        return x, z

    def _cells_near_position(
        self,
        position: np.ndarray | list[float],
        radius: float,
    ) -> set[tuple[int, int]]:
        """Return the current cell plus nearby cells."""
        if radius <= 0:
            raise ValueError(
                "Exploration radius must be positive."
            )

        validated = self._validate_position(position)
        current_cell = self._cell(validated)

        if current_cell is None:
            return set()

        current_column, current_row = current_cell
        cells = {
            current_cell,
        }

        cell_radius = int(
            np.ceil(radius / self.config.cell_size)
        )

        for dx in range(-cell_radius, cell_radius + 1):
            for dy in range(-cell_radius, cell_radius + 1):
                column = current_column + dx
                row = current_row + dy

                if not (
                    0 <= column < self.width
                    and 0 <= row < self.height
                ):
                    continue

                if (column, row) == current_cell:
                    continue

                cell_x, cell_z = self._cell_center(
                    column,
                    row,
                )

                distance = float(
                    np.sqrt(
                        (cell_x - validated[0]) ** 2
                        + (cell_z - validated[2]) ** 2
                    )
                )

                if distance <= radius:
                    cells.add((column, row))

        return cells

    def mark_explored(
        self,
        positions: list[np.ndarray | list[float]],
        radius: float | None = None,
    ) -> int:
        """Mark cells near all positions and return new-cell count."""
        exploration_radius = (
            self.config.exploration_radius
            if radius is None
            else radius
        )

        cells_before = self.total_explored_cells

        for position in positions:
            cells = self._cells_near_position(
                position,
                exploration_radius,
            )

            for column, row in cells:
                self.grid[column, row] = True

        cells_after = self.total_explored_cells

        return cells_after - cells_before

    def mark_explored_by_agent(
        self,
        positions: dict[
            str,
            np.ndarray | list[float],
        ],
        radius: float | None = None,
    ) -> dict[str, int]:
        """Mark cells and assign new cells to agents."""
        exploration_radius = (
            self.config.exploration_radius
            if radius is None
            else radius
        )

        newly_explored_by_agent: dict[str, int] = {}

        for agent_id, position in positions.items():
            cells = self._cells_near_position(
                position,
                exploration_radius,
            )

            new_for_agent = 0

            for column, row in cells:
                if not self.grid[column, row]:
                    self.grid[column, row] = True
                    new_for_agent += 1

            newly_explored_by_agent[agent_id] = new_for_agent

        return newly_explored_by_agent

    def update(
        self,
        positions: list[np.ndarray | list[float]],
        radius: float | None = None,
    ) -> ExplorationSummary:
        """Mark positions and return a coverage summary."""
        newly_explored = self.mark_explored(
            positions=positions,
            radius=radius,
        )

        return ExplorationSummary(
            newly_explored_cells=newly_explored,
            total_explored_cells=self.total_explored_cells,
            total_cells=self.total_cells,
            explored_fraction=self.explored_fraction,
        )

    def mark_explored_per_agent(
        self,
        agent_positions: dict[
            str,
            np.ndarray | list[float],
        ],
        radius: float | None = None,
    ) -> tuple[dict[str, int], int]:
        """Mark cells symmetrically for all agents and return per-agent and total counts."""
        exploration_radius = (
            self.config.exploration_radius
            if radius is None
            else radius
        )

        agent_new_cells: dict[str, int] = {
            agent_id: 0 for agent_id in agent_positions
        }
        cells_to_mark: set[tuple[int, int]] = set()

        for agent_id, position in agent_positions.items():
            cells = self._cells_near_position(
                position,
                exploration_radius,
            )
            for column, row in cells:
                if not self.grid[column, row]:
                    agent_new_cells[agent_id] += 1
                    cells_to_mark.add((column, row))

        for column, row in cells_to_mark:
            self.grid[column, row] = True

        return agent_new_cells, len(cells_to_mark)

    def get_local_patch(
        self,
        position: np.ndarray | list[float],
        radius_cells: int = 2,
    ) -> np.ndarray:
        """Extract a square local grid patch centered on the agent's cell."""
        cell = self._cell(position)
        side = 2 * radius_cells + 1
        patch = np.zeros((side, side), dtype=np.float32)

        if cell is None:
            return patch

        center_col, center_row = cell
        for dx in range(-radius_cells, radius_cells + 1):
            for dy in range(-radius_cells, radius_cells + 1):
                col = center_col + dx
                row = center_row + dy
                if 0 <= col < self.width and 0 <= row < self.height:
                    if self.grid[col, row]:
                        patch[dx + radius_cells, dy + radius_cells] = 1.0

        return patch

    def as_array(self) -> np.ndarray:
        """Return the grid as a float array for rendering or RL."""
        return self.grid.astype(np.float32)

    def as_list(self) -> list[list[int]]:
        """Return the grid as nested integer lists."""
        return self.grid.astype(np.int8).tolist()