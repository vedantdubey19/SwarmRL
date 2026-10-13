const assert = require('assert');
const { LEVELS, difficultyScore, validateCurriculum, levelForStep } = require('./curriculum');

assert.deepStrictEqual(validateCurriculum(LEVELS), []);
assert.ok(validateCurriculum([{ level: 1, obstacles: 3, radius: 3, wind: 0 }, { level: 2, obstacles: 3, radius: 3, wind: 0 }]).length > 0, 'flat difficulty must fail');
assert.ok(validateCurriculum([{ level: 1, obstacles: 3, radius: -1, wind: 0 }]).length > 0, 'negative radius must fail');
assert.ok(validateCurriculum([{ level: 1, obstacles: 'x', radius: 3, wind: 0 }]).length > 0, 'non-number must fail');

const scores = LEVELS.map(difficultyScore);
for (let i = 1; i < scores.length; i++) assert.ok(scores[i] > scores[i - 1], `level ${i + 1} not harder`);

assert.strictEqual(levelForStep(1, 100).level, 1);
assert.strictEqual(levelForStep(100, 100).level, 1);
assert.strictEqual(levelForStep(101, 100).level, 2);
assert.strictEqual(levelForStep(10 ** 6, 100).level, LEVELS.length);
console.log('curriculum: all tests passed');