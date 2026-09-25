const WebSocket = require('ws');
const { createServer } = require('../server');
const { createTelemetryFrame, isValidTelemetryFrame } = require('../schema');

const PORT = 8099;
const NUM_SUBSCRIBERS = 2;
const NUM_DRONES = 50;
const STREAM_HZ = 30;
const FRAME_INTERVAL_MS = Math.round(1000 / STREAM_HZ); // ~33ms
const TOTAL_FRAMES = 150; // 5 seconds of sustained streaming

function generate50DroneFrame(step) {
  const drones = [];
  for (let i = 0; i < NUM_DRONES; i++) {
    const angle = (step * 0.05 + i * (Math.PI * 2 / NUM_DRONES));
    const radius = 15 + (i % 5) * 4;
    const x = Math.cos(angle) * radius;
    const z = Math.sin(angle) * radius;
    const y = 5.0 + Math.sin(step * 0.1 + i) * 1.5;

    const heading = (angle + Math.PI / 2) % (Math.PI * 2);
    const halfH = heading / 2;

    const detections = [];
    for (let d = 0; d < 8; d++) {
      detections.push({
        id: `target_${d}`,
        type: d < 3 ? 'target' : (d < 6 ? 'obstacle' : 'drone'),
        dist: 4.0 + d * 1.5,
        angle: -0.5 + d * 0.15,
      });
    }

    drones.push({
      id: i,
      agent_id: `drone_${i}`,
      pos: [parseFloat(x.toFixed(2)), parseFloat(y.toFixed(2)), parseFloat(z.toFixed(2))],
      vel: [parseFloat((-Math.sin(angle) * 5).toFixed(2)), 0.0, parseFloat((Math.cos(angle) * 5).toFixed(2))],
      heading: parseFloat(heading.toFixed(4)),
      rot: [0.0, parseFloat(Math.sin(halfH).toFixed(4)), 0.0, parseFloat(Math.cos(halfH).toFixed(4))],
      status: 'active',
      detections,
    });
  }

  const targets = [
    { id: 0, pos: [10.0, 0.5, 15.0], found: true, discovered_by: 'drone_0' },
    { id: 1, pos: [-20.0, 0.5, -10.0], found: false, discovered_by: null },
    { id: 2, pos: [30.0, 0.5, -25.0], found: false, discovered_by: null },
    { id: 3, pos: [-15.0, 0.5, 30.0], found: true, discovered_by: 'drone_4' },
    { id: 4, pos: [0.0, 0.5, 0.0], found: false, discovered_by: null },
  ];

  return createTelemetryFrame({
    step,
    timestamp: Date.now(),
    sim_time: step * 0.05,
    metrics: {
      explored_fraction: Math.min(1.0, 0.1 + step * 0.005),
      active_drones: NUM_DRONES,
      targets_found: 2,
      total_targets: 5,
      step_reward_sum: 14.2,
    },
    drones,
    targets,
  });
}

