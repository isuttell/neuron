import { useEffect, useRef, useState, useCallback } from 'react';

interface WebSocketMessage {
  type: 'connected' | 'image_changed' | 'error' | 'pong' | string;
  etag?: string;
  current_etag?: string;
  timestamp?: string;
  message?: string;
  last_check?: string | null;
  js_hash?: string;
  hash_changed?: boolean;
}

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
    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
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
            // Store initial JS hash
            currentJsHashRef.current = message.js_hash || null;
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
        console.error('WebSocket error:', event);
        setError('WebSocket connection error');
      };

      ws.onclose = () => {
        setIsConnected(false);

        // Clear heartbeat
        if (heartbeatIntervalRef.current) {
          clearInterval(heartbeatIntervalRef.current);
          heartbeatIntervalRef.current = null;
        }

        // Schedule reconnect
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, reconnectInterval);
      };

      wsRef.current = ws;
    } catch (err) {
      console.error('Failed to create WebSocket:', err);
      setError('Failed to connect');

      // Schedule reconnect
      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, reconnectInterval);
    }
  }, [url, reconnectInterval, heartbeatInterval]);

  useEffect(() => {
    connect();

    return () => {
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
