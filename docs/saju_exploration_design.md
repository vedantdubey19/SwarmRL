# Saju Exploration Map Design

## Owner

Saju

## Day 6 objective

Track which parts of the search area have been explored and expose
coverage data to the reward system, training code, WebSocket layer, and
frontend.

## Coordinate convention

Drone positions use:

```text
[x, y, z]
```

The exploration map uses:

- x as the horizontal world axis.
- z as the depth world axis.
- y as altitude, ignored for ground-map cell selection.

## Grid configuration

Default values:

- World width: 100 units.
- World depth: 100 units.
- Cell size: 2 units.
- Exploration radius: 2 units.
- Grid size: 50 × 50 cells.
- Total cells: 2500.

## Main outputs

The map provides:

- Newly explored cells.
- Total explored cells.
- Total cell count.
- Explored fraction.
- Boolean grid.
- JSON-friendly integer grid.
- Per-agent newly explored-cell counts.

## Important behavior

- A cell is counted as new only the first time it is marked.
- Repeated visits do not increase the count.
- Multiple drones visiting the same new cell in one update are credited
  to the first agent in the input order.
- Positions outside the world do not mark cells.
- Altitude does not change the x-z ground cell.
- `reset()` clears the entire map.

## Reward integration

The exploration reward can use:

```python
new_cells = exploration_map.mark_explored(...)
```

For per-agent rewards:

```python
new_cells_by_agent = (
    exploration_map.mark_explored_by_agent(...)
)
```

## Frontend integration

The frontend can use:

```python
exploration_map.as_list()
```

for a JSON-friendly grid, or:

```python
exploration_map.as_array()
```

for numerical processing.