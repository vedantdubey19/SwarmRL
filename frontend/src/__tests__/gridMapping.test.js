import { describe, it, expect } from 'vitest';
import {
  worldToCell,
  cellToWorld,
  createInitialGridBuffer,
  applyGridSnapshot,
  applyGridDelta,
  decodeBitmask,
  COLOR_UNEXPLORED,
  COLOR_EXPLORED,
} from '../utils/gridMapping';

describe('gridMapping utilities', () => {
  describe('worldToCell mapping', () => {
    it('maps center (0, 0) to cell (25, 25)', () => {
      const { ix, iz, index } = worldToCell(0, 0);
      expect(ix).toBe(25);
      expect(iz).toBe(25);
      expect(index).toBe(25 * 50 + 25);
    });

    it('maps bottom-left corner (-50, -50) to cell (0, 0)', () => {
      const { ix, iz, index } = worldToCell(-50, -50);
      expect(ix).toBe(0);
      expect(iz).toBe(0);
      expect(index).toBe(0);
    });

    it('maps top-right corner (49.9, 49.9) and clamped (50, 50) to cell (49, 49)', () => {
      const cell1 = worldToCell(49.9, 49.9);
      expect(cell1.ix).toBe(49);
      expect(cell1.iz).toBe(49);
      expect(cell1.index).toBe(2499);

      const cell2 = worldToCell(50, 50);
      expect(cell2.ix).toBe(49);
      expect(cell2.iz).toBe(49);
    });

    it('maps edges accurately', () => {
      // Left edge (-50, 0)
      const left = worldToCell(-50, 0);
      expect(left.ix).toBe(0);
      expect(left.iz).toBe(25);

      // Bottom edge (0, -50)
      const bottom = worldToCell(0, -50);
      expect(bottom.ix).toBe(25);
      expect(bottom.iz).toBe(0);

      // Right edge (49.9, 0)
      const right = worldToCell(49.9, 0);
      expect(right.ix).toBe(49);
      expect(right.iz).toBe(25);

      // Top edge (0, 49.9)
      const top = worldToCell(0, 49.9);
      expect(top.ix).toBe(25);
      expect(top.iz).toBe(49);
    });
  });

  describe('cellToWorld center coordinates', () => {
    it('calculates world center of cell (0, 0) as (-49, -49)', () => {
      const { x, z } = cellToWorld(0, 0);
      expect(x).toBeCloseTo(-49, 2);
      expect(z).toBeCloseTo(-49, 2);
    });

    it('calculates world center of cell (25, 25) as (1, 1)', () => {
      const { x, z } = cellToWorld(25, 25);
      expect(x).toBeCloseTo(1, 2);
      expect(z).toBeCloseTo(1, 2);
    });
  });

  describe('grid buffer and delta application', () => {
    it('initializes buffer with unexplored colors', () => {
      const buf = createInitialGridBuffer(10, 10);
      expect(buf.length).toBe(10 * 10 * 4);
      expect(buf[0]).toBe(COLOR_UNEXPLORED[0]);
      expect(buf[1]).toBe(COLOR_UNEXPLORED[1]);
      expect(buf[2]).toBe(COLOR_UNEXPLORED[2]);
      expect(buf[3]).toBe(COLOR_UNEXPLORED[3]);
    });

    it('applies grid deltas to newly explored cells', () => {
      const buf = createInitialGridBuffer(50, 50);
      applyGridDelta([100, 200], buf, 50, 50);

      // Cell 100 should now have explored color
      const offset100 = 100 * 4;
      expect(buf[offset100]).toBe(COLOR_EXPLORED[0]);
      expect(buf[offset100 + 1]).toBe(COLOR_EXPLORED[1]);

      // Cell 101 should still be unexplored
      const offset101 = 101 * 4;
      expect(buf[offset101]).toBe(COLOR_UNEXPLORED[0]);
    });

    it('decodes bitmask and applies grid snapshot', () => {
      // First byte has bit 7 set (cell index 0)
      // Base64 of single byte 0b10000000 (128) is 'gA=='
      const bitmask = 'gA==';
      const decoded = decodeBitmask(bitmask, 8);
      expect(decoded[0]).toBe(1);
      expect(decoded[1]).toBe(0);

      const buf = createInitialGridBuffer(2, 2);
      applyGridSnapshot(bitmask, buf, 2, 2);
      expect(buf[0]).toBe(COLOR_EXPLORED[0]);
      expect(buf[4]).toBe(COLOR_UNEXPLORED[0]);
    });
  });
});
