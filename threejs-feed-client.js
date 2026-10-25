const WebSocket = require('ws');

// Stand-in for the Three.js frontend: listens to the feed and converts every
// batch into the flat Float32Array [x0,y0,z0, x1,y1,z1, ...] a Three.js buffer needs.
const RUN_MS = Number(process.env.RUN_MS) || 10000;
const ws = new WebSocket('ws://localhost:8080');

let frames = 0, bad = 0;
const latencies = [];

ws.on('open', () => {
  console.log(`Frontend stand-in connected. Listening for ${RUN_MS / 1000}s...`);
  setTimeout(finish, RUN_MS);
});

ws.on('message', (data) => {
  let msg;
  try { msg = JSON.parse(data.toString()); } catch { return; }
  if (msg.type !== 'batch_update') return;

  const positions = new Float32Array(msg.agents.length * 3);
  msg.agents.forEach((a, i) => {
    positions[i * 3] = a.x;
    positions[i * 3 + 1] = a.y;
    positions[i * 3 + 2] = a.z;
  });

  frames++;
  if (positions.length !== 150 || positions.some(Number.isNaN)) bad++;
  latencies.push(Date.now() - msg.timestamp);
  if (frames <= 3 || frames % 25 === 0) {
    console.log(`Step ${msg.step}: ${msg.agents.length} agents -> Float32Array(${positions.length})`);
  }
});

function finish() {
  const avg = latencies.length ? latencies.reduce((a, b) => a + b, 0) / latencies.length : 0;
  console.log('--- Three.js feed check ---');
  console.log(`Frames: ${frames} | bad buffers: ${bad} | avg latency: ${avg.toFixed(1)}ms | max: ${Math.max(0, ...latencies)}ms`);
  const ok = frames > 0 && bad === 0;
  console.log(ok ? 'THREE.JS FEED: PASS' : 'THREE.JS FEED: FAIL');
  process.exit(ok ? 0 : 1);
}

ws.on('error', (e) => { console.error('Error:', e.message); process.exit(1); });