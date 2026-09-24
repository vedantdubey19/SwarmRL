const WebSocket = require('ws');
const {
  isValidTelemetryFrame,
  isValidGridDeltaMessage,
  isValidControlMessage,
  isValidRegisterMessage,
  isValidAgentMessage,
} = require('./schema');

const PORT = process.env.PORT || 8080;

const wss = new WebSocket.Server({ port: PORT });
const clients = new Set();

function createServer(port = PORT) {
  const wss = new WebSocket.Server({ port });

wss.on('connection', (socket, req) => {
  clients.add(socket);
  console.log(`Client connected: ${req.socket.remoteAddress} (total: ${clients.size})`);

  // Heartbeat tracking to detect dead connections
  socket.isAlive = true;
  socket.on('pong', () => {
    socket.isAlive = true;
  });

  socket.on('message', (data) => {
    let parsed;
    try {
      parsed = JSON.parse(data.toString());
    } catch (err) {
      console.error('Invalid JSON received:', err.message);
      socket.send(JSON.stringify({ type: 'error', message: 'Invalid JSON payload' }));
      return;
    }

    if (parsed.type === 'batch_update') {
      console.log(`Received batch: step ${parsed.step}, ${parsed.agents.length} agents`);
      return;
    }
  }

    if (!isValidAgentMessage(parsed)) {
      console.warn('Message does not match agent schema, ignoring:', parsed);
      socket.send(JSON.stringify({ type: 'error', message: 'Message failed schema validation' }));
      return;
    }

    console.log(`WebSocket server listening on ws://localhost:${port}`);
  });

  socket.on('close', (code, reason) => {
    clients.delete(socket);
    console.log(`Client disconnected (code: ${code}, reason: ${reason || 'none'}) (total: ${clients.size})`);
  });

  socket.on('error', (err) => {
    console.error('Socket error:', err.message);
    clients.delete(socket);
  });

  return wss;
}

// Ping clients every 30s to detect dead connections that didn't fire 'close'
const heartbeatInterval = setInterval(() => {
  wss.clients.forEach((socket) => {
    if (socket.isAlive === false) {
      console.log('Terminating unresponsive client');
      clients.delete(socket);
      return socket.terminate();
    }
    socket.isAlive = false;
    socket.ping();
  });
}, 30000);

wss.on('close', () => {
  clearInterval(heartbeatInterval);
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
}

module.exports = { createServer, publishers, subscribers };