async function runLoadTest() {
  console.log(`[Load Test] Starting WebSocket server on port ${PORT}...`);
  const server = createServer(PORT);

  await new Promise(resolve => server.on('listening', resolve));

  const startMemory = process.memoryUsage();
  let stringifyTimes = [];
  let parseTimes = [];
  let latencies = [];
  let totalBytesSent = 0;

  const subscribers = [];
  const subscriberReceived = Array(NUM_SUBSCRIBERS).fill(0);
  const subscriberDropped = Array(NUM_SUBSCRIBERS).fill(0);

  // Connect Subscribers
  for (let s = 0; s < NUM_SUBSCRIBERS; s++) {
    const subWs = new WebSocket(`ws://localhost:${PORT}`);
    await new Promise((resolve, reject) => {
      subWs.on('open', () => {
        subWs.send(JSON.stringify({ type: 'register', role: 'subscriber' }));
      });
      subWs.on('message', (data) => {
        const t0 = process.hrtime.bigint();
        const parsed = JSON.parse(data.toString());
        const t1 = process.hrtime.bigint();
        parseTimes.push(Number(t1 - t0) / 1e6);

        if (parsed.type === 'registered') {
          resolve();
        } else if (parsed.type === 'frame') {
          const expected = subscriberReceived[s];
          if (parsed.step !== expected) {
            subscriberDropped[s] += Math.abs(parsed.step - expected);
          }
          subscriberReceived[s] += 1;
          const latency = Date.now() - parsed.timestamp;
          latencies.push(latency);
        }
      });
      subWs.on('error', reject);
    });
    subscribers.push(subWs);
  }

  // Connect Publisher
  const pubWs = new WebSocket(`ws://localhost:${PORT}`);
  await new Promise((resolve, reject) => {
    pubWs.on('open', () => {
      pubWs.send(JSON.stringify({ type: 'register', role: 'publisher' }));
    });
    pubWs.on('message', (data) => {
      const parsed = JSON.parse(data.toString());
      if (parsed.type === 'registered') {
        resolve();
      }
    });
    pubWs.on('error', reject);
  });

  console.log(`[Load Test] 1 Publisher and ${NUM_SUBSCRIBERS} Subscribers connected.`);
  console.log(`[Load Test] Streaming ${TOTAL_FRAMES} atomic frames at ${STREAM_HZ} Hz (~${FRAME_INTERVAL_MS}ms interval)...`);

  const streamStartTime = Date.now();

  for (let step = 0; step < TOTAL_FRAMES; step++) {
    const frame = generate50DroneFrame(step);

    const t0 = process.hrtime.bigint();
    const payload = JSON.stringify(frame);
    const t1 = process.hrtime.bigint();
    stringifyTimes.push(Number(t1 - t0) / 1e6);

    totalBytesSent += Buffer.byteLength(payload);
    pubWs.send(payload);

    await new Promise(r => setTimeout(r, FRAME_INTERVAL_MS));
  }

  // Allow short drain buffer
  await new Promise(r => setTimeout(r, 200));

  const streamDurationSec = (Date.now() - streamStartTime) / 1000;
  const throughputKBs = (totalBytesSent / 1024) / streamDurationSec;
  const endMemory = process.memoryUsage();

  // Clean up
  pubWs.close();
  subscribers.forEach(s => s.close());
  server.close();

  // Statistics calculation
  const avgLatency = latencies.reduce((a, b) => a + b, 0) / (latencies.length || 1);
  const sortedLatencies = [...latencies].sort((a, b) => a - b);
  const p95Latency = sortedLatencies[Math.floor(sortedLatencies.length * 0.95)] || 0;
  const maxLatency = sortedLatencies[sortedLatencies.length - 1] || 0;

  const avgStringify = stringifyTimes.reduce((a, b) => a + b, 0) / stringifyTimes.length;
  const avgParse = parseTimes.reduce((a, b) => a + b, 0) / parseTimes.length;

  console.log('\n================ 50-AGENT LOAD TEST RESULTS ================');
  console.log(`Total Frames Sent:          ${TOTAL_FRAMES}`);
  subscriberReceived.forEach((count, idx) => {
    console.log(`Subscriber #${idx + 1} Received:      ${count} frames (dropped: ${subscriberDropped[idx]})`);
  });
  console.log(`Wire Throughput:            ${throughputKBs.toFixed(2)} KB/s (threshold: >375 KB/s)`);
  console.log(`Frame Payload Size:         ~${(totalBytesSent / TOTAL_FRAMES / 1024).toFixed(2)} KB/frame`);
  console.log(`Avg Relay Latency:          ${avgLatency.toFixed(2)} ms (threshold: <15 ms)`);
  console.log(`P95 Relay Latency:          ${p95Latency} ms`);
  console.log(`Max Relay Latency:          ${maxLatency} ms`);
  console.log(`Avg JSON.stringify Time:    ${avgStringify.toFixed(3)} ms`);
  console.log(`Avg JSON.parse Time:        ${avgParse.toFixed(3)} ms`);
  console.log(`Heap Used (Start -> End):   ${(startMemory.heapUsed / 1024 / 1024).toFixed(2)} MB -> ${(endMemory.heapUsed / 1024 / 1024).toFixed(2)} MB`);
  console.log('============================================================\n');

  // Assertions
  subscriberReceived.forEach((count, idx) => {
    if (count !== TOTAL_FRAMES) {
      throw new Error(`Subscriber #${idx + 1} missed frames! Expected ${TOTAL_FRAMES}, got ${count}`);
    }
    if (subscriberDropped[idx] !== 0) {
      throw new Error(`Subscriber #${idx + 1} dropped ${subscriberDropped[idx]} frames!`);
    }
  });

  if (avgLatency > 15.0) {
    throw new Error(`Average latency ${avgLatency.toFixed(2)}ms exceeded 15ms threshold!`);
  }

  if (throughputKBs < 375.0) {
    throw new Error(`Throughput ${throughputKBs.toFixed(2)} KB/s fell below 375 KB/s threshold!`);
  }

  console.log('PASS: All 50-agent scale load test criteria satisfied.');
}

if (require.main === module) {
  runLoadTest().catch(err => {
    console.error('FAIL:', err.stack || err);
    process.exit(1);
  });
}


module.exports = { runLoadTest };
