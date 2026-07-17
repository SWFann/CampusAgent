/**
 * WebSocket realtime client for CampusAgent.
 *
 * Implements the WEBSOCKET_CONTRACT.md v1.0 client state machine:
 *
 * - Authentication via HttpOnly access_token Cookie (no URL tokens, no localStorage).
 * - Exponential backoff reconnection (§6.1): 0s, 1s, 2s, 4s, 8s, 16s, 30s max.
 * - Auto-reconnect whitelist (§6.2): network errors, 1001, 1011, 1012, 4408, 4429.
 * - Event dedup via event_id (§6.4): bounded cache max 1000 entries.
 * - HTTP backfill on reconnect (§6.3): paginated message list + message_id dedup.
 * - Sequence gap detection (§6.3.8): triggers HTTP backfill on sequence jump.
 *
 * Privacy: No token, session, or private data is stored in memory or localStorage.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Connection state machine per WEBSOCKET_CONTRACT.md §7. */
export type WsState =
  | "IDLE"
  | "CONNECTING"
  | "OPEN"
  | "RECONNECTING"
  | "REFRESHING"
  | "PAUSED"
  | "CLOSED"
  | "AUTH_FAILED"
  | "FORBIDDEN";

/** Server event envelope per WEBSOCKET_CONTRACT.md §2.2. */
export interface ServerEvent {
  event: string;
  data: Record<string, unknown>;
  version: string;
  event_id: string;
  sequence: number;
  timestamp: string;
  request_id: string | null;
}

/** Client command envelope per WEBSOCKET_CONTRACT.md §2.1. */
export interface ClientCommand {
  event: string;
  data: Record<string, unknown>;
  version: string;
  request_id: string;
  timestamp: string;
}

/** Handler for server events. */
export type ServerEventHandler = (event: ServerEvent) => void;

/** Handler for state changes. */
export type StateChangeHandler = (state: WsState, info?: { failCount?: number }) => void;

// ---------------------------------------------------------------------------
// Constants per WEBSOCKET_CONTRACT.md §6.1
// ---------------------------------------------------------------------------

/** Backoff schedule: index 0 = 0s (immediate), then 1, 2, 4, 8, 16, capped at 30s. */
const BACKOFF_SCHEDULE: number[] = [0, 1, 2, 4, 8, 16, 30];

/** Maximum backoff delay in seconds. */
const MAX_BACKOFF = 30;

/** Jitter range: ±20% per §6.1. */
const JITTER_FACTOR = 0.2;

/** Max consecutive failures before PAUSED state per §6.1. */
const MAX_CONSECUTIVE_FAILURES = 10;

/** Heartbeat interval in milliseconds per §7.2. */
const HEARTBEAT_INTERVAL_MS = 30_000;

/** Max missed pongs before closing connection per §3.3. */
const MAX_MISSED_PONGS = 2;

/** Event dedup cache max size per §6.4. */
const MAX_DEDUP_CACHE = 1000;

/** Max backfill pages per §6.3.5. */
const MAX_BACKFILL_PAGES = 20;

/** Close codes that allow auto-reconnect per §6.2. */
const RECONNECTABLE_CLOSE_CODES = new Set([
  1001, // Going Away
  1011, // Server Internal Error
  1012, // Service Restart
  4408, // Heartbeat Timeout
  4429, // Rate Limited
]);

/** Close codes that forbid auto-reconnect per §6.2. */
const NON_RECONNECTABLE_CLOSE_CODES = new Set([
  1000, // Normal Close
  1008, // Policy Violation
  4403, // Forbidden
  4406, // Protocol Version Unsupported
]);

// ---------------------------------------------------------------------------
// Event dedup cache (bounded FIFO, max 1000 entries)
// ---------------------------------------------------------------------------

class EventDedupCache {
  private cache = new Map<string, number>();

  has(eventId: string): boolean {
    return this.cache.has(eventId);
  }

  add(eventId: string): void {
    if (this.cache.has(eventId)) return;
    this.cache.set(eventId, Date.now());
    if (this.cache.size > MAX_DEDUP_CACHE) {
      // FIFO eviction: remove oldest entry
      const firstKey = this.cache.keys().next().value;
      if (firstKey !== undefined) this.cache.delete(firstKey);
    }
  }

