// schema.js
// Defines the wire schema, serialization helpers, and validation logic
// for SwarmRL WebSocket telemetry, exploration grids, and simulation control.

const SCHEMA_VERSION = 1;

const VALID_ROLES = new Set(['publisher', 'subscriber']);
const VALID_DRONE_STATUSES = new Set([
  'active',
  'collided_drone',
  'collided_obstacle',
  'out_of_bounds',
]);
const VALID_CONTROL_ACTIONS = new Set([
  'play',
  'pause',
  'step',
  'reset',
  'set_rate',
]);

/**
 * Validates a 3D coordinate vector [x, y, z].
 */
function isValidVec3(vec) {
  return (
    Array.isArray(vec) &&
    vec.length === 3 &&
    vec.every((val) => typeof val === 'number' && Number.isFinite(val))
  );
}

/**
 * Validates a quaternion [qx, qy, qz, qw].
 */
function isValidQuat(rot) {
  return (
    Array.isArray(rot) &&
    rot.length === 4 &&
    rot.every((val) => typeof val === 'number' && Number.isFinite(val))
  );
}

/**
 * Validates a single sensor detection item: { id, type, dist, angle }
 */
function isValidDetection(det) {
  return (
    typeof det === 'object' &&
    det !== null &&
    (typeof det.id === 'string' || typeof det.id === 'number') &&
    typeof det.type === 'string' &&
    typeof det.dist === 'number' &&
    Number.isFinite(det.dist) &&
    typeof det.angle === 'number' &&
    Number.isFinite(det.angle)
  );
}

/**
 * Validates an individual drone state within a telemetry frame.
 */
function isValidDroneState(drone) {
  if (typeof drone !== 'object' || drone === null) return false;
  if (typeof drone.id !== 'number' && typeof drone.id !== 'string') return false;
  if (!isValidVec3(drone.pos)) return false;

  // Optional vel (if provided, must be vec3)
  if (typeof drone.vel !== 'undefined' && !isValidVec3(drone.vel)) return false;

  // Heading or rot
  if (
    typeof drone.heading !== 'undefined' &&
    (typeof drone.heading !== 'number' || !Number.isFinite(drone.heading))
  ) {
    return false;
  }
  if (typeof drone.rot !== 'undefined' && !isValidQuat(drone.rot)) {
    return false;
  }

  // Status enum
  if (
    typeof drone.status !== 'undefined' &&
    !VALID_DRONE_STATUSES.has(drone.status)
  ) {
    return false;
  }

  // Detections array
  if (typeof drone.detections !== 'undefined') {
    if (
      !Array.isArray(drone.detections) ||
      !drone.detections.every(isValidDetection)
    ) {
      return false;
    }
  }

  return true;
}

/**
 * Helper to construct a single drone telemetry entry.
 */
function createDroneState({
  id,
  agent_id,
  pos,
  vel = [0, 0, 0],
  heading = 0,
  rot = [0, 0, 0, 1],
  status = 'active',
  detections = [],
}) {
  return {
    id,
    agent_id: agent_id || (typeof id === 'number' ? `drone_${id}` : String(id)),
    pos,
    vel,
    heading,
    rot,
    status,
    detections,
  };
}

/**
 * Validates a target entry: { id, pos: [x, y, z], found: boolean }
 */
function isValidTarget(target) {
  if (typeof target !== 'object' || target === null) return false;
  if (typeof target.id !== 'number' && typeof target.id !== 'string') return false;
  if (!isValidVec3(target.pos)) return false;
  if (typeof target.found !== 'boolean') return false;
  return true;
}

/**
 * Constructs an atomic per-tick telemetry frame for the entire swarm.
 */
function createTelemetryFrame({
  step,
  timestamp,
  sim_time,
  metrics = {},
  drones = [],
  targets = [],
  version = SCHEMA_VERSION,
}) {
  return {
    version,
    type: 'frame',
    step,
    timestamp: typeof timestamp === 'number' ? timestamp : Date.now(),
    sim_time:
      typeof sim_time === 'number'
        ? sim_time
        : Number(((step || 0) * 0.05).toFixed(3)),
    metrics: {
      explored_fraction: metrics.explored_fraction ?? 0.0,
      active_drones:
        metrics.active_drones ??
        drones.filter((d) => (d.status || 'active') === 'active').length,
      targets_found:
        metrics.targets_found ?? targets.filter((t) => t.found).length,
      total_targets: metrics.total_targets ?? targets.length,
      step_reward_sum: metrics.step_reward_sum ?? 0.0,
      ...metrics,
    },
    drones,
    targets,
  };
}

