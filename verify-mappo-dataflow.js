const WebSocket = require('ws');

const FRAMES_TO_CHECK = 10;
const ws = new WebSocket('ws://localhost:8080');
let checked = 0, failures = 0, lastStep = -1;

ws.on('open', () => console.log('Connected. Verifying MAPPO data flow...'));

ws.on('message', (data) => {
  let msg;
  try { msg = JSON.parse(data.toString()); } catch { return; }
  if (msg.type !== 'batch_update') return;

  checked++;
  const problems = [];
  if (msg.step <= lastStep) problems.push(`step went backwards (${lastStep} -> ${msg.step})`);
  lastStep = msg.step;
  if (msg.agents.length !== 50) problems.push(`expected 50 agents, got ${msg.agents.length}`);

  for (const a of msg.agents) {
    for (const k of ['x', 'y', 'z', 'reward', 'cumulativeReward']) {
      if (typeof a[k] !== 'number' || Number.isNaN(a[k])) problems.push(`${a.id}: ${k} is not a number`);
    }
    if (!Array.isArray(a.nearestNeighbors) || a.nearestNeighbors.length !== 3) problems.push(`${a.id}: needs exactly 3 neighbors`);
    else if (a.nearestNeighbors.some((n) => n.id === a.id)) problems.push(`${a.id}: lists itself as neighbor`);
  }

  if (problems.length) { failures++; console.log(`Frame ${checked} (step ${msg.step}) FAIL:`, problems.slice(0, 3)); }
  else console.log(`Frame ${checked} (step ${msg.step}) PASS`);

  if (checked >= FRAMES_TO_CHECK) {
    console.log(failures === 0 ? 'MAPPO DATA FLOW: PASS' : `MAPPO DATA FLOW: FAIL (${failures} bad frames)`);
    ws.close();
    process.exit(failures === 0 ? 0 : 1);
  }
});

ws.on('error', (e) => { console.error('Error:', e.message); process.exit(1); });