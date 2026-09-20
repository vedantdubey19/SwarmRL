const { test, describe } = require('node:test');
const assert = require('node:assert');

const {
  SCHEMA_VERSION,
  createDroneState,
  isValidDroneState,
  createTelemetryFrame,
  isValidTelemetryFrame,
  createGridDeltaMessage,
  isValidGridDeltaMessage,
  createControlMessage,
  isValidControlMessage,
  createRegisterMessage,
  isValidRegisterMessage,
  createAgentMessage,
  isValidAgentMessage,
} = require('../schema');

describe('WebSocket Telemetry Schema Unit Tests', () => {
  test('creates and validates a single drone state', () => {
    const drone = createDroneState({
      id: 0,
      pos: [10.5, 2.0, -15.2],
      vel: [1.0, 0.0, -0.5],
      heading: 1.57,
      rot: [0, 0.707, 0, 0.707],
      status: 'active',
      detections: [{ id: 'target_1', type: 'target', dist: 5.5, angle: 0.1 }],
    });

    assert.strictEqual(drone.id, 0);
    assert.strictEqual(drone.agent_id, 'drone_0');
    assert.strictEqual(isValidDroneState(drone), true);
  });

  test('rejects invalid drone states', () => {
    // Missing position
    assert.strictEqual(isValidDroneState({ id: 1 }), false);
    // Position has non-numbers
    assert.strictEqual(isValidDroneState({ id: 1, pos: ['1', 2, 3] }), false);
    // Position has wrong length
    assert.strictEqual(isValidDroneState({ id: 1, pos: [1, 2] }), false);
    // Invalid status
    assert.strictEqual(
      isValidDroneState({ id: 1, pos: [0, 0, 0], status: 'exploding' }),
      false
    );
    // Invalid detection item
    assert.strictEqual(
      isValidDroneState({
        id: 1,
        pos: [0, 0, 0],
        detections: [{ id: 'bad', type: 'target', dist: 'five', angle: 0 }],
      }),
      false
    );
  });

  test('creates and validates an atomic 50-drone telemetry frame', () => {
    const drones = Array.from({ length: 50 }, (_, i) =>
      createDroneState({
        id: i,
        pos: [i * 1.5, 5.0, -i * 1.2],
        vel: [0.5, 0.0, -0.5],
        heading: 0.785,
        status: i === 49 ? 'collided_obstacle' : 'active',
      })
    );

    const targets = [
      { id: 0, pos: [25.0, 0.5, 18.0], found: true },
      { id: 1, pos: [-10.0, 0.5, -20.0], found: false },
    ];

    const frame = createTelemetryFrame({
      step: 1420,
      timestamp: 1726501234.567,
      sim_time: 71.0,
      metrics: {
        explored_fraction: 0.642,
        active_drones: 49,
        step_reward_sum: 12.4,
      },
      drones,
      targets,
    });

    assert.strictEqual(frame.version, SCHEMA_VERSION);
    assert.strictEqual(frame.type, 'frame');
    assert.strictEqual(frame.drones.length, 50);
    assert.strictEqual(isValidTelemetryFrame(frame), true);
  });

  test('rejects corrupt telemetry frames', () => {
    // Missing step
    assert.strictEqual(
      isValidTelemetryFrame({ type: 'frame', timestamp: Date.now(), drones: [] }),
      false
    );
    // Negative step
    assert.strictEqual(
      isValidTelemetryFrame({
        type: 'frame',
        step: -5,
        timestamp: Date.now(),
        drones: [],
      }),
      false
    );
    // Drones not an array
    assert.strictEqual(
      isValidTelemetryFrame({
        type: 'frame',
        step: 10,
        timestamp: Date.now(),
        drones: 'none',
      }),
      false
    );
    // Drones containing invalid entry
    assert.strictEqual(
      isValidTelemetryFrame({
        type: 'frame',
        step: 10,
        timestamp: Date.now(),
        drones: [{ id: 'drone_0', pos: [1, 2] }], // only 2 coordinates
      }),
      false
    );
  });

  test('creates and validates sparse grid delta messages', () => {
    const delta = createGridDeltaMessage({
      step: 1420,
      new_cells: [
        [14, 22],
        [14, 23],
        [15, 22],
      ],
    });

    assert.strictEqual(delta.type, 'grid_delta');
    assert.strictEqual(delta.new_cells.length, 3);
    assert.strictEqual(isValidGridDeltaMessage(delta), true);

    // Rejection on malformed cells
    assert.strictEqual(
      isValidGridDeltaMessage({
        type: 'grid_delta',
        step: 10,
        new_cells: [[14]], // missing row
      }),
      false
    );
  });

  test('creates and validates simulation control messages', () => {
    const control = createControlMessage({
      action: 'pause',
      params: {},
    });

    assert.strictEqual(control.type, 'control');
    assert.strictEqual(isValidControlMessage(control), true);

    // Invalid action
    assert.strictEqual(
      isValidControlMessage({ type: 'control', action: 'destroy_all' }),
      false
    );
  });

  test('creates and validates client registration messages', () => {
    const pub = createRegisterMessage({ role: 'publisher' });
    const sub = createRegisterMessage({ role: 'subscriber' });

    assert.strictEqual(isValidRegisterMessage(pub), true);
    assert.strictEqual(isValidRegisterMessage(sub), true);
    assert.strictEqual(
      isValidRegisterMessage({ type: 'register', role: 'admin' }),
      false
    );
  });

  test('retains backward compatibility for legacy single-agent messages', () => {
    const legacy = createAgentMessage({ id: 'drone-1', x: 1.0, y: 2.0, z: 3.0 });
    assert.strictEqual(isValidAgentMessage(legacy), true);
    assert.strictEqual(
      isValidAgentMessage({ id: 'drone-bad', x: 'invalid' }),
      false
    );
  });
});
