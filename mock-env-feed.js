const WebSocket = require('ws');
const { createAgentMessage } = require('./schema');

const NUM_AGENTS = 50; // matches world bounds/agent count from Day 5 env spec
const TICK_RATE_MS = 200; // how often to send updated positions

const ws = new WebSocket('ws://localhost:8080');

let agents = Array.from({ length: NUM_AGENTS }, (_, i) => ({
  id: `drone-${i + 1}`,
  x: Math.random() * 100,
  y: Math.random() * 100,
  z: Math.random() * 20,
}));

function stepMockEnv() {
  agents = agents.map(agent => ({
    ...agent,
    x: agent.x + (Math.random() - 0.5) * 2,
    y: agent.y + (Math.random() - 0.5) * 2,
    z: Math.max(0, agent.z + (Math.random() - 0.5) * 1),
  }));
}

ws.on('open', () => {
  console.log(`Mock env feed connected. Streaming ${NUM_AGENTS} agents every ${TICK_RATE_MS}ms`);

  setInterval(() => {
    stepMockEnv();
    agents.forEach(agent => {
      const msg = createAgentMessage(agent);
      ws.send(JSON.stringify(msg));
    });
  }, TICK_RATE_MS);
});

ws.on('error', (err) => console.error('Mock env feed error:', err.message));
ws.on('close', () => console.log('Mock env feed disconnected'));