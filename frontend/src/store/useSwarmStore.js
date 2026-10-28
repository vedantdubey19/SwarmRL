import { create } from 'zustand';
import { FrameBuffer } from '../utils/frameBuffer';
import {
  createInitialGridBuffer,
  applyGridSnapshot,
  applyGridDelta,
} from '../utils/gridMapping';

// Mutable references outside React state to avoid 30 Hz re-rendering churn
export const mutableSimState = {
  frameBuffer: new FrameBuffer(),
  gridBuffer: createInitialGridBuffer(50, 50),
  gridNeedsUpdate: false,
  lastHudUpdate: -10000,
  lastLatencyMs: 0,
};

export const useSwarmStore = create((set) => ({
  // Connection state
  connectionStatus: 'disconnected', // 'disconnected' | 'connecting' | 'connected' | 'reconnecting'
  reconnectAttempt: 0,
  wsUrl: '',

  // World static data
  world: null,

  // Selected drone for UI focus/inspection
  selectedDroneId: null,

  // Throttled HUD metrics (updated at max 4 Hz)
  hudMetrics: {
    exploredFraction: 0,
    collisionTotals: {
      drone: 0,
      obstacle: 0,
      boundary: 0,
      total: 0,
    },
    targetsFound: 0,
    totalTargets: 0,
    activeAgents: 50,
    difficulty: 0,
    fps: 60,
    latencyMs: 0,
    step: 0,
  },

  // Rolling history for HUD graph (max 30 items)
  perfHistory: [],

  // Actions
  setConnectionStatus: (status, attempt = 0) =>
    set({ connectionStatus: status, reconnectAttempt: attempt }),

  setWsUrl: (url) => set({ wsUrl: url }),

  setWorld: (worldData) => set({ world: worldData }),

  setSelectedDroneId: (id) => set({ selectedDroneId: id }),

  // Ingest frame into mutable buffer, throttle HUD update to 4 Hz (250 ms)
  ingestFrame: (frame, now = performance.now()) => {
    const accepted = mutableSimState.frameBuffer.pushFrame(frame);
    if (!accepted) return false;

    // Calculate latency
    if (frame.timestamp) {
      mutableSimState.lastLatencyMs = Math.max(0, Date.now() - frame.timestamp);
    }

    // 4 Hz throttling for HUD React state
    if (now - mutableSimState.lastHudUpdate >= 250) {
      mutableSimState.lastHudUpdate = now;
      const metrics = frame.metrics || {};
      const col = metrics.collision_totals || {};

      set((state) => {
        const newPerfHistory = [
          ...state.perfHistory.slice(-29),
          {
            timestamp: now,
            latencyMs: mutableSimState.lastLatencyMs,
            step: frame.step ?? 0,
          },
        ];

        return {
          hudMetrics: {
            exploredFraction: metrics.explored_fraction ?? 0,
            collisionTotals: {
              drone: col.drone ?? 0,
              obstacle: col.obstacle ?? 0,
              boundary: col.boundary ?? 0,
              total: col.total ?? 0,
            },
            targetsFound: metrics.targets_found ?? 0,
            totalTargets: metrics.total_targets ?? (state.world?.targets?.length || 0),
            activeAgents: metrics.active_agents ?? frame.drones?.length ?? 50,
            difficulty: metrics.difficulty ?? 0,
            fps: state.hudMetrics.fps,
            latencyMs: mutableSimState.lastLatencyMs,
            step: frame.step ?? 0,
          },
          perfHistory: newPerfHistory,
        };
      });
    }

    return true;
  },

  setFps: (fps) =>
    set((state) => ({
      hudMetrics: { ...state.hudMetrics, fps },
    })),

  // Grid snapshot message handler
  handleGridSnapshot: (snapshot) => {
    if (!snapshot || !snapshot.bitmask) return;
    applyGridSnapshot(snapshot.bitmask, mutableSimState.gridBuffer, snapshot.width || 50, snapshot.height || 50);
    mutableSimState.gridNeedsUpdate = true;
  },

  // Grid delta message handler
  handleGridDelta: (delta) => {
    if (!delta || !delta.new_cells) return;
    applyGridDelta(delta.new_cells, mutableSimState.gridBuffer, 50, 50);
    mutableSimState.gridNeedsUpdate = true;
  },

  resetStore: () => {
    mutableSimState.frameBuffer = new FrameBuffer();
    mutableSimState.gridBuffer = createInitialGridBuffer(50, 50);
    mutableSimState.gridNeedsUpdate = true;
    mutableSimState.lastHudUpdate = -10000;
    set({
      world: null,
      selectedDroneId: null,
      connectionStatus: 'disconnected',
      reconnectAttempt: 0,
      hudMetrics: {
        exploredFraction: 0,
        collisionTotals: { drone: 0, obstacle: 0, boundary: 0, total: 0 },
        targetsFound: 0,
        totalTargets: 0,
        activeAgents: 50,
        difficulty: 0,
        fps: 60,
        latencyMs: 0,
        step: 0,
      },
      perfHistory: [],
    });
  },
}));
