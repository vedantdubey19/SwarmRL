import { describe, it, expect, beforeEach } from 'vitest';
import { useSwarmStore, mutableSimState } from '../store/useSwarmStore';

describe('useSwarmStore throttling and ingestion', () => {
  beforeEach(() => {
    useSwarmStore.getState().resetStore();
  });

  it('throttles HUD metric state updates to 4 Hz (250ms)', () => {
    const store = useSwarmStore.getState();

    // Ingest frame at t = 0
    const frame1 = {
      step: 1,
      timestamp: 1000,
      drones: [{ id: 0, position: [0, 0, 0] }],
      metrics: {
        explored_fraction: 0.1,
        collision_totals: { drone: 0, obstacle: 0, boundary: 0, total: 0 },
        targets_found: 1,
      },
    };
    store.ingestFrame(frame1, 0);

    // Initial frame at t=0 triggers HUD update
    expect(useSwarmStore.getState().hudMetrics.step).toBe(1);
    expect(useSwarmStore.getState().hudMetrics.exploredFraction).toBe(0.1);

    // Ingest frame at t = 100ms (< 250ms interval)
    const frame2 = {
      step: 2,
      timestamp: 1033,
      drones: [{ id: 0, position: [1, 0, 1] }],
      metrics: {
        explored_fraction: 0.2,
        collision_totals: { drone: 1, obstacle: 0, boundary: 0, total: 1 },
        targets_found: 2,
      },
    };
    store.ingestFrame(frame2, 100);

    // FrameBuffer receives the frame, but HUD metrics are throttled and remain unchanged
    expect(mutableSimState.frameBuffer.currentFrame.step).toBe(2);
    expect(useSwarmStore.getState().hudMetrics.step).toBe(1); // Throttled!
    expect(useSwarmStore.getState().hudMetrics.exploredFraction).toBe(0.1); // Throttled!

    // Ingest frame at t = 260ms (> 250ms interval)
    const frame3 = {
      step: 3,
      timestamp: 1066,
      drones: [{ id: 0, position: [2, 0, 2] }],
      metrics: {
        explored_fraction: 0.35,
        collision_totals: { drone: 1, obstacle: 0, boundary: 0, total: 1 },
        targets_found: 2,
      },
    };
    store.ingestFrame(frame3, 260);

    // Now HUD metrics are updated!
    expect(useSwarmStore.getState().hudMetrics.step).toBe(3);
    expect(useSwarmStore.getState().hudMetrics.exploredFraction).toBe(0.35);
  });
});
