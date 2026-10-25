const WebSocket = require('ws');
const { GridPaint } = require('./grid-paint');
const { createObstacles, findCollisions } = require('./obstacles');
const { applyWind } = require('./wind');
const { LEVELS, levelForStep } = require('./curriculum');

const NUM_AGENTS = 50;
const WORLD = 100;
const STEP_INTERVAL_MS = 200;
const RECONNECT_DELAY_MS = 2000;
const STEPS_PER_LEVEL = Number(process.env.STEPS_PER_LEVEL) || 150;
const KEYFRAME_EVERY = 25; // resend environment state so late joiners catch up

let ws;
let agents = [];
let stepCount = 0;
let stepTimer = null;
const grid = new GridPaint(20, WORLD);
let currentLevel = LEVELS[0];
let obstacles = [];

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const round2 = (v) => Math.round(v * 100) / 100;

function setLevel(cfg) {
  currentLevel = cfg;
  obstacles = createObstacles(cfg, WORLD);
}

function resetEnv() {
  stepCount = 0;
  grid.reset();
  setLevel(LEVELS[0]);
  agents = Array.from({ length: NUM_AGENTS }, (_, i) => ({
    id: `drone-${i + 1}`,
    x: Math.random() * WORLD,
    y: Math.random() * WORLD,
    z: Math.random() * 20,
    reward: 0,
    cumulativeReward: 0,
  }));
  console.log('Mock env reset. Level 1, grid cleared.');
}

function mockReward(collided) {
  if (collided) return -100; // obstacle collision penalty
  return Math.random() < 0.8 ? 1 : 0; // +1 for exploring, else neutral
}

function stepEnv() {
  stepCount += 1;
  const cfg = levelForStep(stepCount, STEPS_PER_LEVEL);
  const levelChanged = cfg.level !== currentLevel.level;
  if (levelChanged) setLevel(cfg);

  const moved = agents.map((a) => ({
    ...a,
    x: a.x + (Math.random() - 0.5) * 2,
    y: a.y + (Math.random() - 0.5) * 2,
    z: Math.max(0, a.z + (Math.random() - 0.5)),
  }));
  const windy = applyWind(moved, stepCount, currentLevel.wind).map((a) => ({
    ...a,
    x: clamp(a.x, 0, WORLD),
    y: clamp(a.y, 0, WORLD),
  }));
  const hit = new Set(findCollisions(windy, obstacles));

  agents = windy.map((a) => {
    const reward = mockReward(hit.has(a.id));
    return { ...a, reward, cumulativeReward: a.cumulativeReward + reward };
  });
  return { levelChanged, collisions: hit.size };
}

function computeObservationFeatures(list) {
  return list.map((agent) => {
    const nearest = list
      .filter((o) => o.id !== agent.id)
      .map((o) => {
        const dx = o.x - agent.x, dy = o.y - agent.y, dz = o.z - agent.z;
        return { id: o.id, distance: Math.sqrt(dx * dx + dy * dy + dz * dz) };
      })
      .sort((a, b) => a.distance - b.distance)
      .slice(0, 3);
    return { ...agent, nearestNeighbors: nearest.map((n) => ({ id: n.id, distance: round2(n.distance) })) };
  });
}

function send(msg) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(msg));
  }
}

function connect() {
  ws = new WebSocket('ws://localhost:8080');

  ws.on('open', () => {
    console.log('Mock env feed connected.');
    resetEnv();

    stepTimer = setInterval(() => {
      const { levelChanged, collisions } = stepEnv();
      const enriched = computeObservationFeatures(agents);
      const now = Date.now();

      send({
        type: 'batch_update',
        step: stepCount,
        timestamp: now,
        level: currentLevel.level,
        agents: enriched.map((a) => ({
          id: a.id,
          x: round2(a.x),
          y: round2(a.y),
          z: round2(a.z),
          reward: a.reward,
          cumulativeReward: a.cumulativeReward,
          nearestNeighbors: a.nearestNeighbors,
        })),
      });

      const fresh = grid.update(agents);
      if (fresh.length > 0) {
        send({ type: 'grid_delta', step: stepCount, timestamp: now, cells: fresh, percentExplored: grid.percentExplored });
      }

      if (levelChanged || stepCount === 1 || stepCount % KEYFRAME_EVERY === 0) {
        send({
          type: 'env_event',
          kind: 'environment',
          step: stepCount,
          timestamp: now,
          level: currentLevel.level,
          wind: currentLevel.wind,
          obstacles,
        });
        send({
          type: 'grid_snapshot',
          step: stepCount,
          timestamp: now,
          gridSize: grid.cells,
          cells: grid.snapshot(),
          percentExplored: grid.percentExplored,
        });
      }

      if (levelChanged) console.log(`>>> Curriculum advanced to level ${currentLevel.level}`);
      const avg = (agents.reduce((s, a) => s + a.reward, 0) / agents.length).toFixed(2);
      console.log(`Step ${stepCount} | L${currentLevel.level} | avg reward ${avg} | collisions ${collisions} | explored ${grid.percentExplored}%`);
    }, STEP_INTERVAL_MS);
  });

  ws.on('close', () => {
    console.log(`Disconnected. Reconnecting in ${RECONNECT_DELAY_MS}ms...`);
    clearInterval(stepTimer);
    setTimeout(connect, RECONNECT_DELAY_MS);
  });

  ws.on('error', (err) => console.error('Mock env feed error:', err.message));
}

connect();