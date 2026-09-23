import { create } from 'zustand';

function getWebSocketEndpoint() {
  if (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL;
  }
  if (typeof process !== 'undefined' && process.env && process.env.VITE_WS_URL) {
    return process.env.VITE_WS_URL;
  }
  if (typeof window !== 'undefined' && window.location) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.hostname}:8080`;
  }
  return 'ws://localhost:8080';
}

export const useSwarmStore = create((set, get) => ({
  drones: {},
  selectedDroneId: null,
  cameraMode: 'orbit',
  isConnected: false,
  metrics: null,
  _socket: null,

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

  connectWebSocket: (customUrl) => {
    const endpoint = customUrl || getWebSocketEndpoint();
    const currentSocket = get()._socket;
    if (currentSocket && (currentSocket.readyState === 0 || currentSocket.readyState === 1)) {
      return;
    }

    try {
      const ws = new WebSocket(endpoint);

      ws.onopen = () => {
        set({ isConnected: true, _socket: ws });
        ws.send(JSON.stringify({ type: 'register', role: 'subscriber' }));
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'frame' && Array.isArray(data.drones)) {
            const nextDrones = {};
            data.drones.forEach((drone) => {
              nextDrones[drone.id] = drone;
            });
            set({ drones: nextDrones, metrics: data.metrics || null });
          } else if (data.type === 'batch_update' && Array.isArray(data.agents)) {
            const nextDrones = {};
            data.agents.forEach((agent) => {
              nextDrones[agent.id] = agent;
            });
            set({ drones: nextDrones });
          }
        } catch (err) {
          console.error('Failed to parse telemetry message:', err);
        }
      };

      ws.onclose = () => {
        set({ isConnected: false, _socket: null });
      };

      ws.onerror = (err) => {
        console.error('WebSocket telemetry error:', err);
      };

      set({ _socket: ws });
    } catch (err) {
      console.error('Failed to initialize WebSocket client:', err);
    }
  },
}));