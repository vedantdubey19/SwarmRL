const assert = require('assert');
const { windForce, applyWind } = require('./wind');

const agents = [{ id: 'a', x: 10, y: 10, z: 5 }];
assert.deepStrictEqual(applyWind(agents, 42, 0), agents);
assert.deepStrictEqual(windForce(17, 0.5), windForce(17, 0.5));

for (let s = 0; s < 2000; s++) {
  const { dx, dy } = windForce(s, 1);
  assert.ok(Math.abs(dx) <= 1.5 + 1e-9 && Math.abs(dy) <= 1.5 + 1e-9);
}

let sx = 0, sy = 0;
for (let s = 0; s < 1000; s++) {
  const { dx, dy } = windForce(s, 1);
  sx += dx; sy += dy;
}
assert.ok(Math.abs(sx / 1000) < 0.3 && Math.abs(sy / 1000) < 0.3, 'wind should not drift one way');

const weak = applyWind(agents, 10, 0.2)[0];
const strong = applyWind(agents, 10, 0.8)[0];
assert.ok(Math.abs(strong.x - 10) > Math.abs(weak.x - 10));
console.log('wind: all tests passed');