/**
 * Validates an atomic telemetry frame payload.
 */
function isValidTelemetryFrame(msg) {
  if (typeof msg !== 'object' || msg === null) return false;
  if (msg.type !== 'frame') return false;
  if (
    typeof msg.step !== 'number' ||
    !Number.isInteger(msg.step) ||
    msg.step < 0
  ) {
    return false;
  }
  if (typeof msg.timestamp !== 'number' || !Number.isFinite(msg.timestamp)) {
    return false;
  }
  if (
    typeof msg.sim_time !== 'undefined' &&
    (typeof msg.sim_time !== 'number' || !Number.isFinite(msg.sim_time))
  ) {
    return false;
  }
  if (
    typeof msg.metrics !== 'undefined' &&
    (typeof msg.metrics !== 'object' || msg.metrics === null)
  ) {
    return false;
  }
  if (!Array.isArray(msg.drones) || !msg.drones.every(isValidDroneState)) {
    return false;
  }
  if (typeof msg.targets !== 'undefined') {
    if (!Array.isArray(msg.targets) || !msg.targets.every(isValidTarget)) {
      return false;
    }
  }
  return true;
}

/**
 * Sparse exploration grid delta message.
 */
function createGridDeltaMessage({
  step,
  new_cells = [],
  version = SCHEMA_VERSION,
}) {
  return {
    version,
    type: 'grid_delta',
    step,
    new_cells,
  };
}

function isValidGridDeltaMessage(msg) {
  if (typeof msg !== 'object' || msg === null) return false;
  if (msg.type !== 'grid_delta') return false;
  if (
    typeof msg.step !== 'number' ||
    !Number.isInteger(msg.step) ||
    msg.step < 0
  ) {
    return false;
  }
  if (!Array.isArray(msg.new_cells)) return false;
  return msg.new_cells.every(
    (cell) =>
      Array.isArray(cell) &&
      cell.length === 2 &&
      typeof cell[0] === 'number' &&
      Number.isInteger(cell[0]) &&
      typeof cell[1] === 'number' &&
      Number.isInteger(cell[1])
  );
}

/**
 * Simulation control uplink message (Frontend -> Server/Engine).
 */
function createControlMessage({
  action,
  params = {},
  version = SCHEMA_VERSION,
}) {
  return {
    version,
    type: 'control',
    action,
    params,
  };
}

function isValidControlMessage(msg) {
  if (typeof msg !== 'object' || msg === null) return false;
  if (msg.type !== 'control') return false;
  if (typeof msg.action !== 'string' || !VALID_CONTROL_ACTIONS.has(msg.action)) {
    return false;
  }
  if (
    typeof msg.params !== 'undefined' &&
    (typeof msg.params !== 'object' || msg.params === null)
  ) {
    return false;
  }
  return true;
}

/**
 * Client registration message for pub/sub handshake.
 */
function createRegisterMessage({ role, version = SCHEMA_VERSION }) {
  return {
    version,
    type: 'register',
    role,
  };
}

function isValidRegisterMessage(msg) {
  if (typeof msg !== 'object' || msg === null) return false;
  if (msg.type !== 'register') return false;
  return VALID_ROLES.has(msg.role);
}

/**
 * Backward compatibility: legacy single-agent position message.
 */
function createAgentMessage({ id, x, y, z, timestamp }) {
  return {
    id,
    x,
    y,
    z,
    timestamp: timestamp || Date.now(),
  };
}

function isValidAgentMessage(msg) {
  return (
    typeof msg === 'object' &&
    msg !== null &&
    typeof msg.id !== 'undefined' &&
    typeof msg.x === 'number' &&
    Number.isFinite(msg.x) &&
    typeof msg.y === 'number' &&
    Number.isFinite(msg.y) &&
    typeof msg.z === 'number' &&
    Number.isFinite(msg.z) &&
    typeof msg.timestamp === 'number' &&
    Number.isFinite(msg.timestamp)
  );
}

module.exports = {
  SCHEMA_VERSION,
  VALID_ROLES,
  VALID_DRONE_STATUSES,
  VALID_CONTROL_ACTIONS,
  createDroneState,
  isValidDroneState,
  createTelemetryFrame,
  isValidTelemetryFrame,
  createGridDeltaMessage,
  isValidGridDeltaMessage,
  createControlMessage,
  isValidControlMessage,
  createRegisterMessage,
  isValidRegisterMessage,
  createAgentMessage,
  isValidAgentMessage,
};