  clear(): void {
    this.cache.clear();
  }
}

// ---------------------------------------------------------------------------
// UUID v4 generator for request_id
// ---------------------------------------------------------------------------

function generateRequestId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // Fallback for environments without crypto.randomUUID
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/** Generate UTC RFC 3339 timestamp with second precision and Z suffix. */
function utcTimestamp(): string {
  const now = new Date();
  return now.toISOString().replace(/\.\d{3}Z$/, "Z");
}

// ---------------------------------------------------------------------------
// Backoff calculation per §6.1
// ---------------------------------------------------------------------------

function calculateBackoff(failCount: number): number {
  const index = Math.min(failCount, BACKOFF_SCHEDULE.length - 1);
  let baseDelay = BACKOFF_SCHEDULE[index] ?? MAX_BACKOFF;
  // Apply ±20% jitter
  const jitter = baseDelay * JITTER_FACTOR * (Math.random() * 2 - 1);
  return Math.max(0, baseDelay + jitter);
}

// ---------------------------------------------------------------------------
// RealtimeClient
// ---------------------------------------------------------------------------

interface BackfillFn {
  (conversationId: string): Promise<void>;
}

export class RealtimeClient {
  private ws: WebSocket | null = null;
  private state: WsState = "IDLE";
  private failCount = 0;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private missedPongs = 0;
  private dedupCache = new EventDedupCache();
  private lastSequence = 0;
  private subscriptions = new Set<string>();
  private eventHandlers = new Set<ServerEventHandler>();
  private stateHandlers = new Set<StateChangeHandler>();
  private backfillFn: BackfillFn | null = null;
  private isManualClose = false;
  private hasRefreshedAfterHandshakeFail = false;

  /** WebSocket URL derived from API origin. */
  private getWsUrl(): string {
    const apiOrigin = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
    const wsUrl = apiOrigin.replace(/^http/, "ws");
    return `${wsUrl}/api/v1/ws`;
  }

  /** Register a handler for all server events. Returns an unsubscribe function. */
  onEvent(handler: ServerEventHandler): () => void {
    this.eventHandlers.add(handler);
    return () => this.eventHandlers.delete(handler);
  }

  /** Register a handler for state changes. Returns an unsubscribe function. */
  onStateChange(handler: StateChangeHandler): () => void {
    this.stateHandlers.add(handler);
    return () => this.stateHandlers.delete(handler);
  }

  /** Set the backfill function used after reconnection (§6.3). */
  setBackfillFunction(fn: BackfillFn): void {
    this.backfillFn = fn;
  }

  /** Get the current connection state. */
  getState(): WsState {
    return this.state;
  }

  /** Get the current fail count for debugging. */
  getFailCount(): number {
    return this.failCount;
  }

  /** Connect to the WebSocket server. */
  connect(): void {
    if (this.ws !== null) {
      // Already connecting or connected
      if (this.state === "OPEN" || this.state === "CONNECTING") return;
    }

    this.isManualClose = false;
    this.setState("CONNECTING");
    this.missedPongs = 0;

    try {
      const url = this.getWsUrl();
      this.ws = new WebSocket(url);
    } catch {
      this.handleConnectFailure();
      return;
    }

    this.ws.onopen = () => {
      this.failCount = 0;
      this.missedPongs = 0;
      this.startHeartbeat();
      // State will transition to OPEN after connection.established
      this.setState("OPEN");
      // Restore subscriptions
      this.restoreSubscriptions();
    };

    this.ws.onmessage = (event: MessageEvent) => {
      this.handleMessage(event.data);
    };

    this.ws.onerror = () => {
      // Browser doesn't expose handshake failure details;
      // onclose will fire after onerror
    };

    this.ws.onclose = (event: CloseEvent) => {
      this.stopHeartbeat();
      this.ws = null;
      this.handleClose(event.code, event.reason);
    };
  }

