/**
 * SwarmRL High-Frequency Telemetry Sync Buffer (Day 12)
 * Eliminates packet stutter via delta-time spatial interpolation.
 */

export class SwarmSyncBuffer {
  constructor(tickIntervalMs = 50) {
    this.tickInterval = tickIntervalMs;
    this.previousSnapshots = new Map();
    this.targetSnapshots = new Map();
    this.lastPacketTime = performance.now();
  }

  /**
   * Pushes a new batch of 50 agent positions from the WebSocket stream.
   */
  pushBatch(batch) {
    const now = performance.now();
    this.lastPacketTime = now;

    batch.forEach((agent) => {
      const currentTarget = this.targetSnapshots.get(agent.id);

      if (currentTarget) {
        // Shift current target to previous snapshot
        this.previousSnapshots.set(agent.id, { ...currentTarget });
      } else {
        // First initialization for this agent
        this.previousSnapshots.set(agent.id, {
          x: agent.x,
          y: agent.y,
          z: agent.z,
          yaw: agent.yaw || 0,
        });
      }

      this.targetSnapshots.set(agent.id, {
        x: agent.x,
        y: agent.y,
        z: agent.z,
        yaw: agent.yaw || 0,
        collision: agent.collision || false,
        timestamp: now,
      });
    });
  }

  /**
   * Evaluates the interpolated position for an agent at the current render frame.
   * @param {string} agentId
   * @returns {{x: number, y: number, z: number, yaw: number, collision: boolean} | null}
   */
  getInterpolatedState(agentId) {
    const prev = this.previousSnapshots.get(agentId);
    const target = this.targetSnapshots.get(agentId);

    if (!target) return null;
    if (!prev) return target;

    // Compute progress ratio (alpha) between network ticks
    const elapsed = performance.now() - this.lastPacketTime;
    const alpha = Math.min(Math.max(elapsed / this.tickInterval, 0.0), 1.0);

    // Smooth linear interpolation (lerp)
    return {
      x: prev.x + (target.x - prev.x) * alpha,
      y: prev.y + (target.y - prev.y) * alpha,
      z: prev.z + (target.z - prev.z) * alpha,
      yaw: prev.yaw + (target.yaw - prev.yaw) * alpha,
      collision: target.collision,
    };
  }

  clear() {
    this.previousSnapshots.clear(this.targetSnapshots.clear());
  }
}

export const globalSyncBuffer = new SwarmSyncBuffer(50);