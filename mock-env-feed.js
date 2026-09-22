const WebSocket = require('ws');

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
  console.log(`Mock env feed connected. Streaming batched steps every ${STEP_INTERVAL_MS}ms`);
  resetEnv();

  setInterval(() => {
    const updatedAgents = stepEnv();

    // Batch all agents into a single message instead of separate sends per agent
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

    const serialized = JSON.stringify(batchMsg);
    ws.send(serialized);
    console.log(`Step ${stepCount}: sent 1 batched message (${serialized.length} bytes, ${updatedAgents.length} agents)`);
  }, STEP_INTERVAL_MS);
});

ws.on('error', (err) => console.error('Mock env feed error:', err.message));
ws.on('close', () => console.log('Mock env feed disconnected'));