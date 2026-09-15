const WebSocket = require('ws');

const PORT = process.env.PORT || 8080;
const wss = new WebSocket.Server({ port: PORT });

console.log(`WebSocket server listening on ws://localhost:${PORT}`);

wss.on('connection', (socket, req) => {
  console.log('Client connected:', req.socket.remoteAddress);

  socket.on('message', (data) => {
    console.log('Received:', data.toString());
    // Placeholder — real message schema (id, x, y, z, timestamp) comes Day 2
  });

  socket.on('close', () => {
    console.log('Client disconnected');
  });

  socket.on('error', (err) => {
    console.error('Socket error:', err.message);
  });

  socket.send(JSON.stringify({ type: 'connected', message: 'WebSocket server ready' }));
});

wss.on('error', (err) => {
  console.error('Server error:', err.message);
});