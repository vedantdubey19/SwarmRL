const WebSocket = require('ws');
const {
  isValidTelemetryFrame,
  isValidGridDeltaMessage,
  isValidControlMessage,
  isValidRegisterMessage,
  isValidAgentMessage,
} = require('./schema');

const { WS_HOST, WS_PORT } = require('./config');

// Message types the server relays to every other connected client.
const RELAY_TYPES = new Set(['batch_update', 'grid_delta', 'env_event']);

function createServer(port = PORT) {
  const wss = new WebSocket.Server({ port });
  const clients = new Set();

  wss.on('listening', () => {
    console.log(`WebSocket server listening on ws://localhost:${port}`);
  });

  wss.on('connection', (socket, req) => {
    clients.add(socket);
    console.log(`Client connected: ${req.socket.remoteAddress} (total: ${clients.size})`);

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

      if (RELAY_TYPES.has(parsed.type)) {
        if (parsed.type === 'batch_update' && parsed.step % 50 === 0) {
          console.log(`Relaying batch: step ${parsed.step}`);
        }
        const payload = JSON.stringify(parsed);
        clients.forEach((client) => {
          if (client !== socket && client.readyState === WebSocket.OPEN) {
            client.send(payload);
          }
        });
        return;
      }

      if (!isValidAgentMessage(parsed)) {
        console.warn('Message does not match agent schema, ignoring:', parsed);
        socket.send(JSON.stringify({ type: 'error', message: 'Message failed schema validation' }));
        return;
      }

      console.log('Valid agent update:', parsed);
    });

    socket.on('close', (code, reason) => {
      clients.delete(socket);
      console.log(`Client disconnected (code: ${code}, reason: ${reason || 'none'}) (total: ${clients.size})`);
    });

    socket.on('error', (err) => {
      console.error('Socket error:', err.message);
      clients.delete(socket);
    });
  });

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
      console.error(`Port ${port} is already in use. Is another instance running?`);
    } else {
      console.error('Server error:', err.message);
    }
  });

  return wss;
}

if (require.main === module) {
  createServer(PORT);

  process.on('uncaughtException', (err) => {
    console.error('Uncaught exception:', err);
  });

  server.on('error', (err) => {
    if (err.code === 'EADDRINUSE') {
      console.error(`Port ${PORT} is already in use. Is another instance running?`);
    } else {
      console.error('Server error:', err.message);
    }
    process.exit(1);
  });
}

module.exports = { createServer };