import { create } from 'zustand';

export const useSwarmStore = create((set, get) => ({
  // Telemetry target buffer: { [id]: { id, x, y, z, yaw, collision, timestamp } }
  drones: {},
  selectedDroneId: null,
  cameraMode: 'orbit', // 'orbit' | 'follow'
  showCollisionDebug: true,
  totalCollisions: 0,
  packetCount: 0,
  avgLatencyMs: 0,

  // High-performance batch ingestion
  updateDroneBatch: (batch) =>
    set((state) => {
      const updated = { ...state.drones };
      let stepCollisions = 0;
      let latencySum = 0;

      const now = Date.now();
      batch.forEach((agent) => {
        updated[agent.id] = {
          ...agent,
          targetPos: [agent.x, agent.y, agent.z],
          targetYaw: agent.yaw || 0,
        };
        if (agent.collision) stepCollisions++;
        if (agent.timestamp) latencySum += Math.max(0, now - agent.timestamp);
      });

      const avgLat = batch.length > 0 ? Math.round(latencySum / batch.length) : state.avgLatencyMs;

      return {
        drones: updated,
        totalCollisions: state.totalCollisions + Math.floor(stepCollisions / 2),
        packetCount: state.packetCount + 1,
        avgLatencyMs: avgLat,
      };
    }),

  setSelectedDroneId: (id) => set({ selectedDroneId: id }),
  setCameraMode: (mode) => set({ cameraMode: mode }),
  toggleCollisionDebug: () => set((state) => ({ showCollisionDebug: !state.showCollisionDebug })),
}));