import { useEffect, useRef, useState, useCallback } from 'react';
import type { WebSocketMessage } from '@/types/dashboard';
import { useAppDispatch } from '@/store/hooks';
import { setConnected, setDisconnected, updateEtag } from '@/store/connectionSlice';
import { setSensors, updateSensors } from '@/store/sensorSlice';

interface UseWebSocketOptions {
  onMessage?: (message: WebSocketMessage) => void;
  reconnectInterval?: number;
  heartbeatInterval?: number;
}

export function useWebSocket(
  url: string,
  options: UseWebSocketOptions = {}
) {
  const {
    onMessage,
    reconnectInterval = 5000,
    heartbeatInterval = 10000  // Reduced to 10 seconds for hash checking
  } = options;

  const dispatch = useAppDispatch();
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const onMessageRef = useRef(onMessage);
  const currentJsHashRef = useRef<string | null>(null);

  // Update onMessage ref when it changes
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  const connect = useCallback(() => {
    console.log(`[WebSocket] Attempting to connect to: ${url}`);
    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        console.log('[WebSocket] Connected successfully');
        setIsConnected(true);
        setError(null);

        // Start heartbeat after a short delay to ensure connection is stable
        setTimeout(() => {
          heartbeatIntervalRef.current = setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
              try {
                ws.send('ping');
              } catch (e) {
                console.error('Failed to send ping:', e);
              }
            }
          }, heartbeatInterval);
        }, 1000); // Wait 1 second before starting heartbeat
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as WebSocketMessage;

          // Handle different message types
          if (message.type === 'connected') {
            // Store initial JS hash and dispatch connection info
            currentJsHashRef.current = message.js_hash || null;
            dispatch(setConnected({
              currentEtag: message.current_etag || null,
              lastCheck: message.last_check || null,
              jsHash: message.js_hash || null
            }));
          } else if (message.type === 'sensors_state') {
            // Initial sensor state
            dispatch(setSensors({
              sensors: message.sensors || [],
              timestamp: message.timestamp || new Date().toISOString()
            }));
          } else if (message.type === 'sensors_update') {
            // Sensor updates
            dispatch(updateSensors({
              sensors: message.sensors || [],
              timestamp: message.timestamp || new Date().toISOString()
            }));
          } else if (message.type === 'image_changed') {
            // Update ETag when image changes
            if (message.etag) {
              dispatch(updateEtag(message.etag));
            }
          } else if (message.type === 'pong') {
            // Check for hash changes in pong response
            if (message.hash_changed) {
              window.location.reload();
              return; // Don't process further since we're reloading
            }
            // Update current hash
            currentJsHashRef.current = message.js_hash || null;
            return; // Don't pass pong messages to onMessage callback
          }

          setLastMessage(message);
          onMessageRef.current?.(message);
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      ws.onerror = (event) => {
        console.error('[WebSocket] Connection error:', event);
        setError('WebSocket connection error');
      };

      ws.onclose = (event) => {
        console.log(`[WebSocket] Connection closed. Code: ${event.code}, Reason: ${event.reason}`);
        setIsConnected(false);
        dispatch(setDisconnected());

        // Clear heartbeat
        if (heartbeatIntervalRef.current) {
          clearInterval(heartbeatIntervalRef.current);
          heartbeatIntervalRef.current = null;
        }

        // Schedule reconnect
        console.log(`[WebSocket] Scheduling reconnect in ${reconnectInterval}ms`);
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, reconnectInterval);
      };

      wsRef.current = ws;
    } catch (err) {
      console.error('[WebSocket] Failed to create WebSocket:', err);
      setError('Failed to connect');

      // Schedule reconnect
      console.log(`[WebSocket] Scheduling reconnect in ${reconnectInterval}ms after error`);
      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, reconnectInterval);
    }
  }, [url, reconnectInterval, heartbeatInterval, dispatch]);

  useEffect(() => {
    console.log('[WebSocket] Hook mounted, initiating connection');
    connect();

    return () => {
      console.log('[WebSocket] Hook unmounting, cleaning up');
      // Cleanup
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (heartbeatIntervalRef.current) {
        clearInterval(heartbeatIntervalRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  return {
    isConnected,
    lastMessage,
    error
  };
}
