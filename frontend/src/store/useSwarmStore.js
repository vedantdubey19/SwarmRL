import { create } from 'zustand';
import * as THREE from 'three';

function getWebSocketEndpoint() {
  if (typeof import.meta !== 'undefined' && import.meta.env) {
    if (import.meta.env.VITE_WS_URL) return import.meta.env.VITE_WS_URL;
    if (import.meta.env.WS_URL) return import.meta.env.WS_URL;
  }
  if (typeof process !== 'undefined' && process.env) {
    if (process.env.VITE_WS_URL) return process.env.VITE_WS_URL;
    if (process.env.WS_URL) return process.env.WS_URL;
  }

  const defaultPort =
    (typeof import.meta !== 'undefined' && import.meta.env && (import.meta.env.VITE_WS_PORT || import.meta.env.WS_PORT)) ||
    (typeof process !== 'undefined' && process.env && (process.env.VITE_WS_PORT || process.env.WS_PORT)) ||
    8080;

  if (typeof window !== 'undefined' && window.location) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const isDev = Boolean(
      (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.DEV) ||
      window.location.hostname === 'localhost' ||
      window.location.hostname === '127.0.0.1'
    );

    if (isDev && window.location.port !== String(defaultPort)) {
      const devHost = window.location.hostname || 'localhost';
      return `${protocol}//${devHost}:${defaultPort}`;
    }

    if (window.location.host) {
      return `${protocol}//${window.location.host}`;
    }
  }

  return `ws://localhost:${defaultPort}`;
}

const telemetryMap = new Map();
const tempEuler = new THREE.Euler(0, 0, 0, 'YXZ');

export const useSwarmStore = create((set, get) => ({
  droneIds: [],
  selectedDroneId: null,
  cameraMode: 'orbit',
  isConnected: false,
  metrics: null,
  lastStep: -1,
  lastTimestamp: 0,
  lastLatencyMs: null,
  _socket: null,

  setSelectedDroneId: (id) => set({ selectedDroneId: id }),
  setCameraMode: (mode) => set({ cameraMode: mode }),

  getDroneTelemetry: (id) => telemetryMap.get(id),

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
            const { lastStep, lastTimestamp } = get();
            if (typeof data.step === 'number' && data.step < lastStep) {
              return;
            }
            if (typeof data.timestamp === 'number' && data.timestamp < lastTimestamp) {
              return;
            }

            const currentIds = get().droneIds;
            const incomingIds = [];

            for (let i = 0; i < data.drones.length; i++) {
              const drone = data.drones[i];
              const droneId = String(drone.id ?? drone.agent_id ?? i);
              incomingIds.push(droneId);

              const rawPos = Array.isArray(drone.pos)
                ? drone.pos
                : [drone.x || 0, drone.y || 0, drone.z || 0];
              const heading = typeof drone.heading === 'number' ? drone.heading : 0;

              tempEuler.set(0, -heading + Math.PI / 2, 0);

              let entry = telemetryMap.get(droneId);
              if (!entry) {
                entry = {
                  id: droneId,
                  currentPos: new THREE.Vector3(rawPos[0], rawPos[1], rawPos[2]),
                  targetPos: new THREE.Vector3(rawPos[0], rawPos[1], rawPos[2]),
                  currentRot: new THREE.Quaternion().setFromEuler(tempEuler),
                  targetRot: new THREE.Quaternion().setFromEuler(tempEuler),
                  heading,
                  status: drone.status || 'active',
                  detections: drone.detections || [],
                };
                telemetryMap.set(droneId, entry);
              } else {
                entry.targetPos.set(rawPos[0], rawPos[1], rawPos[2]);
                entry.targetRot.setFromEuler(tempEuler);
                entry.heading = heading;
                entry.status = drone.status || 'active';
                entry.detections = drone.detections || [];
              }
            }

            const idsChanged = incomingIds.length !== currentIds.length ||
              incomingIds.some((id, idx) => id !== currentIds[idx]);

            set({
              lastStep: typeof data.step === 'number' ? data.step : lastStep,
              lastTimestamp: typeof data.timestamp === 'number' ? data.timestamp : lastTimestamp,
              lastLatencyMs: typeof data.timestamp === 'number' ? Math.max(0, Date.now() - data.timestamp) : null,
              metrics: data.metrics || null,
              ...(idsChanged ? { droneIds: incomingIds } : {}),
            });
          } else if (data.type === 'batch_update' && Array.isArray(data.agents)) {
            const currentIds = get().droneIds;
            const incomingIds = [];

            for (let i = 0; i < data.agents.length; i++) {
              const agent = data.agents[i];
              const agentId = String(agent.id || i);
              incomingIds.push(agentId);

              const rawPos = [agent.x || 0, agent.y || 0, agent.z || 0];
              const heading = typeof agent.heading === 'number' ? agent.heading : 0;
              tempEuler.set(0, -heading + Math.PI / 2, 0);

              let entry = telemetryMap.get(agentId);
              if (!entry) {
                entry = {
                  id: agentId,
                  currentPos: new THREE.Vector3(rawPos[0], rawPos[1], rawPos[2]),
                  targetPos: new THREE.Vector3(rawPos[0], rawPos[1], rawPos[2]),
                  currentRot: new THREE.Quaternion().setFromEuler(tempEuler),
                  targetRot: new THREE.Quaternion().setFromEuler(tempEuler),
                  heading,
                  status: 'active',
                  detections: [],
                };
                telemetryMap.set(agentId, entry);
              } else {
                entry.targetPos.set(rawPos[0], rawPos[1], rawPos[2]);
                entry.targetRot.setFromEuler(tempEuler);
                entry.heading = heading;
              }
            }

            const idsChanged = incomingIds.length !== currentIds.length ||
              incomingIds.some((id, idx) => id !== currentIds[idx]);

            set({
              ...(idsChanged ? { droneIds: incomingIds } : {}),
            });
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