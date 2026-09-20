const WebSocket = require('ws');
const {
  isValidTelemetryFrame,
  isValidGridDeltaMessage,
  isValidControlMessage,
  isValidRegisterMessage,
  isValidAgentMessage,
} = require('./schema');

const PORT = process.env.PORT || 8080;

const publishers = new Set();
const subscribers = new Set();

function createServer(port = PORT) {
  const wss = new WebSocket.Server({ port });

  function broadcast(data, filterFn) {
    const payload = typeof data === 'string' ? data : JSON.stringify(data);
    for (const client of wss.clients) {
      if (client.readyState === WebSocket.OPEN && (!filterFn || filterFn(client))) {
        try {
          client.send(payload);
        } catch (err) {
          console.error('Error broadcasting to client:', err.message);
        }
      }
    }
  }

  wss.on('listening', () => {
    console.log(`WebSocket server listening on ws://localhost:${port}`);
  });

  wss.on('connection', (socket, req) => {
    socket.role = null;
    const remote = req && req.socket ? req.socket.remoteAddress : 'unknown';
    console.log('Client connected:', remote);

    socket.on('message', (data) => {
      let parsed;
      try {
        parsed = JSON.parse(data.toString());
      } catch (err) {
        console.error('Invalid JSON received:', err.message);
        socket.send(
          JSON.stringify({ type: 'error', message: 'Invalid JSON payload' })
        );
        return;
      }

      if (typeof parsed !== 'object' || parsed === null) {
        socket.send(
          JSON.stringify({ type: 'error', message: 'Message payload must be an object' })
        );
        return;
      }

      // Handle handshake registration
      if (parsed.type === 'register') {
        if (!isValidRegisterMessage(parsed)) {
          console.warn('Invalid register message:', parsed);
          socket.send(
            JSON.stringify({
              type: 'error',
              message: 'Invalid registration message: role must be "publisher" or "subscriber"',
            })
          );
          return;
        }

        publishers.delete(socket);
        subscribers.delete(socket);

        socket.role = parsed.role;
        if (parsed.role === 'publisher') {
          publishers.add(socket);
        } else {
          subscribers.add(socket);
        }

        socket.send(
          JSON.stringify({
            type: 'registered',
            role: socket.role,
            status: 'ready',
          })
        );
        return;
      }

      // Handle batched telemetry frame
      if (parsed.type === 'frame') {
        if (!isValidTelemetryFrame(parsed)) {
          console.warn('Invalid frame message received:', parsed);
          socket.send(
            JSON.stringify({
              type: 'error',
              message: 'Message failed telemetry frame schema validation',
            })
          );
          return;
        }

        // Broadcast to all subscribers (or clients not registered as publisher)
        broadcast(
          data.toString(),
          (client) => subscribers.has(client) || (!client.role && client !== socket)
        );
        return;
      }

      // Handle exploration grid delta
      if (parsed.type === 'grid_delta') {
        if (!isValidGridDeltaMessage(parsed)) {
          console.warn('Invalid grid_delta message received:', parsed);
          socket.send(
            JSON.stringify({
              type: 'error',
              message: 'Message failed grid_delta schema validation',
            })
          );
          return;
        }

        broadcast(
          data.toString(),
          (client) => subscribers.has(client) || (!client.role && client !== socket)
        );
        return;
      }

      // Handle simulation control uplink (Frontend -> Engine)
      if (parsed.type === 'control') {
        if (!isValidControlMessage(parsed)) {
          console.warn('Invalid control message received:', parsed);
          socket.send(
            JSON.stringify({
              type: 'error',
              message: 'Message failed control schema validation',
            })
          );
          return;
        }

        // Forward to registered publishers
        broadcast(data.toString(), (client) => publishers.has(client));

        // Acknowledge control command back to sender
        socket.send(
          JSON.stringify({
            type: 'control_ack',
            action: parsed.action,
            status: 'ok',
          })
        );
        return;
      }

      // Backward compatibility: Legacy single-agent message
      if (isValidAgentMessage(parsed)) {
        broadcast(
          data.toString(),
          (client) => subscribers.has(client) || (!client.role && client !== socket)
        );
        return;
      }

      // Unknown or unhandled message type
      console.warn('Unrecognized message schema:', parsed);
      socket.send(
        JSON.stringify({
          type: 'error',
          message: 'Message failed schema validation: unknown type or format',
        })
      );
    });

    socket.on('close', (code, reason) => {
      publishers.delete(socket);
      subscribers.delete(socket);
      console.log(`Client disconnected (code: ${code}, reason: ${reason || 'none'})`);
    });

    socket.on('error', (err) => {
      publishers.delete(socket);
      subscribers.delete(socket);
      console.error('Socket error:', err.message);
    });
  });

  return wss;
}

let serverInstance = null;
if (require.main === module) {
  serverInstance = createServer(PORT);

  serverInstance.on('error', (err) => {
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