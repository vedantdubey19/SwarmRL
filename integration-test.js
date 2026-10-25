const WebSocket = require('ws');

const RUN_MS = Number(process.env.RUN_MS) || 15000;
const ws = new WebSocket('ws://localhost:8080');

const seen = { batch: 0, grid: 0, snap: 0, env: 0 };
const problems = [];
const levels = new Set();
let lastStep = -1, lastPercent = 0, malformed = 0;

ws.on('open', () => {
  console.log(`Connected. Running full integration check for ${RUN_MS / 1000}s...`);
  setTimeout(finish, RUN_MS);
});

ws.on('message', (data) => {
  let m;
  try { m = JSON.parse(data.toString()); } catch { malformed++; return; }

  if (m.type === 'batch_update') {
    seen.batch++;
    if (m.agents.length !== 50) problems.push(`step ${m.step}: ${m.agents.length} agents`);
    if (m.step <= lastStep) problems.push(`step order broke at ${m.step}`);
    lastStep = m.step;
    levels.add(m.level);
  } else if (m.type === 'grid_delta') {
    seen.grid++;
    if (!Array.isArray(m.cells) || m.cells.length === 0) problems.push('grid_delta without cells');
    if (m.percentExplored < lastPercent) problems.push('explored % went down');
    lastPercent = m.percentExplored;
  } else if (m.type === 'grid_snapshot') {
    seen.snap++;
    const expected = Math.round((m.cells.length / (m.gridSize * m.gridSize)) * 1000) / 10;
    if (expected !== m.percentExplored) problems.push(`snapshot cells (${m.cells.length}) disagree with ${m.percentExplored}%`);
  } else if (m.type === 'env_event') {
    seen.env++;
    if (!Array.isArray(m.obstacles) || typeof m.wind !== 'number') problems.push('bad env_event');
  }
});

function finish() {
  console.log('--- Day 28 integration result ---');
  console.log(`batch_update: ${seen.batch} | grid_delta: ${seen.grid} | grid_snapshot: ${seen.snap} | env_event: ${seen.env}`);
  console.log(`levels seen: ${[...levels].join(', ')} | explored: ${lastPercent}% | malformed: ${malformed}`);
  if (seen.batch === 0) problems.push('no batch_update received');
  if (seen.grid === 0) problems.push('no grid_delta received');
  if (seen.snap === 0) problems.push('no grid_snapshot received');
  if (seen.env === 0) problems.push('no env_event received');
  if (malformed) problems.push(`${malformed} malformed messages`);
  if (problems.length) {
    console.log('FAIL:', problems.slice(0, 5));
    process.exit(1);
  }
  console.log('INTEGRATION: PASS');
  process.exit(0);
}

ws.on('error', (e) => { console.error('Error:', e.message); process.exit(1); });