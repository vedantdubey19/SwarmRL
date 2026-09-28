const WebSocket = require('ws');

const URL = 'ws://localhost:8080';
const RUN_MS = 20000;
const EXPECTED_AGENTS = 50;

const ws = new WebSocket(URL);
let frames = 0, malformed = 0, wrongCount = 0, firstFrame = null;
const latencies = [];
const start = Date.now();

ws.on('open', () => {
  console.log('Connected. Registering as subscriber...');
  // Match this to the register message in docs/websocket_streaming_protocol.md
  ws.send(JSON.stringify({ type: 'register', role: 'subscriber' }));
  setTimeout(() => { report(); ws.close(); }, RUN_MS);
});

ws.on('message', (data) => {
  let msg;
  try { msg = JSON.parse(data.toString()); } catch { malformed++; return; }

  const list = Object.values(msg).find(Array.isArray); // the per-agent array in the frame
  if (!list) return; // not a frame (ack, error, etc.)

  frames++;
  if (!firstFrame) firstFrame = msg;
  if (list.length !== EXPECTED_AGENTS) wrongCount++;
  if (typeof msg.timestamp === 'number') latencies.push(Date.now() - msg.timestamp);
});

function report() {
  const secs = (Date.now() - start) / 1000;
  console.log('--- Rendering check ---');
  console.log(`Frames: ${frames} (${(frames / secs).toFixed(1)}/sec)`);
  console.log(`Frames without ${EXPECTED_AGENTS} agents: ${wrongCount}`);
  console.log(`Malformed messages: ${malformed}`);
  if (latencies.length) {
    const avg = latencies.reduce((a, b) => a + b, 0) / latencies.length;
    console.log(`Latency avg ${avg.toFixed(1)}ms, max ${Math.max(...latencies)}ms`);
  }
  if (firstFrame) console.log('First frame keys:', Object.keys(firstFrame));
  console.log(frames > 0 && wrongCount === 0 && malformed === 0 ? 'PASS' : 'CHECK FAILED');
}

ws.on('error', (err) => console.error('Client error:', err.message));