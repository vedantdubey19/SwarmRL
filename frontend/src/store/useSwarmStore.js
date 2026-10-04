import { create } from 'zustand';

// Elevation equation matching Terrain.jsx
const getElevation = (x, z) => {
  return (
    Math.sin(x * 0.08) * Math.cos(z * 0.08) * 3.5 +
    Math.sin(x * 0.03 + 1.2) * Math.cos(z * 0.03 + 0.8) * 4.0
  );
};

export const useSwarmStore = create((set) => ({
  drones: {},
  selectedDroneId: null,
  cameraMode: 'orbit', // 'orbit' | 'follow'
  showCollisionDebug: true,
  totalCollisions: 0,

  updateDroneBatch: (batch) =>
    set((state) => {
      const updated = { ...state.drones };
      let stepCollisions = 0;

      batch.forEach((drone) => {
        updated[drone.id] = { ...drone };
        if (drone.collision) stepCollisions++;
      });

      return {
        drones: updated,
        totalCollisions: state.totalCollisions + Math.floor(stepCollisions / 2),
      };
    }),

  // Day 09: Stress-test action generating 50 randomized drone coordinates
  randomizeSwarmPositions: (count = 50) =>
    set((state) => {
      const updated = {};
      const agents = [];

      for (let i = 0; i < count; i++) {
        const id = `agent-${String(i + 1).padStart(2, '0')}`;
        const x = Number(((Math.random() - 0.5) * 80).toFixed(2));
        const z = Number(((Math.random() - 0.5) * 80).toFixed(2));
        const terrainY = getElevation(x, z);
        const y = Number((terrainY + 3.5 + Math.random() * 5.0).toFixed(2));
        const yaw = Number((Math.random() * Math.PI * 2).toFixed(2));

        agents.push({ id, x, y, z, yaw, collision: false, timestamp: Date.now() });
      }

      // Check proximity collisions among randomized positions
      let collisionCount = 0;
      for (let i = 0; i < agents.length; i++) {
        for (let j = i + 1; j < agents.length; j++) {
          const dx = agents[i].x - agents[j].x;
          const dz = agents[i].z - agents[j].z;
          if (Math.sqrt(dx * dx + dz * dz) < 2.5) {
            agents[i].collision = true;
            agents[j].collision = true;
            collisionCount++;
          }
        }
        updated[agents[i].id] = agents[i];
      }

      return {
        drones: updated,
        totalCollisions: state.totalCollisions + collisionCount,
      };
    }),

  setSelectedDroneId: (id) => set({ selectedDroneId: id }),
  setCameraMode: (mode) => set({ cameraMode: mode }),
  toggleCollisionDebug: () => set((state) => ({ showCollisionDebug: !state.showCollisionDebug })),
}));