const assert = require('assert');
const { createObstacles, findCollisions } = require('./obstacles');

const cfg = { level: 2, obstacles: 6, radius: 3.5, wind: 0.2 };
const a = createObstacles(cfg);
const b = createObstacles(cfg);
assert.strictEqual(a.length, 6);
assert.deepStrictEqual(a, b, 'same level must give the same obstacles');
assert.notDeepStrictEqual(a, createObstacles({ ...cfg, level: 3 }), 'levels must differ');

const o = [{ id: 'o1', x: 50, y: 50, z: 10, r: 3 }];
const hits = findCollisions(
  [
    { id: 'inside', x: 51, y: 50, z: 10 },
    { id: 'outside', x: 60, y: 50, z: 10 },
    { id: 'edge', x: 53, y: 50, z: 10 },
  ],
  o
);
assert.deepStrictEqual(hits, ['inside']);
console.log('obstacles: all tests passed');