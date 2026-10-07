const WebSocket = require('ws');
const {
  isValidTelemetryFrame,
  isValidGridDeltaMessage,
  isValidControlMessage,
  isValidRegisterMessage,
  isValidAgentMessage,
} = require('./schema');

const { WS_HOST, WS_PORT } = require('./config');

const PORT = WS_PORT;
const HOST = WS_HOST;

const clients = new Set();
const publishers = new Set();
const subscribers = new Set();

function createServer(port = PORT, host = HOST) {
  const serverOptions = { port };
  if (host && host !== '0.0.0.0') {
    serverOptions.host = host;
  }
  const wss = new WebSocket.Server(serverOptions);

  wss.on('connection', (socket, req) => {
    clients.add(socket);
    socket.isAlive = true;

    socket.on('pong', () => {
      socket.isAlive = true;
    });

    socket.on('message', (data) => {
      let parsed;
      try {
        parsed = JSON.parse(data.toString());
      } catch (err) {
        socket.send(JSON.stringify({ type: 'error', message: 'Invalid JSON payload' }));
        return;
      }

      if (parsed.type === 'register') {
        if (parsed.role === 'publisher') {
          publishers.add(socket);
          socket.send(JSON.stringify({ type: 'registered', role: 'publisher' }));
          return;
        }
        if (parsed.role === 'subscriber') {
          subscribers.add(socket);
          socket.send(JSON.stringify({ type: 'registered', role: 'subscriber' }));
          return;
        }
        socket.send(JSON.stringify({ type: 'error', message: 'Unknown registration role' }));
        return;
      }

      if (parsed.type === 'frame' || parsed.type === 'batch_update' || parsed.type === 'grid_delta') {
        const rawPayload = typeof data === 'string' ? data : data.toString();
        for (const sub of subscribers) {
          if (sub.readyState === WebSocket.OPEN) {
            sub.send(rawPayload);
          }
        }
        return;
      }

      if (isValidAgentMessage(parsed)) {
        const rawPayload = typeof data === 'string' ? data : data.toString();
        for (const sub of subscribers) {
          if (sub.readyState === WebSocket.OPEN) {
            sub.send(rawPayload);
          }
        }
        return;
      }

      socket.send(JSON.stringify({ type: 'error', message: 'Message failed schema validation' }));
    });

    socket.on('close', () => {
      clients.delete(socket);
      publishers.delete(socket);
      subscribers.delete(socket);
    });

    socket.on('error', () => {
      clients.delete(socket);
      publishers.delete(socket);
      subscribers.delete(socket);
    });
  });

  const heartbeatInterval = setInterval(() => {
    wss.clients.forEach((socket) => {
      if (socket.isAlive === false) {
        clients.delete(socket);
        publishers.delete(socket);
        subscribers.delete(socket);
        return socket.terminate();
      }
      socket.isAlive = false;
      socket.ping();
    });
  }, 30000);

  wss.on('close', () => {
    clearInterval(heartbeatInterval);
  });

  return wss;
}

if (require.main === module) {
  const server = createServer(PORT, HOST);
  server.on('listening', () => {
    const displayHost = HOST || 'localhost';
    console.log(`WebSocket server listening on ws://${displayHost}:${PORT}`);
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

module.exports = { createServer, publishers, subscribers };