const WebSocket = require('ws');

const DEFAULT_PORT = 8080;
const DEFAULT_HOST = '0.0.0.0';
const MAX_BUFFERED_AMOUNT = 1024 * 512; // 512 KB

function createRelayServer(port = null, host = null, onReady = null) {
  const serverPort = port !== null ? port : parseInt(process.env.PORT || process.env.WS_PORT || DEFAULT_PORT, 10);
  const serverHost = host || process.env.HOST || process.env.WS_HOST || DEFAULT_HOST;

  const wss = new WebSocket.Server({ port: serverPort, host: serverHost }, () => {
    if (onReady) onReady(wss);
  });

  const publishers = new Set();
  const subscribers = new Set();

  let latestWorld = null;
  let latestGridSnapshot = null;

  wss.on('connection', (socket) => {
    socket.role = 'subscriber';
    subscribers.add(socket);
    socket.isAlive = true;

    // Send cached state to late joiners
    if (latestWorld) {
      try {
        socket.send(JSON.stringify(latestWorld));
      } catch (err) {}
    }
    if (latestGridSnapshot) {
      try {
        socket.send(JSON.stringify(latestGridSnapshot));
      } catch (err) {}
    }

    socket.on('pong', () => {
      socket.isAlive = true;
    });

    socket.on('message', (rawData) => {
      let msg;
      try {
        msg = JSON.parse(rawData.toString());
      } catch (err) {
        return;
      }

      if (!msg || typeof msg !== 'object') return;

      if (msg.type === 'register') {
        if (msg.role === 'publisher') {
          subscribers.delete(socket);
          publishers.add(socket);
          socket.role = 'publisher';
        } else {
          publishers.delete(socket);
          subscribers.add(socket);
          socket.role = 'subscriber';
        }
        return;
      }

      if (msg.type === 'world') {
        latestWorld = msg;
      } else if (msg.type === 'grid_snapshot') {
        latestGridSnapshot = msg;
      }

      // Forward to subscribers with backpressure / slow subscriber protection
      const payload = typeof rawData === 'string' ? rawData : JSON.stringify(msg);
      for (const sub of subscribers) {
        if (sub.readyState === WebSocket.OPEN) {
          if (sub.bufferedAmount > MAX_BUFFERED_AMOUNT) {
            // Drop frame for slow subscriber to avoid unbounded queueing
            continue;
          }
          try {
            sub.send(payload);
          } catch (err) {}
        }
      }
    });

    socket.on('close', () => {
      publishers.delete(socket);
      subscribers.delete(socket);
    });

    socket.on('error', () => {
      publishers.delete(socket);
      subscribers.delete(socket);
    });
  });

  const heartbeat = setInterval(() => {
    wss.clients.forEach((ws) => {
      if (!ws.isAlive) {
        return ws.terminate();
      }
      ws.isAlive = false;
      ws.ping();
    });
  }, 10000);
  heartbeat.unref();

  return {
    wss,
    close: () => {
      clearInterval(heartbeat);
      return new Promise((resolve) => wss.close(resolve));
    },
    getCachedWorld: () => latestWorld,
    getCachedGridSnapshot: () => latestGridSnapshot,
    subscribers,
    publishers,
  };
}

if (require.main === module) {
  const relay = createRelayServer(null, null, (wss) => {
    const p = wss.address().port;
    console.log(`SwarmRL WebSocket Relay running on ws://${DEFAULT_HOST}:${p}`);
  });
}

module.exports = { createRelayServer };
