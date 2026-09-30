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
  const roll = Math.random();
  if (roll < 0.05) return -100;
  if (roll < 0.8) return 1;
  return 0;
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

function computeObservationFeatures(agentList) {
  return agentList.map(agent => {
    const distances = agentList
      .filter(other => other.id !== agent.id)
      .map(other => {
        const dx = other.x - agent.x;
        const dy = other.y - agent.y;
        const dz = other.z - agent.z;
        return { id: other.id, distance: Math.sqrt(dx * dx + dy * dy + dz * dz) };
      })
      .sort((a, b) => a.distance - b.distance);

    const nearest = distances.slice(0, 3);

    return {
      ...agent,
      nearestNeighbors: nearest.map(n => ({
        id: n.id,
        distance: Math.round(n.distance * 100) / 100,
      })),
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
      const enrichedAgents = computeObservationFeatures(updatedAgents);

      const batchMsg = {
        type: 'batch_update',
        step: stepCount,
        timestamp: Date.now(),
        agents: enrichedAgents.map(a => ({
          id: a.id,
          x: Math.round(a.x * 100) / 100,
          y: Math.round(a.y * 100) / 100,
          z: Math.round(a.z * 100) / 100,
          reward: a.reward,
          cumulativeReward: a.cumulativeReward,
          nearestNeighbors: a.nearestNeighbors,
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