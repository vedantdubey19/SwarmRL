import * as THREE from 'three';

/**
 * Normalizes an angle into (-PI, PI] for shortest-path angular lerping.
 */
function normalizeAngle(angle) {
  let a = angle % (Math.PI * 2);
  if (a > Math.PI) a -= Math.PI * 2;
  if (a <= -Math.PI) a += Math.PI * 2;
  return a;
}

export class SwarmSyncBuffer {
  constructor(tickIntervalMs = 50) {
    this.tickInterval = tickIntervalMs;
    this.previousSnapshots = new Map();
    this.targetSnapshots = new Map();
    this.lastPacketTime = performance.now();
  }

  pushBatch(batch) {
    const now = performance.now();
    this.lastPacketTime = now;

    batch.forEach((agent) => {
      const currentTarget = this.targetSnapshots.get(agent.id);

      if (currentTarget) {
        this.previousSnapshots.set(agent.id, { ...currentTarget });
      } else {
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
        collision: Boolean(agent.collision),
        timestamp: now,
      });
    });
  }

  getInterpolatedState(agentId) {
    const prev = this.previousSnapshots.get(agentId);
    const target = this.targetSnapshots.get(agentId);

    if (!target) return null;
    if (!prev) return target;

    // Strict clamping of alpha between [0.0, 1.0] to prevent extrapolation slingshots
    const elapsed = performance.now() - this.lastPacketTime;
    const alpha = Math.min(Math.max(elapsed / this.tickInterval, 0.0), 1.0);

    // Linear spatial lerp
    const x = THREE.MathUtils.lerp(prev.x, target.x, alpha);
    const y = THREE.MathUtils.lerp(prev.y, target.y, alpha);
    const z = THREE.MathUtils.lerp(prev.z, target.z, alpha);

    // Shortest-arc angular lerp (prevents 360-degree flip glitch on boundary wraps)
    const prevYaw = normalizeAngle(prev.yaw);
    const targetYaw = normalizeAngle(target.yaw);
    const yaw = THREE.MathUtils.lerpAngle(prevYaw, targetYaw, alpha);

    return {
      x,
      y,
      z,
      yaw,
      collision: target.collision,
    };
  }

  clear() {
    this.previousSnapshots.clear();
    this.targetSnapshots.clear();
  }
}

export const globalSyncBuffer = new SwarmSyncBuffer(50);