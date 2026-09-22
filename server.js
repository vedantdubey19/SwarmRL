const WebSocket = require('ws');
const { createAgentMessage, isValidAgentMessage } = require('./schema');

const PORT = process.env.PORT || 8080;

const wss = new WebSocket.Server({ port: PORT });

wss.on('listening', () => {
  console.log(`WebSocket server listening on ws://localhost:${PORT}`);
});

wss.on('connection', (socket, req) => {
  console.log('Client connected:', req.socket.remoteAddress);

  socket.on('message', (data) => {
    let parsed;
    try {
      parsed = JSON.parse(data.toString());
    } catch (err) {
      console.error('Invalid JSON received:', err.message);
      socket.send(JSON.stringify({ type: 'error', message: 'Invalid JSON payload' }));
      return;
    }

    // Handle batched per-step updates (Day 8 optimization)
    if (parsed.type === 'batch_update') {
      console.log(`Received batch: step ${parsed.step}, ${parsed.agents.length} agents`);
      return;
    }

    // Fallback: single-agent message validation (Day 2/3 behavior)
    if (!isValidAgentMessage(parsed)) {
      console.warn('Message does not match agent schema, ignoring:', parsed);
      socket.send(JSON.stringify({ type: 'error', message: 'Message failed schema validation' }));
      return;
    }

    console.log('Valid agent update:', parsed);
  });

  socket.on('close', (code, reason) => {
    console.log(`Client disconnected (code: ${code}, reason: ${reason || 'none'})`);
  });

  socket.on('error', (err) => {
    console.error('Socket error:', err.message);
  });

  try {
    const testMessage = createAgentMessage({ id: 'drone-1', x: 0, y: 0, z: 0 });
    socket.send(JSON.stringify(testMessage));
  } catch (err) {
    console.error('Failed to send initial test message:', err.message);
  }
});

wss.on('error', (err) => {
  if (err.code === 'EADDRINUSE') {
    console.error(`Port ${PORT} is already in use. Is another instance running?`);
  } else {
    console.error('Server error:', err.message);
  }
  process.exit(1);
});

process.on('uncaughtException', (err) => {
  console.error('Uncaught exception:', err);
});

process.on('unhandledRejection', (reason) => {
  console.error('Unhandled promise rejection:', reason);
});