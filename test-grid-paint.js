const assert = require('assert');
const { GridPaint } = require('./grid-paint');

const g = new GridPaint(10, 100);

// two agents in the same cell -> one delta entry
let d = g.update([{ id: 'a', x: 5, y: 5 }, { id: 'b', x: 6, y: 7 }]);
assert.strictEqual(d.length, 1, 'same cell should paint once');

// same positions again -> nothing new
d = g.update([{ id: 'a', x: 5, y: 5 }]);
assert.strictEqual(d.length, 0, 'repainting a cell must not create a delta');

// out-of-range positions clamp to edge cells instead of crashing
d = g.update([{ id: 'c', x: -20, y: 500 }]);
assert.strictEqual(d.length, 1);
assert.deepStrictEqual([d[0].ix, d[0].iy], [0, 9]);

// percentage: 2 of 100 cells
assert.strictEqual(g.percentExplored, 2);

// snapshot returns every explored cell exactly once
const snap = g.snapshot();
assert.strictEqual(snap.length, 2);
assert.ok(snap.some((c) => c.ix === 0 && c.iy === 9));

g.reset();
assert.strictEqual(g.percentExplored, 0);
assert.strictEqual(g.snapshot().length, 0);
console.log('grid-paint: all tests passed');