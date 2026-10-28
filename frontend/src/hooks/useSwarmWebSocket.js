import { useEffect, useRef } from 'react';
import { useSwarmStore } from '../store/useSwarmStore';
import { deriveWsUrl } from '../utils/url';

export function useSwarmWebSocket(overrideUrl = null) {
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const attemptRef = useRef(0);
  const isDestroyedRef = useRef(false);

  const setConnectionStatus = useSwarmStore((s) => s.setConnectionStatus);
  const setWsUrl = useSwarmStore((s) => s.setWsUrl);
  const setWorld = useSwarmStore((s) => s.setWorld);
  const ingestFrame = useSwarmStore((s) => s.ingestFrame);
  const handleGridSnapshot = useSwarmStore((s) => s.handleGridSnapshot);
  const handleGridDelta = useSwarmStore((s) => s.handleGridDelta);

  useEffect(() => {
    isDestroyedRef.current = false;
    const resolvedUrl = overrideUrl || deriveWsUrl(import.meta.env?.VITE_WS_URL);
    setWsUrl(resolvedUrl);

    function connect() {
      if (isDestroyedRef.current) return;

      const attempt = attemptRef.current;
      setConnectionStatus(attempt === 0 ? 'connecting' : 'reconnecting', attempt);

      try {
        const ws = new WebSocket(resolvedUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          if (isDestroyedRef.current) {
            ws.close();
            return;
          }
          attemptRef.current = 0;
          setConnectionStatus('connected', 0);

          // Register as subscriber
          ws.send(JSON.stringify({ type: 'register', role: 'subscriber' }));
        };

        ws.onmessage = (event) => {
          if (isDestroyedRef.current) return;
          try {
            const data = JSON.parse(event.data);
            const msgType = data.type;

            if (msgType === 'world') {
              setWorld(data);
            } else if (msgType === 'frame') {
              ingestFrame(data);
            } else if (msgType === 'grid_snapshot') {
              handleGridSnapshot(data);
            } else if (msgType === 'grid_delta') {
              handleGridDelta(data);
            }
          } catch {
            // Ignore malformed message
          }
        };

        ws.onclose = () => {
          wsRef.current = null;
          if (isDestroyedRef.current) return;

          attemptRef.current += 1;
          const delay = Math.min(5000, 500 * Math.pow(1.5, attemptRef.current - 1));
          setConnectionStatus('reconnecting', attemptRef.current);
          reconnectTimeoutRef.current = setTimeout(connect, delay);
        };

        ws.onerror = () => {
          // Trigger onclose
          ws.close();
        };
      } catch {
        attemptRef.current += 1;
        const delay = Math.min(5000, 500 * Math.pow(1.5, attemptRef.current - 1));
        setConnectionStatus('reconnecting', attemptRef.current);
        reconnectTimeoutRef.current = setTimeout(connect, delay);
      }
    }

    connect();

    return () => {
      isDestroyedRef.current = true;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      setConnectionStatus('disconnected', 0);
    };
  }, [overrideUrl, setConnectionStatus, setWsUrl, setWorld, ingestFrame, handleGridSnapshot, handleGridDelta]);
}
