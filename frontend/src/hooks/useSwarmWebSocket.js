import { useEffect, useRef, useState } from 'react';
import { useSwarmStore } from '../store/useSwarmStore';

export function useSwarmWebSocket(url = 'ws://localhost:8765') {
  const [isConnected, setIsConnected] = useState(false);
  const [lastLatencyMs, setLastLatencyMs] = useState(0);
  const socketRef = useRef(null);
  const updateDroneBatch = useSwarmStore((state) => state.updateDroneBatch);

  useEffect(() => {
    let reconnectTimeout = null;

    function connect() {
      const ws = new WebSocket(url);
      socketRef.current = ws;

      ws.onopen = () => {
        console.log('[SwarmRL] Telemetry Stream CONNECTED:', url);
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const batch = JSON.parse(event.data);
          if (Array.isArray(batch)) {
            // Measure transmission latency against local client clock
            if (batch.length > 0 && batch[0].timestamp) {
              const latency = Math.max(0, Date.now() - batch[0].timestamp);
              setLastLatencyMs(latency);
            }
            // Update Zustand swarm state
            updateDroneBatch(batch);
          }
        } catch (err) {
          console.error('[SwarmRL] Telemetry deserialization error:', err);
        }
      };

      ws.onclose = () => {
        console.warn('[SwarmRL] Telemetry Stream DISCONNECTED. Retrying in 2s...');
        setIsConnected(false);
        reconnectTimeout = setTimeout(connect, 2000);
      };

      ws.onerror = (err) => {
        console.error('[SwarmRL] Telemetry Socket Error:', err);
        ws.close();
      };
    }

    connect();

    return () => {
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        socketRef.current.close();
      }
    };
  }, [url, updateDroneBatch]);

  return { isConnected, lastLatencyMs };
}