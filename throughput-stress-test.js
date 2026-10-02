const WebSocket = require('ws');

const URL = 'ws://localhost:8080';
const NUM_SUBSCRIBERS = 5;
const MSG_RATE_PER_SEC = 20;
const TEST_DURATION_MS = 30000;

let sent = 0;
let totalReceived = 0;
const subscribers = [];

function makeSubscriber(index) {
  const ws = new WebSocket(URL);
  let received = 0;

  ws.on('open', () => {
    ws.send(JSON.stringify({ type: 'register', role: 'subscriber' }));
  });

  ws.on('message', () => {
    received++;
    totalReceived++;
  });

  ws.on('error', (err) => console.error(`Subscriber ${index} error:`, err.message));

  return { ws, getReceived: () => received };
}

function makePublisher() {
  const ws = new WebSocket(URL);

  ws.on('open', () => {
    ws.send(JSON.stringify({ type: 'register', role: 'publisher' }));

    const intervalMs = 1000 / MSG_RATE_PER_SEC;
    const timer = setInterval(() => {
      const msg = {
        type: 'frame',
        step: sent,
        timestamp: Date.now(),
        agents: Array.from({ length: 50 }, (_, i) => ({ id: `drone-${i + 1}`, x: 0, y: 0, z: 0 })),
      };
      ws.send(JSON.stringify(msg));
      sent++;
    }, intervalMs);

    setTimeout(() => {
      clearInterval(timer);
      report();
      ws.close();
      subscribers.forEach(s => s.ws.close());
    }, TEST_DURATION_MS);
  });

  ws.on('error', (err) => console.error('Publisher error:', err.message));
}

function report() {
  console.log('--- Throughput Stress Test ---');
  console.log(`Duration: ${TEST_DURATION_MS / 1000}s | Rate target: ${MSG_RATE_PER_SEC}/sec`);
  console.log(`Messages sent by publisher: ${sent}`);
  console.log(`Subscribers: ${NUM_SUBSCRIBERS}`);
  console.log(`Total messages received across all subscribers: ${totalReceived}`);
  console.log(`Expected total (sent x subscribers): ${sent * NUM_SUBSCRIBERS}`);
  console.log(`Drop rate: ${(100 - (totalReceived / (sent * NUM_SUBSCRIBERS)) * 100).toFixed(1)}%`);
}

console.log(`Starting stress test: ${NUM_SUBSCRIBERS} subscribers, publisher at ${MSG_RATE_PER_SEC} msg/sec for ${TEST_DURATION_MS / 1000}s`);
for (let i = 0; i < NUM_SUBSCRIBERS; i++) {
  subscribers.push(makeSubscriber(i));
}
setTimeout(makePublisher, 500);