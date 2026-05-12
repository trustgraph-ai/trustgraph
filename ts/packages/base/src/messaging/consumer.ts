/**
 * High-level consumer with concurrency, retry, and rate-limit handling.
 *
 * Python reference: trustgraph-base/trustgraph/base/consumer.py
 */

import type { PubSubBackend, BackendConsumer, Message } from "../backend/types.js";
import type { Flow } from "../processor/flow.js";
import { TooManyRequestsError } from "../errors.js";
import * as S from "effect/Schema";

export type MessageHandler<T> = (
  message: T,
  properties: Record<string, string>,
  flow: FlowContext,
) => Promise<void>;

export interface FlowContext<Requirements = never> {
  id: string;
  name: string;
  /** Reference to the owning Flow instance, giving handlers access to producers and parameters. */
  flow: Flow<Requirements>;
}

export interface ConsumerOptions<T> {
  pubsub: PubSubBackend;
  topic: string;
  subscription: string;
  handler: MessageHandler<T>;
  concurrency?: number;
  initialPosition?: "latest" | "earliest";
  rateLimitRetryMs?: number;
  rateLimitTimeoutMs?: number;
}

export class Consumer<T> {
  private backend: BackendConsumer<T> | null = null;
  private running = false;
  private abortController = new AbortController();
  private readonly options: ConsumerOptions<T>;

  private readonly concurrency: number;
  private readonly rateLimitRetryMs: number;

  constructor(options: ConsumerOptions<T>) {
    this.options = options;
    this.concurrency = options.concurrency ?? 1;
    this.rateLimitRetryMs = options.rateLimitRetryMs ?? 10_000;
  }

  async start(flow: FlowContext): Promise<void> {
    this.backend = await this.options.pubsub.createConsumer<T>({
      topic: this.options.topic,
      subscription: this.options.subscription,
      initialPosition: this.options.initialPosition ?? "latest",
    });

    this.running = true;

    // Spawn concurrent consumer tasks
    const tasks = Array.from({ length: this.concurrency }, () =>
      this.consumeLoop(flow),
    );
    // Run all concurrently — first rejection stops all
    await Promise.all(tasks);
  }

  async stop(): Promise<void> {
    this.running = false;
    this.abortController.abort();
    if (this.backend !== null) {
      await this.backend.close();
      this.backend = null;
    }
  }

  private async consumeLoop(flow: FlowContext): Promise<void> {
    while (this.running) {
      let msg: Message<T> | null = null;
      try {
        const backend = this.backend;
        if (backend === null) throw new Error("Consumer backend not started");

        msg = await backend.receive(2000);
        if (msg === null) continue;

        await this.handleWithRetry(msg, flow);
        await backend.acknowledge(msg);
      } catch (err) {
        if (!this.running) break;
        console.error("[Consumer] Error in consume loop:", err);
        if (msg !== null) {
          try {
            const backend = this.backend;
            if (backend !== null) {
              await backend.negativeAcknowledge(msg);
            }
          } catch (nakErr) {
            console.error("[Consumer] Failed to nak message:", nakErr);
          }
        }
        await sleep(1000);
      }
    }
  }

  private async handleWithRetry(msg: Message<T>, flow: FlowContext): Promise<void> {
    try {
      await this.options.handler(msg.value(), msg.properties(), flow);
    } catch (err) {
      if (S.is(TooManyRequestsError)(err)) {
        console.warn(`[Consumer] Rate limited, retrying in ${this.rateLimitRetryMs}ms`);
        await sleep(this.rateLimitRetryMs);
        await this.options.handler(msg.value(), msg.properties(), flow);
      } else {
        throw err;
      }
    }
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
