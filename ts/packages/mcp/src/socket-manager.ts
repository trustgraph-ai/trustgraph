/**
 * WebSocket manager for communicating with the TrustGraph gateway.
 *
 * Maintains a persistent connection per user and handles request/response
 * correlation via UUIDs.
 *
 * Python reference: trustgraph-mcp/trustgraph/mcp_server/tg_socket.py
 */

import WebSocket from "ws";
import { randomUUID } from "node:crypto";

export interface SocketManagerConfig {
  gatewayUrl: string;
  token?: string;
}

interface PendingRequest {
  resolve: (value: unknown) => void;
  reject: (error: Error) => void;
  responses: unknown[];
  streaming: boolean;
  onChunk?: (chunk: unknown) => void;
}

export class SocketManager {
  private ws: WebSocket | null = null;
  private pending = new Map<string, PendingRequest>();
  private connected = false;

  constructor(private readonly config: SocketManagerConfig) {}

  async connect(): Promise<void> {
    if (this.connected) return;

    const url = new URL(this.config.gatewayUrl);
    if (this.config.token) {
      url.searchParams.set("token", this.config.token);
    }

    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(url.toString());

      this.ws.on("open", () => {
        this.connected = true;
        resolve();
      });

      this.ws.on("error", (err) => {
        if (!this.connected) reject(err);
        else console.error("[SocketManager] WebSocket error:", err);
      });

      this.ws.on("message", (data) => {
        try {
          const msg = JSON.parse(data.toString());
          const { id, response, error, complete } = msg;

          const req = this.pending.get(id);
          if (!req) return;

          if (error) {
            req.reject(new Error(`${error.type}: ${error.message}`));
            this.pending.delete(id);
            return;
          }

          if (req.streaming && req.onChunk) {
            req.onChunk(response);
          }

          req.responses.push(response);

          if (complete) {
            req.resolve(req.streaming ? req.responses : response);
            this.pending.delete(id);
          }
        } catch (err) {
          console.error("[SocketManager] Failed to parse message:", err);
        }
      });

      this.ws.on("close", () => {
        this.connected = false;
        // Reject all pending requests
        for (const [id, req] of this.pending) {
          req.reject(new Error("WebSocket closed"));
        }
        this.pending.clear();
      });
    });
  }

  async request(
    service: string,
    requestData: Record<string, unknown>,
    options?: {
      flowId?: string;
      timeoutMs?: number;
      onChunk?: (chunk: unknown) => void;
    },
  ): Promise<unknown> {
    await this.connect();
    if (!this.ws) throw new Error("Not connected");

    const id = randomUUID();
    const timeoutMs = options?.timeoutMs ?? 300_000;

    const msg = {
      id,
      service,
      flow: options?.flowId ?? "default",
      request: requestData,
    };

    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`Request timed out after ${timeoutMs}ms`));
      }, timeoutMs);

      this.pending.set(id, {
        resolve: (value) => {
          clearTimeout(timer);
          resolve(value);
        },
        reject: (err) => {
          clearTimeout(timer);
          reject(err);
        },
        responses: [],
        streaming: !!options?.onChunk,
        onChunk: options?.onChunk,
      });

      this.ws!.send(JSON.stringify(msg));
    });
  }

  async close(): Promise<void> {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
      this.connected = false;
    }
  }
}
