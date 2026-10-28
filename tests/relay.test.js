const test = require('node:test');
const assert = require('node:assert');
let WebSocket;
try {
  WebSocket = require('ws');
} catch (e) {
  try {
    WebSocket = require('../server/node_modules/ws');
  } catch (e2) {
    throw e;
  }
}
const { createRelayServer } = require('../server/server');

test('late joiner receives cached world and grid snapshot', async () => {
  let port;
  let relay;
  await new Promise((resolve) => {
    relay = createRelayServer(0, '127.0.0.1', (wss) => {
      port = wss.address().port;
      resolve();
    });
  });

  // 1. Publisher connects and sends world and grid snapshot
  const pub = new WebSocket(`ws://127.0.0.1:${port}`);
  await new Promise((resolve) => pub.on('open', resolve));
  pub.send(JSON.stringify({ type: 'register', role: 'publisher' }));

  const worldMsg = {
    type: 'world',
    bounds: { x_min: -50, x_max: 50, y_min: 0, y_max: 20, z_min: -50, z_max: 50 },
    obstacles: [{ id: 'obs_0', position: [0, 5, 0], radius: 2 }],
    targets: [{ id: 'target_0', position: [10, 0, 10], found: false }],
  };
  const snapMsg = {
    type: 'grid_snapshot',
    step: 0,
    width: 50,
    height: 50,
    bitmask: 'ABCD',
  };

  pub.send(JSON.stringify(worldMsg));
  pub.send(JSON.stringify(snapMsg));

  await new Promise((resolve) => setTimeout(resolve, 80));

  // 2. Late joiner subscriber connects
  const sub = new WebSocket(`ws://127.0.0.1:${port}`);
  const received = [];
  sub.on('message', (data) => {
    received.push(JSON.parse(data.toString()));
  });

  await new Promise((resolve) => sub.on('open', resolve));
  await new Promise((resolve) => setTimeout(resolve, 100));

  assert.strictEqual(received.length, 2);
  assert.strictEqual(received[0].type, 'world');
  assert.strictEqual(received[0].obstacles[0].id, 'obs_0');
  assert.strictEqual(received[1].type, 'grid_snapshot');
  assert.strictEqual(received[1].bitmask, 'ABCD');

  pub.close();
  sub.close();
  await relay.close();
});

test('slow subscriber buffer overflow drops frames without blocking fast subscriber', async () => {
  let port;
  let relay;
  await new Promise((resolve) => {
    relay = createRelayServer(0, '127.0.0.1', (wss) => {
      port = wss.address().port;
      resolve();
    });
  });

  const pub = new WebSocket(`ws://127.0.0.1:${port}`);
  await new Promise((resolve) => pub.on('open', resolve));
  pub.send(JSON.stringify({ type: 'register', role: 'publisher' }));

  const fastSub = new WebSocket(`ws://127.0.0.1:${port}`);
  const slowSub = new WebSocket(`ws://127.0.0.1:${port}`);

  let fastReceived = 0;
  fastSub.on('message', (data) => {
    const msg = JSON.parse(data.toString());
    if (msg.type === 'frame') fastReceived++;
  });

  await Promise.all([
    new Promise((resolve) => fastSub.on('open', resolve)),
    new Promise((resolve) => slowSub.on('open', resolve)),
  ]);

  // Set high bufferedAmount on server-side socket for slowSub
  for (const sub of relay.subscribers) {
    sub.bufferedAmount = 1024 * 1024; // 1 MB > 512 KB
    break; // Mark one as slow
  }

  for (let i = 0; i < 10; i++) {
    pub.send(JSON.stringify({ type: 'frame', step: i, timestamp: Date.now(), drones: [], metrics: {} }));
  }

  await new Promise((resolve) => setTimeout(resolve, 100));

  assert(fastReceived > 0, `Expected fastReceived > 0, got ${fastReceived}`);

  pub.close();
  fastSub.close();
  slowSub.close();
  await relay.close();
});
