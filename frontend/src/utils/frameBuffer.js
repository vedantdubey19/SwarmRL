import * as THREE from 'three';

/**
 * Checks whether an incoming frame should be dropped due to being out-of-order.
 * Frames must arrive in strictly non-decreasing step order, and for the same step,
 * increasing timestamp order.
 *
 * @param {object} incomingFrame
 * @param {object | null} lastAcceptedFrame
 * @returns {boolean} True if frame should be dropped
 */
export function shouldDropFrame(incomingFrame, lastAcceptedFrame) {
  if (!lastAcceptedFrame) return false;
  if (!incomingFrame) return true;

  const inStep = incomingFrame.step ?? 0;
  const lastStep = lastAcceptedFrame.step ?? 0;

  if (inStep < lastStep) {
    return true;
  }

  if (inStep === lastStep) {
    const inTime = incomingFrame.timestamp ?? 0;
    const lastTime = lastAcceptedFrame.timestamp ?? 0;
    if (inTime <= lastTime) {
      return true;
    }
  }

  return false;
}

/**
 * Transforms simulation heading angle (rad) into Three.js Euler rotation Y.
 * In the simulation: heading 0 rad is along +X in the X-Z plane, +Y is up.
 * In Three.js default mesh facing: forward is along +Z (or -Z).
 * Specification: rotation.y = -heading + Math.PI / 2
 *
 * @param {number} heading - Heading in radians [ -pi, pi ]
 * @returns {number} Three.js Euler angle around Y axis
 */
export function headingToThreeRotationY(heading) {
  return -heading + Math.PI / 2;
}

/**
 * Linearly interpolates between two numbers.
 */
export function lerp(a, b, t) {
  return a + (b - a) * t;
}

/**
 * Interpolates two angles in radians taking shortest angular distance.
 */
export function lerpAngle(a, b, t) {
  let diff = (b - a) % (2 * Math.PI);
  if (diff < -Math.PI) diff += 2 * Math.PI;
  if (diff > Math.PI) diff -= 2 * Math.PI;
  return a + diff * t;
}

const _qA = new THREE.Quaternion();
const _qB = new THREE.Quaternion();

/**
 * Slerps between two quaternions represented as [x, y, z, w].
 * Returns [x, y, z, w].
 */
export function slerpQuat(qA, qB, t) {
  _qA.set(qA[0], qA[1], qA[2], qA[3]);
  _qB.set(qB[0], qB[1], qB[2], qB[3]);
  _qA.slerp(_qB, t);
  return [_qA.x, _qA.y, _qA.z, _qA.w];
}

/**
 * Interpolates a collection of drones between two telemetry frames.
 *
 * @param {Array<object>} prevDrones
 * @param {Array<object>} currDrones
 * @param {number} alpha - Interpolation factor in [0, 1]
 * @returns {Array<object>} Interpolated drone objects
 */
export function interpolateDrones(prevDrones, currDrones, alpha) {
  if (!currDrones || currDrones.length === 0) return [];
  if (!prevDrones || prevDrones.length === 0 || alpha >= 1.0) {
    return currDrones.map((d) => ({
      ...d,
      interpolatedPosition: [...d.position],
      interpolatedRotationY: headingToThreeRotationY(d.heading ?? 0),
    }));
  }

  const prevMap = new Map();
  for (const d of prevDrones) {
    const key = d.id !== undefined ? d.id : d.agent_id;
    prevMap.set(key, d);
  }

  const clampedAlpha = Math.max(0.0, Math.min(1.0, alpha));

  return currDrones.map((curr) => {
    const key = curr.id !== undefined ? curr.id : curr.agent_id;
    const prev = prevMap.get(key);

    if (!prev) {
      return {
        ...curr,
        interpolatedPosition: [...curr.position],
        interpolatedRotationY: headingToThreeRotationY(curr.heading ?? 0),
      };
    }

    const pX = lerp(prev.position[0], curr.position[0], clampedAlpha);
    const pY = lerp(prev.position[1], curr.position[1], clampedAlpha);
    const pZ = lerp(prev.position[2], curr.position[2], clampedAlpha);

    const prevRotY = headingToThreeRotationY(prev.heading ?? 0);
    const currRotY = headingToThreeRotationY(curr.heading ?? 0);
    const rotY = lerpAngle(prevRotY, currRotY, clampedAlpha);

    let interpQuat = curr.quaternion;
    if (prev.quaternion && curr.quaternion) {
      interpQuat = slerpQuat(prev.quaternion, curr.quaternion, clampedAlpha);
    }

    return {
      ...curr,
      interpolatedPosition: [pX, pY, pZ],
      interpolatedRotationY: rotY,
      interpolatedQuaternion: interpQuat,
    };
  });
}

/**
 * Mutable FrameBuffer for smooth rendering without React state churn.
 */
export class FrameBuffer {
  constructor() {
    this.previousFrame = null;
    this.currentFrame = null;
    this.prevTimestamp = 0;
    this.currTimestamp = 0;
    this.interpDuration = 33.3; // Expected ~30 Hz frame interval (ms)
  }

  pushFrame(frame) {
    if (shouldDropFrame(frame, this.currentFrame)) {
      return false;
    }

    const now = performance.now();
    this.previousFrame = this.currentFrame;
    this.prevTimestamp = this.currTimestamp || now;
    this.currentFrame = frame;
    this.currTimestamp = now;

    if (this.previousFrame) {
      const dt = this.currTimestamp - this.prevTimestamp;
      if (dt > 5 && dt < 200) {
        this.interpDuration = dt;
      }
    }

    return true;
  }

  getInterpolatedDrones(now = performance.now()) {
    if (!this.currentFrame) return [];
    if (!this.previousFrame) {
      return interpolateDrones(null, this.currentFrame.drones, 1.0);
    }

    const elapsed = now - this.currTimestamp;
    const alpha = this.interpDuration > 0 ? Math.min(1.0, elapsed / this.interpDuration) : 1.0;
    return interpolateDrones(this.previousFrame.drones, this.currentFrame.drones, alpha);
  }
}
