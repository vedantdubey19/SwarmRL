import { describe, it, expect } from 'vitest';
import {
  shouldDropFrame,
  headingToThreeRotationY,
  lerp,
  lerpAngle,
  interpolateDrones,
  FrameBuffer,
} from '../utils/frameBuffer';

describe('frameBuffer utilities', () => {
  describe('shouldDropFrame', () => {
    it('accepts initial frame when lastAccepted is null', () => {
      expect(shouldDropFrame({ step: 10, timestamp: 1000 }, null)).toBe(false);
    });

    it('drops frame with older step count', () => {
      const last = { step: 50, timestamp: 2000 };
      const incoming = { step: 49, timestamp: 2050 };
      expect(shouldDropFrame(incoming, last)).toBe(true);
    });

    it('drops frame with same step count but older or equal timestamp', () => {
      const last = { step: 50, timestamp: 2000 };
      const duplicate = { step: 50, timestamp: 2000 };
      const olderTime = { step: 50, timestamp: 1999 };
      expect(shouldDropFrame(duplicate, last)).toBe(true);
      expect(shouldDropFrame(olderTime, last)).toBe(true);
    });

    it('accepts strictly newer step count', () => {
      const last = { step: 50, timestamp: 2000 };
      const nextStep = { step: 51, timestamp: 2033 };
      expect(shouldDropFrame(nextStep, last)).toBe(false);
    });

    it('accepts same step with newer timestamp', () => {
      const last = { step: 50, timestamp: 2000 };
      const newerTime = { step: 50, timestamp: 2010 };
      expect(shouldDropFrame(newerTime, last)).toBe(false);
    });
  });

  describe('headingToThreeRotationY', () => {
    it('matches simulation heading convention', () => {
      // In env: heading 0 rad points along +X in the X-Z plane, +Y is up.
      // In Three.js: rotation.y = -heading + Math.PI / 2
      expect(headingToThreeRotationY(0)).toBeCloseTo(Math.PI / 2, 5);
      expect(headingToThreeRotationY(Math.PI / 2)).toBeCloseTo(0, 5);
      expect(headingToThreeRotationY(-Math.PI / 2)).toBeCloseTo(Math.PI, 5);
      expect(headingToThreeRotationY(Math.PI)).toBeCloseTo(-Math.PI / 2, 5);
    });
  });

  describe('lerp and lerpAngle', () => {
    it('correctly interpolates numbers', () => {
      expect(lerp(10, 20, 0.5)).toBe(15);
      expect(lerp(0, 100, 0.25)).toBe(25);
    });

    it('interpolates angles along shortest path across wrap-around', () => {
      const angleA = Math.PI - 0.1;
      const angleB = -Math.PI + 0.1;
      const mid = lerpAngle(angleA, angleB, 0.5);
      expect(Math.abs(mid)).toBeCloseTo(Math.PI, 2);
    });
  });

  describe('interpolateDrones', () => {
    it('interpolates positions between two frames', () => {
      const prev = [
        { id: 0, position: [0, 0, 0], heading: 0, status: 'active' },
        { id: 1, position: [10, 5, 20], heading: 0, status: 'active' },
      ];
      const curr = [
        { id: 0, position: [10, 10, 10], heading: 0, status: 'active' },
        { id: 1, position: [20, 5, 40], heading: 0, status: 'active' },
      ];

      const interpolated = interpolateDrones(prev, curr, 0.5);
      expect(interpolated[0].interpolatedPosition).toEqual([5, 5, 5]);
      expect(interpolated[1].interpolatedPosition).toEqual([15, 5, 30]);
    });
  });

  describe('FrameBuffer class', () => {
    it('tracks incoming frames and drops duplicates', () => {
      const buffer = new FrameBuffer();
      expect(buffer.pushFrame({ step: 1, timestamp: 100, drones: [] })).toBe(true);
      expect(buffer.pushFrame({ step: 1, timestamp: 100, drones: [] })).toBe(false);
      expect(buffer.pushFrame({ step: 2, timestamp: 133, drones: [] })).toBe(true);
    });
  });
});
