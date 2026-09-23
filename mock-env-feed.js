const WebSocket = require('ws');
const { createTelemetryFrame } = require('./schema');

const NUM_AGENTS = 50;
const STEP_INTERVAL_MS = 40; // 25 Hz
const WS_URL = process.env.WS_URL || 'ws://localhost:8080';

const ws = new WebSocket(WS_URL);

let stepCount = 0;
let drones = [];

function resetEnv() {
  stepCount = 0;
  drones = Array.from({ length: NUM_AGENTS }, (_, i) => {
    const angle = (i / NUM_AGENTS) * Math.PI * 2;
    const r = 20.0 + (i % 5) * 3.0;
    return {
      id: i,
      agent_id: `drone_${i}`,
      pos: [Math.cos(angle) * r, 5.0, Math.sin(angle) * r],
      vel: [0.0, 0.0, 0.0],
      heading: angle,
      rot: [0.0, 0.0, 0.0, 1.0],
      status: 'active',
      detections: [],
    };
  });
}

function stepEnv() {
  stepCount += 1;
  drones = drones.map(drone => {
    const vx = (Math.random() - 0.5) * 2.0;
    const vy = (Math.random() - 0.5) * 0.5;
    const vz = (Math.random() - 0.5) * 2.0;
    const heading = (drone.heading + (Math.random() - 0.5) * 0.1) % (Math.PI * 2);

    return {
      ...drone,
      pos: [
        Math.max(-48, Math.min(48, drone.pos[0] + vx)),
        Math.max(1, Math.min(18, drone.pos[1] + vy)),
        Math.max(-48, Math.min(48, drone.pos[2] + vz)),
      ],
      vel: [vx, vy, vz],
      heading,
    };
  });
}

ws.on('open', () => {
  console.log(`Mock env feed connected to ${WS_URL}. Registering as publisher...`);
  ws.send(JSON.stringify({ type: 'register', role: 'publisher' }));

  resetEnv();

  setInterval(() => {
    stepEnv();

    const frame = createTelemetryFrame({
      step: stepCount,
      timestamp: Date.now(),
      sim_time: stepCount * 0.04,
      metrics: {
        explored_fraction: Math.min(1.0, stepCount * 0.001),
        active_drones: NUM_AGENTS,
        targets_found: 1,
        total_targets: 5,
        step_reward_sum: 5.2,
      },
      drones,
      targets: [
        { id: 0, pos: [12.0, 0.5, -8.0], found: true, discovered_by: 'drone_0' },
      ],
    });

    ws.send(JSON.stringify(frame));
  }, STEP_INTERVAL_MS);
});

ws.on('error', (err) => console.error('Mock env feed error:', err.message));
ws.on('close', () => console.log('Mock env feed disconnected'));