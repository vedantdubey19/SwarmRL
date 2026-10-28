#!/usr/bin/env node
/**
 * Developer-only standalone mock feed tool for UI testing without Python.
 * NOT part of the live path or production simulation.
 * Usage: node scripts/mock_feed.js --mock
 */

const WebSocket = require('ws');

if (!process.argv.includes('--mock')) {
  console.error('ERROR: scripts/mock_feed.js is a developer-only tool and requires the --mock flag to run.');
  console.error('Usage: node scripts/mock_feed.js --mock [--ws ws://localhost:8080] [--hz 30]');
  process.exit(1);
}

const wsUrl = process.argv[process.argv.indexOf('--ws') + 1] || process.env.WS_URL || 'ws://127.0.0.1:8080';
const hzArg = Number(process.argv[process.argv.indexOf('--hz') + 1]) || 30;
const intervalMs = 1000 / hzArg;

console.log(`[DEV TOOL] Starting mock feed to ${wsUrl} at ${hzArg} Hz...`);

const ws = new WebSocket(wsUrl);

ws.on('open', () => {
  console.log('[DEV TOOL] Connected to WebSocket relay.');
  ws.send(JSON.stringify({ type: 'register', role: 'publisher' }));

  // Send world layout
  ws.send(
    JSON.stringify({
      version: '1.0.0',
      type: 'world',
      bounds: { x_min: -50, x_max: 50, y_min: 0, y_max: 20, z_min: -50, z_max: 50 },
      obstacles: [],
      targets: [{ id: 0, position: [0, 1, 0], radius: 1, found: false }],
    })
  );

  let step = 0;
  setInterval(() => {
    step++;
    const drones = [];
    for (let i = 0; i < 50; i++) {
      const angle = (step * 0.05) + (i * (2 * Math.PI / 50));
      const radius = 20 + 5 * Math.sin(step * 0.02 + i);
      drones.push({
        id: i,
        agent_id: `drone_${i}`,
        position: [Math.cos(angle) * radius, 5 + Math.sin(step * 0.1 + i), Math.sin(angle) * radius],
        velocity: [Math.cos(angle), 0, Math.sin(angle)],
        heading: angle,
        quaternion: [0, 0, 0, 1],
        status: 'active',
        detections: [],
      });
    }

    const frame = {
      version: '1.0.0',
      type: 'frame',
      step,
      timestamp: Date.now(),
      sim_time: step * 0.1,
      drones,
      metrics: {
        explored_fraction: Math.min(1.0, step * 0.001),
        collision_totals: { drone: 0, obstacle: 0, boundary: 0, total: 0 },
        targets_found: 0,
        total_targets: 1,
        active_agents: 50,
        difficulty: 0,
        step_reward_sum: 0,
      },
    };

    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(frame));
    }
  }, intervalMs);
});

ws.on('error', (err) => {
  console.error('[DEV TOOL] Socket error:', err.message);
});

ws.on('close', () => {
  console.log('[DEV TOOL] Connection closed.');
  process.exit(0);
});
