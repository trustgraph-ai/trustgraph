/**
 * WebSocket multiplexer — handles concurrent requests over a single connection.
 *
 * Python reference: trustgraph-flow/trustgraph/gateway/dispatch/mux.py
 */

import { AsyncQueue } from "@trustgraph/base";

const MAX_OUTSTANDING = 15;
const MAX_QUEUE_SIZE = 10;

export interface MuxRequest {
  id: string;
  service: string;
  flow?: string;
  request: Record<string, unknown>;
}

export type MuxHandler = (
  request: MuxRequest,
  respond: (response: unknown, complete: boolean) => Promise<void>,
) => Promise<void>;

export class Mux {
  private queue = new AsyncQueue<MuxRequest>();
  private outstanding = 0;
  private running = true;
  private readonly handler: MuxHandler;

  constructor(handler: MuxHandler) {
    this.handler = handler;
  }

  receive(request: MuxRequest): void {
    if (this.queue.length >= MAX_QUEUE_SIZE) {
      console.warn("[Mux] Queue full, dropping request:", request.id);
      return;
    }
    this.queue.push(request);
  }

  async run(send: (data: string) => void): Promise<void> {
    while (this.running) {
      if (this.outstanding >= MAX_OUTSTANDING) {
        await sleep(50);
        continue;
      }

      try {
        const request = await this.queue.pop(1000);
        this.outstanding++;

        // Fire and forget — error handling inside
        this.processRequest(request, send).finally(() => {
          this.outstanding--;
        });
      } catch {
        // Timeout on queue pop — just loop
      }
    }
  }

  stop(): void {
    this.running = false;
  }

  private async processRequest(
    request: MuxRequest,
    send: (data: string) => void,
  ): Promise<void> {
    try {
      await this.handler(request, async (response, complete) => {
        send(JSON.stringify({ id: request.id, response, complete }));
      });
    } catch (err) {
      send(
        JSON.stringify({
          id: request.id,
          error: { type: "internal", message: String(err) },
          complete: true,
        }),
      );
    }
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
