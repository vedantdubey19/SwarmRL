const WebSocket = require('ws');

const NUM_AGENTS = 50;
const STEP_INTERVAL_MS = 200;
const TEST_DURATION_MS = 30000; // run for 30s sustained load

const ws = new WebSocket('ws://localhost:8080');

let agents = [];
let stepCount = 0;
let messagesReceived = 0;
let messagesSent = 0;
let startTime;

function resetEnv() {
  agents = Array.from({ length: NUM_AGENTS }, (_, i) => ({
    id: `drone-${i + 1}`,
    x: Math.random() * 100,
    y: Math.random() * 100,
    z: Math.random() * 20,
  }));
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
  console.log(`Starting ${TEST_DURATION_MS / 1000}s sustained load test with ${NUM_AGENTS} agents...`);
  startTime = Date.now();
  resetEnv();

  const interval = setInterval(() => {
    if (Date.now() - startTime >= TEST_DURATION_MS) {
      clearInterval(interval);
      printResults();
      ws.close();
      return;
    }

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
    messagesSent += 1;
  }, STEP_INTERVAL_MS);
});

ws.on('message', () => {
  messagesReceived += 1;
});

function printResults() {
  const elapsedSec = (Date.now() - startTime) / 1000;
  console.log('--- 50-Agent Validation Results ---');
  console.log(`Duration: ${elapsedSec.toFixed(1)}s`);
  console.log(`Steps sent: ${stepCount}`);
  console.log(`Batch messages sent: ${messagesSent}`);
  console.log(`Total agent-updates sent: ${messagesSent * NUM_AGENTS}`);
  console.log(`Messages received from server: ${messagesReceived}`);
  console.log(`Avg steps/sec: ${(stepCount / elapsedSec).toFixed(2)}`);
}

ws.on('error', (err) => console.error('Validation test error:', err.message));
ws.on('close', () => console.log('Validation test complete.'));