import { create } from 'zustand';
import { globalTelemetryBridge } from '../utils/telemetryBridge';
import { globalSyncBuffer } from '../utils/syncBuffer';

const GRID_SIZE = 60; // 60x60 grid resolution over 120m world bounds (2m cells)
const CELL_WORLD_SIZE = 2.0;
const HALF_BOUNDS = 60;

export const useSwarmStore = create((set, get) => ({
  drones: {},
  selectedDroneId: null,
  cameraMode: 'orbit',
  showCollisionDebug: true,
  showSensorCones: true,
  showGroundPainting: true, // Day 18 toggle
  totalCollisions: 0,
  packetCount: 0,
  avgLatencyMs: 0,
  networkJitterMs: 0,
  swarmDispersionRadius: 0,
  renderFps: 60,

  // Set of explored cell indices ("x_z")
  exploredCells: new Set(),
  coveragePercentage: 0,

  ingestRawBatch: (rawBatch) =>
    set((state) => {
      const { validNodes, avgJitter } = globalTelemetryBridge.processBatch(rawBatch);
      if (validNodes.length === 0) return {};

      globalSyncBuffer.pushBatch(validNodes);

      const updated = { ...state.drones };
      let stepCollisions = 0;
      let latencySum = 0;
      let sumX = 0;
      let sumZ = 0;
      const now = Date.now();

      // Paint ground beneath active drones
      const newExplored = new Set(state.exploredCells);
      const sensorRadiusCells = 2; // ~4m ground footprint

      validNodes.forEach((agent) => {
        updated[agent.id] = agent;
        if (agent.collision) stepCollisions++;
        if (agent.timestamp) latencySum += Math.max(0, now - agent.timestamp);
        sumX += agent.x;
        sumZ += agent.z;

        // Discretize agent world coordinates into grid indices
        const gridX = Math.floor((agent.x + HALF_BOUNDS) / CELL_WORLD_SIZE);
        const gridZ = Math.floor((agent.z + HALF_BOUNDS) / CELL_WORLD_SIZE);

        for (let dx = -sensorRadiusCells; dx <= sensorRadiusCells; dx++) {
          for (let dz = -sensorRadiusCells; dz <= sensorRadiusCells; dz++) {
            if (dx * dx + dz * dz <= sensorRadiusCells * sensorRadiusCells) {
              const cx = gridX + dx;
              const cz = gridZ + dz;
              if (cx >= 0 && cx < GRID_SIZE && cz >= 0 && cz < GRID_SIZE) {
                newExplored.add(`${cx}_${cz}`);
              }
            }
          }
        }
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

      const totalGridCells = GRID_SIZE * GRID_SIZE;
      const coverage = Math.min(100, Number(((newExplored.size / totalGridCells) * 100).toFixed(1)));

      return {
        drones: updated,
        exploredCells: newExplored,
        coveragePercentage: coverage,
        totalCollisions: state.totalCollisions + Math.floor(stepCollisions / 2),
        packetCount: state.packetCount + 1,
        avgLatencyMs: Math.round(latencySum / count),
        networkJitterMs: avgJitter,
        swarmDispersionRadius: Math.round(Math.sqrt(maxDistSq)),
      };
    }),

  setRenderFps: (fps) => set({ renderFps: fps }),
  setSelectedDroneId: (id) => set({ selectedDroneId: id }),
  setCameraMode: (mode) => set({ cameraMode: mode }),
  toggleCollisionDebug: () => set((state) => ({ showCollisionDebug: !state.showCollisionDebug })),
  toggleSensorCones: () => set((state) => ({ showSensorCones: !state.showSensorCones })),
  toggleGroundPainting: () => set((state) => ({ showGroundPainting: !state.showGroundPainting })),
}));