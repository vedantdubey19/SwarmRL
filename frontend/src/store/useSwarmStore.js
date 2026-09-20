import { create } from 'zustand';

export const useSwarmStore = create((set) => ({
  // Telemetry payload schema: { [id]: { id, x, y, z, timestamp } }
  drones: {},
  selectedDroneId: null,
  cameraMode: 'orbit', // 'orbit' | 'follow'

  // Update telemetry batch from WebSocket stream
  updateDroneBatch: (batch) =>
    set((state) => {
      const updated = { ...state.drones };
      batch.forEach((drone) => {
        updated[drone.id] = { ...drone };
      });
      return { drones: updated };
    }),

  setSelectedDroneId: (id) => set({ selectedDroneId: id }),
  setCameraMode: (mode) => set({ cameraMode: mode }),
}));