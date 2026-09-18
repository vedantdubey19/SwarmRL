// schema.js
// Defines the structure of per-agent position updates streamed over WebSocket

function createAgentMessage({ id, x, y, z, timestamp }) {
  return {
    id,               // unique agent/drone identifier
    x, y, z,          // 3D position coordinates
    timestamp: timestamp || Date.now(),
  };
}

function isValidAgentMessage(msg) {
  return (
    typeof msg.id !== 'undefined' &&
    typeof msg.x === 'number' &&
    typeof msg.y === 'number' &&
    typeof msg.z === 'number' &&
    typeof msg.timestamp === 'number'
  );
}

module.exports = { createAgentMessage, isValidAgentMessage };