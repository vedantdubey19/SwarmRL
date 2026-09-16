const WebSocket = require('ws');
const { createAgentMessage, isValidAgentMessage } = require('./schema');

const PORT = process.env.PORT || 8080;
const wss = new WebSocket.Server({ port: PORT });

console.log(`WebSocket server listening on ws://localhost:${PORT}`);

wss.on('connection', (socket, req) => {
  console.log('Client connected:', req.socket.remoteAddress);

  socket.on('message', (data) => {
    let parsed;
    try {
      parsed = JSON.parse(data.toString());
    } catch (err) {
      console.error('Invalid JSON received:', err.message);
      return;
    }

    if (!isValidAgentMessage(parsed)) {
      console.warn('Message does not match agent schema, ignoring:', parsed);
      return;
    }

    console.log('Valid agent update:', parsed);
    // Later: broadcast this to other connected clients (Three.js frontend etc.)
  });

  socket.on('close', () => {
    console.log('Client disconnected');
  });

  socket.on('error', (err) => {
    console.error('Socket error:', err.message);
  });

  // Send a test payload using the schema, so we can verify shape end-to-end
  const testMessage = createAgentMessage({ id: 'drone-1', x: 0, y: 0, z: 0 });
  socket.send(JSON.stringify(testMessage));
});

wss.on('error', (err) => {
  console.error('Server error:', err.message);
});