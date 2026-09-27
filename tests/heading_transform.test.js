const test = require('node:test');
const assert = require('node:assert/strict');

/**
 * Transforms a heading angle (radians) into a Three.js Y-rotation.
 * Heading 0 rad = [1, 0, 0] (+X axis) in horizontal X-Z plane.
 * Three.js default mesh forward is +Z [0, 0, 1].
 */
function headingToThreeRotationY(heading) {
  return -heading + Math.PI / 2;
}

/**
 * Computes 3D forward vector for Three.js mesh rotated by rotationY around +Y.
 */
function computeThreeForwardVector(rotationY) {
  return [
    Math.sin(rotationY),
    0.0,
    Math.cos(rotationY),
  ];
}

/**
 * Computes Saju's ConeSensor forward heading direction vector.
 * In sensors/sensors.py: sensor_dir = [cos(heading), 0.0, sin(heading)]
 */
function computeConeSensorDirection(heading) {
  return [
    Math.cos(heading),
    0.0,
    Math.sin(heading),
  ];
}

test('Heading Transform Alignment: Physics ConeSensor vs Three.js Render Layer', async (t) => {
  const testHeadings = [
    { name: '0 rad (+X / East)', heading: 0.0 },
    { name: 'pi/4 rad (+X,+Z / South-East)', heading: Math.PI / 4 },
    { name: 'pi/2 rad (+Z / South)', heading: Math.PI / 2 },
    { name: '3*pi/4 rad (-X,+Z / South-West)', heading: (3 * Math.PI) / 4 },
    { name: 'pi rad (-X / West)', heading: Math.PI },
    { name: '-pi/2 rad (-Z / North)', heading: -Math.PI / 2 },
    { name: '-pi/4 rad (+X,-Z / North-East)', heading: -Math.PI / 4 },
  ];

  for (const { name, heading } of testHeadings) {
    await t.test(`verifies alignment for ${name}`, () => {
      const sensorDir = computeConeSensorDirection(heading);
      const rotY = headingToThreeRotationY(heading);
      const renderDir = computeThreeForwardVector(rotY);

      // Verify X, Y, Z components match within floating-point tolerance
      assert.ok(
        Math.abs(sensorDir[0] - renderDir[0]) < 1e-6,
        `X mismatch for ${name}: sensor=${sensorDir[0]}, render=${renderDir[0]}`
      );
      assert.ok(
        Math.abs(sensorDir[1] - renderDir[1]) < 1e-6,
        `Y mismatch for ${name}: sensor=${sensorDir[1]}, render=${renderDir[1]}`
      );
      assert.ok(
        Math.abs(sensorDir[2] - renderDir[2]) < 1e-6,
        `Z mismatch for ${name}: sensor=${sensorDir[2]}, render=${renderDir[2]}`
      );

      // Cosine similarity / dot product between sensor direction and render forward must be 1.0
      const dotProduct =
        sensorDir[0] * renderDir[0] +
        sensorDir[1] * renderDir[1] +
        sensorDir[2] * renderDir[2];

      assert.ok(
        Math.abs(dotProduct - 1.0) < 1e-6,
        `Direction vectors are not colinear: dot=${dotProduct}`
      );
    });
  }
});
