const assert = require('assert');
const { GridPaint } = require('./grid-paint');

const g = new GridPaint(10, 100);

let d = g.update([{ id: 'a', x: 5, y: 5 }, { id: 'b', x: 6, y: 7 }]);
assert.strictEqual(d.length, 1, 'same cell should paint once');

d = g.update([{ id: 'a', x: 5, y: 5 }]);
assert.strictEqual(d.length, 0, 'repainting a cell must not create a delta');

d = g.update([{ id: 'c', x: -20, y: 500 }]);
assert.strictEqual(d.length, 1);
assert.deepStrictEqual([d[0].ix, d[0].iy], [0, 9]);

assert.strictEqual(g.percentExplored, 2);

g.reset();
assert.strictEqual(g.percentExplored, 0);
console.log('grid-paint: all tests passed');