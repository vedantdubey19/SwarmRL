import { useEffect, useRef, useState, useCallback } from 'react';
import { useSwarmStore } from '../store/useSwarmStore';

export function useSwarmWebSocket(url = 'ws://localhost:8765') {
  const [isConnected, setIsConnected] = useState(false);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  const socketRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const ingestRawBatch = useSwarmStore((state) => state.ingestRawBatch);

  const connect = useCallback(() => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      const ws = new WebSocket(url);
      socketRef.current = ws;

      ws.onopen = () => {
        console.log('[SwarmRL Live Stream] Connected to real telemetry feed:', url);
        setIsConnected(true);
        setReconnectAttempts(0);
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          ingestRawBatch(payload);
        } catch (err) {
          console.error('[SwarmRL Live Stream] Deserialization error:', err);
        }
      };

      ws.onclose = (event) => {
        setIsConnected(false);
        // Exponential backoff with a 5-second cap
        const timeout = Math.min(1000 * Math.pow(1.5, reconnectAttempts), 5000);
        console.warn(`[SwarmRL Live Stream] Disconnected (Code: ${event.code}). Retrying in ${Math.round(timeout)}ms...`);
        reconnectTimeoutRef.current = setTimeout(() => {
          setReconnectAttempts((prev) => prev + 1);
          connect();
        }, timeout);
      };

      ws.onerror = (err) => {
        console.error('[SwarmRL Live Stream] WebSocket error:', err);
        ws.close();
      };
    } catch (e) {
      console.error('[SwarmRL Live Stream] Connection initialization error:', e);
    }
  }, [url, ingestRawBatch, reconnectAttempts]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        socketRef.current.close();
      }
    };
  }, [connect]);

  return { isConnected, reconnectAttempts };
}