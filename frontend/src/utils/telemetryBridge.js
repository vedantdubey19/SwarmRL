/**
 * SwarmRL Real-Data Ingestion Bridge (Day 11)
 * Normalizes, validates, and de-skews high-frequency RL telemetry batches.
 */

export class TelemetryBridge {
  constructor(options = {}) {
    this.maxHistory = options.maxHistory || 100;
    this.lastPacketTimestamp = 0;
    this.jitterSamples = [];
  }

  /**
   * Sanitizes raw RL inference state dictionaries into clean render nodes.
   */
  normalizeAgentState(raw) {
    if (!raw || typeof raw !== 'object') return null;

    const id = raw.id || `agent-${String(raw.agent_id || 0).padStart(2, '0')}`;
    const x = Number(raw.x ?? raw.pos_x ?? 0);
    const y = Number(raw.y ?? raw.pos_y ?? 0);
    const z = Number(raw.z ?? raw.pos_z ?? 0);
    const yaw = Number(raw.yaw ?? raw.heading ?? 0);
    const collision = Boolean(raw.collision ?? raw.is_colliding ?? false);
    const reward = Number(raw.reward ?? 0);
    const timestamp = Number(raw.timestamp ?? Date.now());

    return {
      id,
      x: isNaN(x) ? 0 : x,
      y: isNaN(y) ? 0 : y,
      z: isNaN(z) ? 0 : z,
      yaw: isNaN(yaw) ? 0 : yaw,
      collision,
      reward,
      timestamp,
      targetPos: [x, y, z],
      targetYaw: yaw,
    };
  }

  /**
   * Ingests a raw network batch, cleans entries, and computes jitter.
   */
  processBatch(rawBatch) {
    if (!Array.isArray(rawBatch)) return { validNodes: [], jitterMs: 0 };

    const now = Date.now();
    let jitter = 0;

    if (this.lastPacketTimestamp > 0) {
      const delta = now - this.lastPacketTimestamp;
      jitter = Math.abs(delta - 50); // Delta relative to expected 20Hz (50ms) interval
      this.jitterSamples.push(jitter);
      if (this.jitterSamples.length > this.maxHistory) {
        this.jitterSamples.shift();
      }
    }
    this.lastPacketTimestamp = now;

    const validNodes = [];
    for (let i = 0; i < rawBatch.length; i++) {
      const node = this.normalizeAgentState(rawBatch[i]);
      if (node) validNodes.push(node);
    }

    const avgJitter =
      this.jitterSamples.length > 0
        ? Math.round(
            this.jitterSamples.reduce((a, b) => a + b, 0) /
              this.jitterSamples.length
          )
        : 0;

    return { validNodes, avgJitter };
  }
}

export const globalTelemetryBridge = new TelemetryBridge();