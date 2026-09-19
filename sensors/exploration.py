import numpy as np


class ExplorationMap:
    """Track explored cells in the drone search area."""

    def __init__(
        self,
        world_size: tuple[float, float] = (100.0, 100.0),
        cell_size: float = 2.0,
    ):
        self.world_size = world_size
        self.cell_size = cell_size

        self.width = int(np.ceil(world_size[0] / cell_size))
        self.height = int(np.ceil(world_size[1] / cell_size))

        self.grid = np.zeros(
            (self.width, self.height),
            dtype=np.bool_,
        )

    def reset(self) -> None:
        self.grid.fill(False)

    def _cell(
        self,
        position: np.ndarray,
    ) -> tuple[int, int] | None:
        x = float(position[0])
        z = float(position[2])

        column = int(
            (x + self.world_size[0] / 2) / self.cell_size
        )
        row = int(
            (z + self.world_size[1] / 2) / self.cell_size
        )

        if not (
            0 <= column < self.width
            and 0 <= row < self.height
        ):
            return None

        return column, row

    def mark_explored(
        self,
        positions: list[np.ndarray],
        radius: float = 2.0,
    ) -> int:
        before = int(self.grid.sum())
        cell_radius = int(np.ceil(radius / self.cell_size))

        for position in positions:
            cell = self._cell(np.asarray(position))

            if cell is None:
                continue

            center_x, center_y = cell

            for dx in range(-cell_radius, cell_radius + 1):
                for dy in range(-cell_radius, cell_radius + 1):
                    x = center_x + dx
                    y = center_y + dy

                    if 0 <= x < self.width and 0 <= y < self.height:
                        self.grid[x, y] = True

        after = int(self.grid.sum())

        return after - before

    def mark_explored_per_agent(
        self,
        agent_positions: dict[str, np.ndarray],
        radius: float = 2.0,
    ) -> tuple[dict[str, int], int]:
        """Mark explored cells for each agent simultaneously.

        Returns a tuple of:
          - dict mapping agent_id to newly explored cell count attributed to that agent
          - total new cells marked across the entire swarm

        Symmetrically attributes newly covered cells: if multiple agents cover
        the same previously-unexplored cell in the same timestep, all contributing
        agents receive credit, avoiding order-dependent race conditions.
        """
        cell_radius = int(np.ceil(radius / self.cell_size))
        agent_new_cells: dict[str, int] = {
            agent_id: 0 for agent_id in agent_positions
        }
        cells_to_mark: set[tuple[int, int]] = set()

        for agent_id, position in agent_positions.items():
            cell = self._cell(np.asarray(position))
            if cell is None:
                continue

            center_x, center_y = cell
            for dx in range(-cell_radius, cell_radius + 1):
                for dy in range(-cell_radius, cell_radius + 1):
                    x = center_x + dx
                    y = center_y + dy
                    if 0 <= x < self.width and 0 <= y < self.height:
                        if not self.grid[x, y]:
                            agent_new_cells[agent_id] += 1
                            cells_to_mark.add((x, y))

        for x, y in cells_to_mark:
            self.grid[x, y] = True

        total_new = len(cells_to_mark)
        return agent_new_cells, total_new

    @property
    def explored_fraction(self) -> float:
        return float(self.grid.mean())

    def as_array(self) -> np.ndarray:
        return self.grid.astype(np.float32)