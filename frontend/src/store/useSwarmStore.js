import { create } from 'zustand';
import { globalTelemetryBridge } from '../utils/telemetryBridge';
import { globalSyncBuffer } from '../utils/syncBuffer';

export const useSwarmStore = create((set) => ({
  drones: {},
  selectedDroneId: null,
  cameraMode: 'orbit', // 'orbit' | 'follow'
  showCollisionDebug: true,
  totalCollisions: 0,
  packetCount: 0,
  avgLatencyMs: 0,
  networkJitterMs: 0,
  swarmDispersionRadius: 0,
  renderFps: 60,

  ingestRawBatch: (rawBatch) =>
    set((state) => {
      const { validNodes, avgJitter } = globalTelemetryBridge.processBatch(rawBatch);
      if (validNodes.length === 0) return {};

      // Push coordinates to the spatial interpolation buffer
      globalSyncBuffer.pushBatch(validNodes);

      const updated = { ...state.drones };
      let stepCollisions = 0;
      let latencySum = 0;
      let sumX = 0;
      let sumZ = 0;
      const now = Date.now();

      validNodes.forEach((agent) => {
        updated[agent.id] = agent;
        if (agent.collision) stepCollisions++;
        if (agent.timestamp) latencySum += Math.max(0, now - agent.timestamp);
        sumX += agent.x;
        sumZ += agent.z;
      });

      const count = validNodes.length;
      const centroidX = sumX / count;
      const centroidZ = sumZ / count;

      let maxDistSq = 0;
      validNodes.forEach((agent) => {
        const dx = agent.x - centroidX;
        const dz = agent.z - centroidZ;
        const distSq = dx * dx + dz * dz;
        if (distSq > maxDistSq) maxDistSq = distSq;
      });

      const dispersionRadius = Math.round(Math.sqrt(maxDistSq));
      const avgLat = Math.round(latencySum / count);

      return {
        drones: updated,
        totalCollisions: state.totalCollisions + Math.floor(stepCollisions / 2),
        packetCount: state.packetCount + 1,
        avgLatencyMs: avgLat,
        networkJitterMs: avgJitter,
        swarmDispersionRadius: dispersionRadius,
      };
    }),

  setRenderFps: (fps) => set({ renderFps: fps }),
  setSelectedDroneId: (id) => set({ selectedDroneId: id }),
  setCameraMode: (mode) => set({ cameraMode: mode }),
  toggleCollisionDebug: () =>
    set((state) => ({ showCollisionDebug: !state.showCollisionDebug })),
}));