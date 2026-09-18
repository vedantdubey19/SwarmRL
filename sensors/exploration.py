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

    @property
    def explored_fraction(self) -> float:
        return float(self.grid.mean())

    def as_array(self) -> np.ndarray:
        return self.grid.astype(np.float32)