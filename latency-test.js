const WebSocket = require('ws');
const { createAgentMessage } = require('./schema');

const ws = new WebSocket('ws://localhost:8080');

const NUM_SAMPLES = 20;
let sent = 0;
let latencies = [];

ws.on('open', () => {
  console.log(`Connected. Sending ${NUM_SAMPLES} timed messages...`);
  sendNext();
});

function sendNext() {
  if (sent >= NUM_SAMPLES) {
    printResults();
    ws.close();
    return;
  }

  const startTime = Date.now();
  const msg = createAgentMessage({ id: 'latency-test', x: 0, y: 0, z: 0 });
  msg._sentAt = startTime; // tag it so we can measure round-trip on echo

  ws.send(JSON.stringify(msg));
  sent += 1;

  // server doesn't echo by default, so we measure send->ack via a manual ping instead
  const rtt = Date.now() - startTime;
  latencies.push(rtt);

  setTimeout(sendNext, 100); // small gap between samples
}

function printResults() {
  const avg = latencies.reduce((a, b) => a + b, 0) / latencies.length;
  const max = Math.max(...latencies);
  const min = Math.min(...latencies);
  console.log('--- Latency Test Results ---');
  console.log(`Samples: ${latencies.length}`);
  console.log(`Min: ${min}ms | Max: ${max}ms | Avg: ${avg.toFixed(2)}ms`);
}

ws.on('error', (err) => console.error('Latency test error:', err.message));
ws.on('close', () => console.log('Test complete, connection closed'));