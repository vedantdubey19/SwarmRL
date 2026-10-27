// Tracks which map cells have been "painted" (explored) by the swarm.
class GridPaint {
  constructor(cells = 20, worldSize = 100) {
    this.cells = cells;
    this.worldSize = worldSize;
    this.explored = new Set();
  }

  cellOf(x, y) {
    const clamp = (v) =>
      Math.min(this.cells - 1, Math.max(0, Math.floor((v / this.worldSize) * this.cells)));
    return { ix: clamp(x), iy: clamp(y) };
  }

  // Returns only the cells painted for the first time this step (the "delta").
  update(agents) {
    const fresh = [];
    for (const a of agents) {
      const { ix, iy } = this.cellOf(a.x, a.y);
      const key = ix * this.cells + iy;
      if (!this.explored.has(key)) {
        this.explored.add(key);
        fresh.push({ ix, iy, by: a.id });
      }
    }
    return fresh;
  }

  get percentExplored() {
    return Math.round((this.explored.size / (this.cells * this.cells)) * 1000) / 10;
  }

  // Every explored cell, so a late-joining client can rebuild the whole map.
  snapshot() {
    return [...this.explored].map((key) => ({
      ix: Math.floor(key / this.cells),
      iy: key % this.cells,
    }));
  }

  reset() {
    this.explored.clear();
  }
}

module.exports = { GridPaint };