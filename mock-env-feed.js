const WebSocket = require('ws');
const { createTelemetryFrame } = require('./schema');

const NUM_AGENTS = 50;
const STEP_INTERVAL_MS = 200;
const RECONNECT_DELAY_MS = 2000;

let ws;
let agents = [];
let stepCount = 0;
let stepTimer = null;

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

function connect() {
  ws = new WebSocket('ws://localhost:8080');

  ws.on('open', () => {
    console.log('Mock env feed connected.');
    resetEnv();

    stepTimer = setInterval(() => {
      const updatedAgents = stepEnv();
      const batchMsg = {
        type: 'batch_update',
        step: stepCount,
        timestamp: Date.now(),
        agents: updatedAgents.map(a => ({
          id: a.id,
          x: Math.round(a.x * 100) / 100,
          y: Math.round(a.y * 100) / 100,
          z: Math.round(a.z * 100) / 100,
        })),
      };
      ws.send(JSON.stringify(batchMsg));
      console.log(`Step ${stepCount}: sent batch (${updatedAgents.length} agents)`);
    }, STEP_INTERVAL_MS);
  });

  ws.on('close', () => {
    console.log(`Disconnected. Reconnecting in ${RECONNECT_DELAY_MS}ms...`);
    clearInterval(stepTimer);
    setTimeout(connect, RECONNECT_DELAY_MS);
  });

  ws.on('error', (err) => {
    console.error('Mock env feed error:', err.message);
  });
}

connect();
