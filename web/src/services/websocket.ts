/**
 * websocket.ts — Real-time bidirectional WebSocket synchronization client.
 * Connects to DeepGuard backend, manages session reconnection, and dispatches real-time events.
 */

export interface SyncMessage {
  event: string;
  user_id: number;
  timestamp: string;
  version?: number;
  entity_id?: string | null;
  data: any;
}

type EventCallback = (data: any, raw: SyncMessage) => void;

class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string = "";
  private reconnectAttempts = 0;
  private reconnectTimer: any = null;
  private pingInterval: any = null;
  private isExplicitlyClosed = false;
  private listeners: Map<string, Set<EventCallback>> = new Map();
  private reconnectListeners: Set<() => void> = new Set();
  private statusListeners: Set<(connected: boolean) => void> = new Set();

  constructor() {
    // Automatically start connection if token exists
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("access_token");
      if (token) {
        this.connect();
      }
    }
  }

  private getWebSocketUrl(): string {
    const apiBase = import.meta.env.VITE_API_URL || "http://localhost:8000";
    let wsBase = apiBase.replace(/^http/, "ws");
    if (!wsBase.endsWith("/")) {
      wsBase += "/";
    }
    const token = localStorage.getItem("access_token") || "";
    return `${wsBase}api/ws?token=${encodeURIComponent(token)}`;
  }

  public connect() {
    const token = localStorage.getItem("access_token");
    if (!token) {
      this.disconnect();
      return;
    }

    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.isExplicitlyClosed = false;
    this.url = this.getWebSocketUrl();

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log("[SyncWS] Connected to DeepGuard real-time synchronization backend.");
        this.reconnectAttempts = 0;
        this.notifyStatus(true);
        this.startHeartbeat();

        // Notify reconnect listeners so components can reconcile missed state
        this.reconnectListeners.forEach((cb) => {
          try {
            cb();
          } catch (e) {
            console.error("[SyncWS] Error in reconnect callback:", e);
          }
        });
      };

      this.ws.onmessage = (event: MessageEvent) => {
        try {
          const parsed: SyncMessage = JSON.parse(event.data);
          if (parsed && parsed.event) {
            this.dispatchEvent(parsed.event, parsed.data, parsed);
          }
        } catch (err) {
          // Could be raw ping/pong or plain text
        }
      };

      this.ws.onclose = (event: CloseEvent) => {
        this.notifyStatus(false);
        this.stopHeartbeat();
        this.ws = null;

        if (!this.isExplicitlyClosed && localStorage.getItem("access_token")) {
          const delay = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts), 15000);
          this.reconnectAttempts++;
          console.warn(`[SyncWS] Disconnected (code: ${event.code}). Retrying in ${Math.round(delay)}ms...`);
          clearTimeout(this.reconnectTimer);
          this.reconnectTimer = setTimeout(() => {
            this.connect();
          }, delay);
        }
      };

      this.ws.onerror = (err) => {
        console.warn("[SyncWS] Connection warning or error:", err);
      };
    } catch (err) {
      console.error("[SyncWS] Exception creating WebSocket:", err);
    }
  }

  public disconnect() {
    this.isExplicitlyClosed = true;
    clearTimeout(this.reconnectTimer);
    this.stopHeartbeat();
    if (this.ws) {
      try {
        this.ws.close();
      } catch {}
      this.ws = null;
    }
    this.notifyStatus(false);
  }

  private startHeartbeat() {
    this.stopHeartbeat();
    this.pingInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        try {
          this.ws.send(JSON.stringify({ type: "ping" }));
        } catch {}
      }
    }, 25000);
  }

  private stopHeartbeat() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  public subscribe(event: string, callback: EventCallback): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(callback);

    // Ensure connection is active
    if (!this.ws || this.ws.readyState === WebSocket.CLOSED) {
      this.connect();
    }

    return () => {
      const set = this.listeners.get(event);
      if (set) {
        set.delete(callback);
        if (set.size === 0) {
          this.listeners.delete(event);
        }
      }
    };
  }

  public onReconnect(callback: () => void): () => void {
    this.reconnectListeners.add(callback);
    return () => {
      this.reconnectListeners.delete(callback);
    };
  }

  public onStatusChange(callback: (connected: boolean) => void): () => void {
    this.statusListeners.add(callback);
    callback(this.isConnected());
    return () => {
      this.statusListeners.delete(callback);
    };
  }

  public isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  private notifyStatus(connected: boolean) {
    this.statusListeners.forEach((cb) => {
      try {
        cb(connected);
      } catch {}
    });
  }

  private dispatchEvent(event: string, data: any, raw: SyncMessage) {
    const handlers = this.listeners.get(event);
    if (handlers) {
      handlers.forEach((cb) => {
        try {
          cb(data, raw);
        } catch (e) {
          console.error(`[SyncWS] Error handling event ${event}:`, e);
        }
      });
    }

    // Also dispatch to catch-all wildcard '*' listeners
    const wildcardHandlers = this.listeners.get("*");
    if (wildcardHandlers) {
      wildcardHandlers.forEach((cb) => {
        try {
          cb(data, raw);
        } catch (e) {
          console.error(`[SyncWS] Error in wildcard handler:`, e);
        }
      });
    }
  }
}

export const syncWebSocket = new WebSocketClient();
export const wsService = syncWebSocket;