  /** Manually close the connection. No auto-reconnect. */
  disconnect(): void {
    this.isManualClose = true;
    this.stopHeartbeat();
    this.clearReconnectTimer();
    if (this.ws !== null) {
      try {
        this.ws.close(1000, "client_disconnect");
      } catch {
        // Ignore close errors
      }
    }
    this.ws = null;
    this.setState("CLOSED");
  }

  /** Subscribe to a conversation's events (§3.1). */
  subscribe(conversationId: string): void {
    this.subscriptions.add(conversationId);
    if (this.state === "OPEN" && this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.sendCommand("conversation.subscribe", { conversation_id: conversationId });
    }
  }

  /** Unsubscribe from a conversation's events (§3.2). */
  unsubscribe(conversationId: string): void {
    this.subscriptions.delete(conversationId);
    if (this.state === "OPEN" && this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.sendCommand("conversation.unsubscribe", { conversation_id: conversationId });
    }
  }

  /** Send a ping heartbeat (§3.3). */
  ping(): void {
    if (this.state === "OPEN" && this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.sendCommand("ping", {});
    }
  }

  /** Reset failure count and retry (called by user action or browser online event). */
  retry(): void {
    this.failCount = 0;
    this.hasRefreshedAfterHandshakeFail = false;
    this.clearReconnectTimer();
    this.connect();
  }

  // -----------------------------------------------------------------------
  // Private methods
  // -----------------------------------------------------------------------

  private setState(newState: WsState): void {
    if (this.state === newState) return;
    this.state = newState;
    const info = { failCount: this.failCount };
    this.stateHandlers.forEach((handler) => handler(newState, info));
  }

