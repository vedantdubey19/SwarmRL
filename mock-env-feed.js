const WebSocket = require('ws');

const NUM_AGENTS = 50;
const STEP_INTERVAL_MS = 200;
const RECONNECT_DELAY_MS = 2000;

let ws;
let agents = [];
let stepCount = 0;
let stepTimer = null;

function resetEnv() {
  stepCount = 0;
  agents = Array.from({ length: NUM_AGENTS }, (_, i) => ({
    id: `drone-${i + 1}`,
    x: Math.random() * 100,
    y: Math.random() * 100,
    z: Math.random() * 20,
    reward: 0,
    cumulativeReward: 0,
  }));
  console.log('Mock env reset. Initial agent positions + rewards generated.');
}

function mockReward(agent) {
  // Stand-in for the real reward function (Venkatesh's +1 unexplored / -100 collision logic).
  // Small random positive reward most steps, occasional penalty, so reward flow can be tested end-to-end.
  const roll = Math.random();
  if (roll < 0.05) return -100; // simulated collision penalty
  if (roll < 0.8) return 1; // simulated unexplored-area reward
  return 0; // neutral step
}

function stepEnv() {
  stepCount += 1;
  agents = agents.map(agent => {
    const reward = mockReward(agent);
    return {
      ...agent,
      x: agent.x + (Math.random() - 0.5) * 2,
      y: agent.y + (Math.random() - 0.5) * 2,
      z: Math.max(0, agent.z + (Math.random() - 0.5) * 1),
      reward,
      cumulativeReward: agent.cumulativeReward + reward,
    };
  });
  return agents;
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
          reward: a.reward,
          cumulativeReward: a.cumulativeReward,
        })),
      };
      ws.send(JSON.stringify(batchMsg));

      const avgReward = (updatedAgents.reduce((sum, a) => sum + a.reward, 0) / updatedAgents.length).toFixed(2);
      console.log(`Step ${stepCount}: sent batch (${updatedAgents.length} agents) | avg reward: ${avgReward}`);
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