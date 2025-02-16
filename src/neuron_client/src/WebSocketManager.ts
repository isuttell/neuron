import { EventEmitter } from "events";
import { Action } from "redux";
import { getAccessToken } from "./actions/getToken";
import type { WebSocketEvent, WebSocketPayload } from "./types/websocket";

export default class WebSocketManager {
  private socket?: WebSocket;
  private events: EventEmitter;
  private url: string;
  public connected: boolean = false;

  constructor(url: string) {
    this.events = new EventEmitter();
    this.url = url;
    this.connected = false;
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
          this.events.emit("open");
        });
      }
    });

    this.socket.addEventListener("message", (event) => {
      try {
        const payload = JSON.parse(event.data) as WebSocketEvent;
        if (payload.type) {
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
      this.attemptReconnect();
    });

    this.socket.addEventListener("error", (error) => {
      console.error(error);
    });
    return true;
  }

  attemptReconnect() {
    delete this.socket;
    setTimeout(() => this.connect(), 1000);
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
    if (this.socket) {
      this.socket.close();
    }
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

export const socketManager = new WebSocketManager(
  window.location.protocol === "https:"
    ? `wss://${window.location.host}/ws`
    : `ws://${window.location.host}/ws`
);
