const WebSocket = require('ws');

// Keyframes go out every 25 steps (5s at 200ms/step), so wait a little longer than that.
const WAIT_MS = Number(process.env.WAIT_MS) || 8000;
const ws = new WebSocket('ws://localhost:8080');

let gotEnv = false, snap = null, done = false;

ws.on('open', () => {
  console.log(`Joined mid-run. Waiting up to ${WAIT_MS / 1000}s for a state keyframe...`);
  setTimeout(finish, WAIT_MS);
});

ws.on('message', (data) => {
  let m;
  try { m = JSON.parse(data.toString()); } catch { return; }
  if (m.type === 'env_event') gotEnv = true;
  if (m.type === 'grid_snapshot') snap = m;
  if (gotEnv && snap) finish();
});

function finish() {
  if (done) return;
  done = true;
  const problems = [];
  if (!gotEnv) problems.push('no env_event keyframe (obstacles/wind) received');
  if (!snap) problems.push('no grid_snapshot received');
  if (snap && snap.cells.length === 0) problems.push('snapshot is empty even though the run is underway');
  console.log(`env keyframe: ${gotEnv} | snapshot cells: ${snap ? snap.cells.length : 0} (${snap ? snap.percentExplored : 0}% explored)`);
  console.log(problems.length ? `LATE JOINER: FAIL ${JSON.stringify(problems)}` : 'LATE JOINER: PASS');
  process.exit(problems.length ? 1 : 0);
}

ws.on('error', (e) => { console.error('Error:', e.message); process.exit(1); });