import { EventEmitter } from "events";
import { Action } from "redux";
import { getAccessToken } from "./actions/getToken";
import type { WebSocketEvent, WebSocketPayload } from "./types/websocket";

export default class WebSocketManager {
  private static instance: WebSocketManager | null = null;
  private socket?: WebSocket;
  private events: EventEmitter;
  private url: string;
  public connected: boolean = false;
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 100;
  private baseReconnectDelay: number = 1000; // 1 second
  private maxReconnectDelay: number = 30000; // 30 seconds
  private reconnectTimer?: number;
  private pingTimeout?: number;

  private constructor(url: string) {
    this.events = new EventEmitter();
    this.url = url;
    this.connected = false;
  }

  public static getInstance(url?: string): WebSocketManager {
    if (!WebSocketManager.instance) {
      if (!url) {
        throw new Error("WebSocketManager URL required for first initialization");
      }
      WebSocketManager.instance = new WebSocketManager(url);
    }
    return WebSocketManager.instance;
  }

  public static resetInstance(): void {
    if (WebSocketManager.instance) {
      WebSocketManager.instance.close();
      WebSocketManager.instance = null;
    }
  }

  connect() {
    if (this.socket) {
      return false;
    }
    this.socket = new WebSocket(this.url);
    this.socket.addEventListener("open", () => {
      if (!this.connected) {
        getAccessToken().then((token) => {
          this.socket?.send(`access_token=${token}`);
          this.connected = true;
          this.reconnectAttempts = 0; // Reset reconnection attempts on successful connection
          this.events.emit("open");
        });
      }
    });

    this.socket.addEventListener("message", (event) => {
      try {
        const payload = JSON.parse(event.data) as WebSocketEvent;
        if (payload.type) {
          // Handle ping messages by responding with pong
          if (payload.type === "ping") {
            this.sendPong(payload.timestamp);
            return;
          }
          this.events.emit(payload.type, payload);
        } else {
          console.error("Received payload without type:", payload);
        }
      } catch (error) {
        console.error("Failed to parse WebSocket message:", error);
      }
    });

    this.socket.addEventListener("close", () => {
      if (this.connected) {
        this.connected = false;
        this.events.emit("close");
      }
      this.clearTimers();
      this.attemptReconnect();
    });

    this.socket.addEventListener("error", (error) => {
      console.error(error);
    });
    return true;
  }

  private clearTimers() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = undefined;
    }
    if (this.pingTimeout) {
      clearTimeout(this.pingTimeout);
      this.pingTimeout = undefined;
    }
  }

  private sendPong(timestamp: number) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      const pongMessage = JSON.stringify({
        type: "pong",
        timestamp: timestamp
      });
      this.socket.send(pongMessage);
    }
  }

  private calculateReconnectDelay(): number {
    // Exponential backoff: 1s, 2s, 4s, 8s, 16s, 30s (capped)
    const exponentialDelay = Math.min(
      this.baseReconnectDelay * Math.pow(2, this.reconnectAttempts),
      this.maxReconnectDelay
    );

    // Add jitter (±25%) to prevent thundering herd
    const jitter = exponentialDelay * 0.25 * (Math.random() * 2 - 1);
    return Math.max(exponentialDelay + jitter, 500); // Minimum 500ms
  }

  attemptReconnect() {
    // Check if we've exceeded max retry attempts
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error(`Max reconnection attempts (${this.maxReconnectAttempts}) reached. Giving up.`);
      this.events.emit("give_up");
      return;
    }

    this.reconnectAttempts++;
    const delay = this.calculateReconnectDelay();

    console.log(`Attempting reconnection ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${Math.round(delay)}ms`);

    delete this.socket;
    this.reconnectTimer = window.setTimeout(() => {
      this.connect();
    }, delay);
  }

  emit(payload: WebSocketPayload) {
    if (!this.socket) {
      throw new Error("WebSocket connection not established");
    }
    this.socket.send(JSON.stringify({ type: payload.type, payload }));
  }

  on<T extends WebSocketEvent>(
    event: T["type"],
    listener: (payload: T) => void
  ) {
    this.events.on(event, listener);
    return {
      remove: () => this.events.off(event, listener),
    };
  }

  once<T extends WebSocketEvent>(
    event: T["type"],
    listener: (payload: T) => void
  ) {
    const wrappedListener = (payload: T) => {
      listener(payload);
      this.events.off(event, wrappedListener);
    };
    this.events.on(event, wrappedListener);
  }

  // Handle internal events that are not WebSocket messages
  onInternal(event: string, listener: () => void) {
    this.events.on(event, listener);
    return {
      remove: () => this.events.off(event, listener),
    };
  }

  sendMessage(action: Action) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      const message = {
        ...action,
        type: action.type.replace("socket/", ""),
      } as WebSocketPayload;
      this.socket.send(JSON.stringify(message));
    } else {
      console.error(
        "WebSocket is not open. Ready state:",
        this.socket?.readyState
      );
    }
  }

  close() {
    this.clearTimers();
    if (this.socket) {
      this.socket.close();
    }
  }

  resetReconnectionAttempts() {
    this.reconnectAttempts = 0;
    this.clearTimers();
  }

  ready() {
    if (this.connected && this.socket) {
      return Promise.resolve();
    }
    return new Promise<void>((resolve) => {
      const openHandler = () => {
        resolve();
        this.events.off("open", openHandler);
      };
      this.events.on("open", openHandler);
    });
  }
}

export const socketManager = WebSocketManager.getInstance(
  window.location.protocol === "https:"
    ? `wss://${window.location.host}/ws`
    : `ws://${window.location.host}/ws`
);
