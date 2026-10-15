import { useEffect, useRef, useState } from 'react';
import { useSwarmStore } from '../store/useSwarmStore';

export function useSwarmWebSocket(url = 'ws://localhost:8765') {
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef(null);
  const ingestRawBatch = useSwarmStore((state) => state.ingestRawBatch);

  useEffect(() => {
    let reconnectTimeout = null;

    function connect() {
      const ws = new WebSocket(url);
      socketRef.current = ws;

      ws.onopen = () => {
        console.log('[SwarmRL Bridge] Connected to telemetry socket:', url);
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          ingestRawBatch(payload);
        } catch (err) {
          console.error('[SwarmRL Bridge] Frame parse error:', err);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        reconnectTimeout = setTimeout(connect, 1500);
      };

      ws.onerror = (err) => {
        console.error('[SwarmRL Bridge] Socket error:', err);
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
  }, [url, ingestRawBatch]);

  return { isConnected };
}