const WebSocket = require('ws');

const ws = new WebSocket('ws://localhost:8080');

const dummyPayloads = [
  { id: 'drone-1', x: 0, y: 0, z: 0, timestamp: Date.now() },
  { id: 'drone-2', x: 5, y: 3, z: 1, timestamp: Date.now() },
  { id: 'drone-3', x: -2, y: 8, z: 4, timestamp: Date.now() },
];

ws.on('open', () => {
  console.log('Connected. Sending dummy payloads...');
  dummyPayloads.forEach((payload, i) => {
    setTimeout(() => {
      ws.send(JSON.stringify(payload));
      console.log('Sent:', payload);
    }, i * 500);
  });

  // also test an invalid payload
  setTimeout(() => {
    ws.send(JSON.stringify({ id: 'bad-drone', x: 1 })); // missing y, z, timestamp
    console.log('Sent invalid payload (missing fields)');
  }, dummyPayloads.length * 500 + 500);
});

ws.on('message', (data) => {
  console.log('Received:', data.toString());
});

ws.on('close', () => console.log('Connection closed'));
ws.on('error', (err) => console.error('Client error:', err.message));