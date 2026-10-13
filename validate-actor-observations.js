const WebSocket = require('ws');

const ws = new WebSocket('ws://localhost:8080');
let framesChecked = 0;
const MAX_FRAMES = 10;

ws.on('open', () => {
  console.log('Connected. Validating decentralized actor observations...');
});

ws.on('message', (data) => {
  let msg;
  try {
    msg = JSON.parse(data.toString());
  } catch {
    return;
  }

  if (msg.type !== 'batch_update' || framesChecked >= MAX_FRAMES) return;
  framesChecked++;

  console.log(`\n--- Frame ${framesChecked} (step ${msg.step}) ---`);

  let allValid = true;

  msg.agents.forEach(agent => {
    // 1. Each agent must have its own neighbor list, not empty, not full swarm
    if (!Array.isArray(agent.nearestNeighbors) || agent.nearestNeighbors.length === 0) {
      console.log(`FAIL: ${agent.id} has no neighbor observations`);
      allValid = false;
      return;
    }

    // 2. An agent should never list itself as its own neighbor
    const selfReference = agent.nearestNeighbors.find(n => n.id === agent.id);
    if (selfReference) {
      console.log(`FAIL: ${agent.id} lists itself as a neighbor (leak of global state)`);
      allValid = false;
    }

    // 3. Neighbor count should be capped (decentralized = local view only, not full swarm)
    if (agent.nearestNeighbors.length > 3) {
      console.log(`FAIL: ${agent.id} has ${agent.nearestNeighbors.length} neighbors, expected max 3 (local obs, not global)`);
      allValid = false;
    }

    // 4. Distances should be sorted ascending (nearest first) — sanity check on the computation
    const distances = agent.nearestNeighbors.map(n => n.distance);
    const sorted = [...distances].sort((a, b) => a - b);
    if (JSON.stringify(distances) !== JSON.stringify(sorted)) {
      console.log(`FAIL: ${agent.id} neighbor list not sorted by distance`);
      allValid = false;
    }
  });

  // 5. Spot-check: two different agents shouldn't have identical neighbor sets (would indicate shared/global state bug)
  const neighborSignatures = msg.agents.map(a => JSON.stringify(a.nearestNeighbors.map(n => n.id)));
  const uniqueSignatures = new Set(neighborSignatures);
  if (uniqueSignatures.size < msg.agents.length * 0.5) {
    console.log(`WARNING: Many agents share identical neighbor sets (${uniqueSignatures.size}/${msg.agents.length} unique) — check for global state leak`);
  }

  console.log(allValid ? `Frame ${framesChecked}: PASS` : `Frame ${framesChecked}: FAIL (see above)`);

  if (framesChecked >= MAX_FRAMES) {
    console.log('\nValidation complete.');
    ws.close();
  }
});

ws.on('error', (err) => console.error('Error:', err.message));