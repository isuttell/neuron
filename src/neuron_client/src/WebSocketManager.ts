import { EventEmitter } from "events";
import { getAccessToken } from "./actions/getToken";
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
      const payload = JSON.parse(event.data);
      if (payload.type) {
        this.events.emit(payload.type, payload);
      } else {
        console.error("Received payload without type:", payload);
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

  emit(payload: any) {
    if (!this.socket) {
      throw new Error("WebSocket connection not established");
    }
    this.socket.send(JSON.stringify({ type: event, payload }));
  }

  on(event: string, listener: (...args: any[]) => void) {
    this.events.on(event, listener);
    return {
      remove: () => this.events.off(event, listener),
    };
  }

  once(event: string, listener: (...args: any[]) => void) {
    this.events.on(event, (...args) => {
      listener(...args);
      this.events.off(event, listener);
    });
  }

  sendMessage(message: any) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
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
    return new Promise((resolve) => {
      this.once("open", resolve);
    });
  }
}

export const socketManager = new WebSocketManager(
  window.location.protocol === "https:"
    ? `wss://${window.location.host}/ws`
    : `ws://${window.location.host}/ws`
);
