const WebSocket = require('ws');
const { createRelayServer } = require('../server/server');

async function runLoadTest() {
  console.log('=== Starting SwarmRL 50-Agent WebSocket Relay Load Test ===');

  let port;
  let relay;
  await new Promise((resolve) => {
    relay = createRelayServer(0, '127.0.0.1', (wss) => {
      port = wss.address().port;
      resolve();
    });
  });

  const wsUrl = `ws://127.0.0.1:${port}`;
  console.log(`Relay active at ${wsUrl}`);

  // Connect 2 subscribers
  const sub1 = new WebSocket(wsUrl);
  const sub2 = new WebSocket(wsUrl);

  const latencies1 = [];
  const latencies2 = [];

  sub1.on('message', (data) => {
    const now = Date.now();
    try {
      const msg = JSON.parse(data.toString());
      if (msg.type === 'frame') {
        latencies1.push(now - msg.timestamp);
      }
    } catch (e) {}
  });

  sub2.on('message', (data) => {
    const now = Date.now();
    try {
      const msg = JSON.parse(data.toString());
      if (msg.type === 'frame') {
        latencies2.push(now - msg.timestamp);
      }
    } catch (e) {}
  });

  await Promise.all([
    new Promise((resolve) => sub1.on('open', resolve)),
    new Promise((resolve) => sub2.on('open', resolve)),
  ]);

  sub1.send(JSON.stringify({ type: 'register', role: 'subscriber' }));
  sub2.send(JSON.stringify({ type: 'register', role: 'subscriber' }));

  // Connect publisher
  const pub = new WebSocket(wsUrl);
  await new Promise((resolve) => pub.on('open', resolve));
  pub.send(JSON.stringify({ type: 'register', role: 'publisher' }));

  // Build a realistic 50-drone payload
  function make50DroneFrame(step) {
    const drones = [];
    for (let i = 0; i < 50; i++) {
      drones.push({
        id: i,
        agent_id: `drone_${i}`,
        position: [i * 1.5 - 35, 5.0, (i % 10) * 3 - 15],
        velocity: [1.2, 0.0, -0.8],
        quaternion: [0.0, 0.707, 0.0, 0.707],
        heading: 1.57,
        status: 'active',
        detections: [
          { id: 'target_0', type: 'target', distance: 8.5, bearing_x: 0.1, bearing_y: 0.9, angle: 0.2 },
          { id: 'obs_1', type: 'obstacle', distance: 12.0, bearing_x: -0.3, bearing_y: 0.8, angle: 0.4 },
        ],
      });
    }

    return {
      type: 'frame',
      step: step,
      timestamp: Date.now(),
      sim_time: step * 0.1,
      drones: drones,
      metrics: {
        explored_fraction: Math.min(1.0, 0.05 + step * 0.002),
        collision_totals: { drone: 0, obstacle: 0, boundary: 0, total: 0 },
        targets_found: Math.floor(step / 60),
        active_agents: 50,
        difficulty: 2,
        step_reward_sum: 2.5,
      },
    };
  }

  const TARGET_FRAMES = 180; // 180 frames at 30 Hz = 6 seconds of streaming
  const FRAME_INTERVAL_MS = 1000 / 30; // 33.3 ms

  console.log(`Streaming ${TARGET_FRAMES} frames at 30 Hz to 2 subscribers...`);

  const startTime = Date.now();
  for (let step = 1; step <= TARGET_FRAMES; step++) {
    const frame = make50DroneFrame(step);
    pub.send(JSON.stringify(frame));
    await new Promise((r) => setTimeout(r, FRAME_INTERVAL_MS));
  }

  // Allow in-flight messages to arrive
  await new Promise((r) => setTimeout(r, 200));

  const totalTime = (Date.now() - startTime) / 1000;
  console.log(`Stream complete in ${totalTime.toFixed(2)}s`);

  // Close connections
  pub.close();
  sub1.close();
  sub2.close();
  await relay.close();

  // Statistics calculation
  const allLatencies = [...latencies1, ...latencies2];
  allLatencies.sort((a, b) => a - b);

  const avgLatency = allLatencies.reduce((sum, v) => sum + v, 0) / (allLatencies.length || 1);
  const p50 = allLatencies[Math.floor(allLatencies.length * 0.50)] || 0;
  const p95 = allLatencies[Math.floor(allLatencies.length * 0.95)] || 0;
  const p99 = allLatencies[Math.floor(allLatencies.length * 0.99)] || 0;
  const maxLat = allLatencies[allLatencies.length - 1] || 0;

  const droppedSub1 = TARGET_FRAMES - latencies1.length;
  const droppedSub2 = TARGET_FRAMES - latencies2.length;
  const totalDropped = droppedSub1 + droppedSub2;

  console.log('\n--- Load Test Results ---');
  console.log(`Frames Sent:              ${TARGET_FRAMES}`);
  console.log(`Subscriber 1 Received:    ${latencies1.length} / ${TARGET_FRAMES} (Dropped: ${droppedSub1})`);
  console.log(`Subscriber 2 Received:    ${latencies2.length} / ${TARGET_FRAMES} (Dropped: ${droppedSub2})`);
  console.log(`Total Dropped Frames:     ${totalDropped}`);
  console.log(`Average Latency:          ${avgLatency.toFixed(2)} ms`);
  console.log(`P50 Latency:              ${p50} ms`);
  console.log(`P95 Latency:              ${p95} ms`);
  console.log(`P99 Latency:              ${p99} ms`);
  console.log(`Max Latency:              ${maxLat} ms`);

  // Assert gate requirements
  if (totalDropped !== 0) {
    console.error(`FAILED: Expected zero dropped frames, got ${totalDropped}`);
    process.exit(1);
  }

  if (avgLatency >= 15.0) {
    console.error(`FAILED: Average latency ${avgLatency.toFixed(2)} ms exceeds required 15 ms`);
    process.exit(1);
  }

  console.log('\nGATE PASSED: 150+ frames at 30 Hz to 2 subscribers with zero dropped and average latency under 15 ms.');
  process.exit(0);
}

runLoadTest().catch((err) => {
  console.error('Fatal load test error:', err);
  process.exit(1);
});