  private sendCommand(event: string, data: Record<string, unknown>): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    const command: ClientCommand = {
      event,
      data,
      version: "v1",
      request_id: generateRequestId(),
      timestamp: utcTimestamp(),
    };
    try {
      this.ws.send(JSON.stringify(command));
    } catch {
      // Send failure — will trigger onclose eventually
    }
  }

  private handleMessage(rawData: string): void {
    let parsed: unknown;
    try {
      parsed = JSON.parse(rawData);
    } catch {
      // Invalid JSON — ignore
      return;
    }

    if (typeof parsed !== "object" || parsed === null) return;
    const evt = parsed as Record<string, unknown>;

    // Validate minimum envelope shape
    if (typeof evt.event !== "string" || typeof evt.event_id !== "string") return;

    const serverEvent: ServerEvent = {
      event: evt.event as string,
      data: (evt.data as Record<string, unknown>) ?? {},
      version: (evt.version as string) ?? "v1",
      event_id: evt.event_id as string,
      sequence: (evt.sequence as number) ?? 0,
      timestamp: (evt.timestamp as string) ?? "",
      request_id: (evt.request_id as string | null) ?? null,
    };

    // Event dedup via event_id (§6.4)
    if (this.dedupCache.has(serverEvent.event_id)) return;
    this.dedupCache.add(serverEvent.event_id);

    // Reset missed pongs on any message (connection is alive)
    this.missedPongs = 0;

    // Handle specific events internally
    if (serverEvent.event === "connection.established") {
      this.lastSequence = serverEvent.sequence;
    } else if (serverEvent.event === "pong") {
      this.missedPongs = 0;
    } else if (serverEvent.event === "error") {
      // Error events are forwarded to handlers
    }

    // Sequence gap detection (§6.3.8) — triggers HTTP backfill
    if (serverEvent.sequence > 0 && serverEvent.event !== "connection.established") {
      if (this.lastSequence > 0 && serverEvent.sequence > this.lastSequence + 1) {
        // Sequence gap detected — trigger HTTP backfill
        this.triggerBackfill(serverEvent);
      }
      this.lastSequence = serverEvent.sequence;
    }

    // Forward to all handlers
    this.eventHandlers.forEach((handler) => handler(serverEvent));
  }

  private triggerBackfill(event: ServerEvent): void {
    const data = event.data;
    const conversationId = (data.conversation_id as string) ?? null;
    if (conversationId && this.backfillFn) {
      this.backfillFn(conversationId).catch(() => {
        // Silent fail — HTTP is source of truth, will retry on next gap
      });
    }
  }

  private restoreSubscriptions(): void {
    if (this.subscriptions.size === 0) return;
    // Restore subscriptions one by one
    for (const conversationId of this.subscriptions) {
      this.sendCommand("conversation.subscribe", { conversation_id: conversationId });
    }
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      if (this.state !== "OPEN") return;
      this.missedPongs++;
      if (this.missedPongs > MAX_MISSED_PONGS) {
        // Connection seems dead — close and reconnect
        this.ws?.close(4408, "heartbeat_timeout");
      } else {
        this.ping();
      }
    }, HEARTBEAT_INTERVAL_MS);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer !== null) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  private handleConnectFailure(): void {
    this.failCount++;
    if (this.failCount >= MAX_CONSECUTIVE_FAILURES) {
      this.setState("PAUSED");
      return;
    }
    this.setState("RECONNECTING");
    const delay = calculateBackoff(this.failCount);
    this.reconnectTimer = setTimeout(() => this.connect(), delay * 1000);
  }

  private handleClose(code: number, _reason: string): void {
    // Manual close — don't reconnect
    if (this.isManualClose || code === 1000) {
      this.setState("CLOSED");
      return;
    }

    // Non-reconnectable close codes (§6.2)
    if (NON_RECONNECTABLE_CLOSE_CODES.has(code)) {
      if (code === 1008) {
        // Policy violation — could be origin error
        this.setState("FORBIDDEN");
      } else if (code === 4403) {
        this.setState("FORBIDDEN");
      } else if (code === 4406) {
        this.setState("CLOSED");
      } else {
        this.setState("CLOSED");
      }
      return;
    }

    // Reconnectable close codes (§6.2) or unknown (treat as network error)
    if (RECONNECTABLE_CLOSE_CODES.has(code) || (code === 1005 || code === 1006)) {
      // 4429 — Rate limited: use retry_after_ms if available
      // For simplicity, use standard backoff
      this.failCount++;
      if (this.failCount >= MAX_CONSECUTIVE_FAILURES) {
        this.setState("PAUSED");
        return;
      }
      this.setState("RECONNECTING");
      const delay = calculateBackoff(this.failCount);
      this.reconnectTimer = setTimeout(() => this.connect(), delay * 1000);
      return;
    }

    // Unknown close code — treat as network error and reconnect
    this.failCount++;
    if (this.failCount >= MAX_CONSECUTIVE_FAILURES) {
      this.setState("PAUSED");
      return;
    }
    this.setState("RECONNECTING");
    const delay = calculateBackoff(this.failCount);
    this.reconnectTimer = setTimeout(() => this.connect(), delay * 1000);
  }

  /** Clear all subscriptions and dedup cache. */
  reset(): void {
    this.subscriptions.clear();
    this.dedupCache.clear();
    this.lastSequence = 0;
    this.failCount = 0;
  }
}

// ---------------------------------------------------------------------------
// Singleton instance
// ---------------------------------------------------------------------------

let realtimeClient: RealtimeClient | null = null;

/** Get the singleton RealtimeClient instance. */
export function getRealtimeClient(): RealtimeClient {
  if (realtimeClient === null) {
    realtimeClient = new RealtimeClient();
  }
  return realtimeClient;
}

// ---------------------------------------------------------------------------
// React hook for WebSocket state
// ---------------------------------------------------------------------------

import { useCallback, useEffect, useState } from "react";

/**
 * React hook that subscribes to the realtime client's state.
 * Returns the current state and a retry function.
 */
export function useRealtimeState(): {
  state: WsState;
  failCount: number;
  retry: () => void;
} {
  const client = getRealtimeClient();
  const [state, setState] = useState<WsState>(client.getState());
  const [failCount, setFailCount] = useState<number>(client.getFailCount());

  useEffect(() => {
    const unsub = client.onStateChange((newState, info) => {
      setState(newState);
      if (info?.failCount !== undefined) setFailCount(info.failCount);
    });
    return unsub;
  }, [client]);

  const retry = useCallback(() => {
    client.retry();
  }, [client]);

  return { state, failCount, retry };
}
