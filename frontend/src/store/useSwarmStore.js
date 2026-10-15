import { create } from 'zustand';
import * as THREE from 'three';
import { globalTelemetryBridge } from '../utils/telemetryBridge';

export const useSwarmStore = create((set) => ({
  drones: {},
  selectedDroneId: null,
  cameraMode: 'orbit', // 'orbit' | 'follow'
  showCollisionDebug: true,
  totalCollisions: 0,
  packetCount: 0,
  avgLatencyMs: 0,
  networkJitterMs: 0,

  // Day 11 Real-Data Ingestion Pipeline Hook
  ingestRawBatch: (rawBatch) =>
    set((state) => {
      const { validNodes, avgJitter } = globalTelemetryBridge.processBatch(rawBatch);
      if (validNodes.length === 0) return {};

      const updated = { ...state.drones };
      let stepCollisions = 0;
      let latencySum = 0;
      const now = Date.now();

      validNodes.forEach((agent) => {
        updated[agent.id] = agent;
        if (agent.collision) stepCollisions++;
        if (agent.timestamp) latencySum += Math.max(0, now - agent.timestamp);
      });

      const avgLat = Math.round(latencySum / validNodes.length);

      return {
        drones: updated,
        totalCollisions: state.totalCollisions + Math.floor(stepCollisions / 2),
        packetCount: state.packetCount + 1,
        avgLatencyMs: avgLat,
        networkJitterMs: avgJitter,
      };
    }),

  setSelectedDroneId: (id) => set({ selectedDroneId: id }),
  setCameraMode: (mode) => set({ cameraMode: mode }),
  toggleCollisionDebug: () =>
    set((state) => ({ showCollisionDebug: !state.showCollisionDebug })),
}));