const WebSocket = require('ws');
const { createAgentMessage } = require('./schema');

const NUM_AGENTS = 50;
const STEP_INTERVAL_MS = 200;

const ws = new WebSocket('ws://localhost:8080');

let agents = [];
let stepCount = 0;

function resetEnv() {
  stepCount = 0;
  agents = Array.from({ length: NUM_AGENTS }, (_, i) => ({
    id: `drone-${i + 1}`,
    x: Math.random() * 100,
    y: Math.random() * 100,
    z: Math.random() * 20,
  }));
  console.log('Mock env reset. Initial agent positions generated.');
}

function stepEnv() {
  stepCount += 1;
  agents = agents.map(agent => ({
    ...agent,
    x: agent.x + (Math.random() - 0.5) * 2,
    y: agent.y + (Math.random() - 0.5) * 2,
    z: Math.max(0, agent.z + (Math.random() - 0.5) * 1),
  }));
  return agents;
}

ws.on('open', () => {
  console.log(`Mock env feed connected. Wiring per-step coordinates every ${STEP_INTERVAL_MS}ms`);
  resetEnv();

  setInterval(() => {
    const updatedAgents = stepEnv();
    updatedAgents.forEach(agent => {
      const msg = createAgentMessage(agent);
      ws.send(JSON.stringify(msg));
    });
    console.log(`Step ${stepCount}: sent ${updatedAgents.length} agent positions`);
  }, STEP_INTERVAL_MS);
});

ws.on('error', (err) => console.error('Mock env feed error:', err.message));
ws.on('close', () => console.log('Mock env feed disconnected'));