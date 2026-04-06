/**
 * Fan-out subscriber: routes responses to waiting callers by request ID.
 *
 * Python reference: trustgraph-base/trustgraph/base/subscriber.py
 */

import type { PubSubBackend, BackendConsumer } from "../backend/types.js";

type Resolver<T> = {
  queue: AsyncQueue<T>;
};

/**
 * Simple async queue for inter-task communication (replaces asyncio.Queue).
 */
export class AsyncQueue<T> {
  private buffer: T[] = [];
  private waiters: Array<(value: T) => void> = [];

  push(item: T): void {
    const waiter = this.waiters.shift();
    if (waiter) {
      waiter(item);
    } else {
      this.buffer.push(item);
    }
  }

  async pop(timeoutMs?: number): Promise<T> {
    const buffered = this.buffer.shift();
    if (buffered !== undefined) return buffered;

    return new Promise<T>((resolve, reject) => {
      let timer: ReturnType<typeof setTimeout> | undefined;

      const waiter = (value: T) => {
        if (timer) clearTimeout(timer);
        resolve(value);
      };

      this.waiters.push(waiter);

      if (timeoutMs !== undefined) {
        timer = setTimeout(() => {
          const idx = this.waiters.indexOf(waiter);
          if (idx !== -1) this.waiters.splice(idx, 1);
          reject(new Error(`Queue.pop timed out after ${timeoutMs}ms`));
        }, timeoutMs);
      }
    });
  }

  get length(): number {
    return this.buffer.length;
  }
}

export class Subscriber<T> {
  private backend: BackendConsumer<T> | null = null;
  private running = false;

  // ID-specific subscriptions (request/response correlation)
  private idSubscribers = new Map<string, Resolver<T>>();
  // Wildcard subscribers (receive all messages)
  private allSubscribers = new Map<string, Resolver<T>>();

  constructor(
    private readonly pubsub: PubSubBackend,
    private readonly topic: string,
    private readonly subscription: string,
  ) {}

  async start(): Promise<void> {
    this.backend = await this.pubsub.createConsumer<T>({
      topic: this.topic,
      subscription: this.subscription,
    });
    this.running = true;
    // Start the dispatch loop (fire and forget — runs until stop)
    this.dispatchLoop().catch((err) => {
      if (this.running) console.error("[Subscriber] dispatch loop error:", err);
    });
  }

  async stop(): Promise<void> {
    this.running = false;
    if (this.backend) {
      await this.backend.close();
      this.backend = null;
    }
  }

  subscribe(id: string): AsyncQueue<T> {
    const queue = new AsyncQueue<T>();
    this.idSubscribers.set(id, { queue });
    return queue;
  }

  subscribeAll(id: string): AsyncQueue<T> {
    const queue = new AsyncQueue<T>();
    this.allSubscribers.set(id, { queue });
    return queue;
  }

  unsubscribe(id: string): void {
    this.idSubscribers.delete(id);
  }

  unsubscribeAll(id: string): void {
    this.allSubscribers.delete(id);
  }

  private async dispatchLoop(): Promise<void> {
    let consecutiveErrors = 0;
    while (this.running) {
      try {
        const msg = await this.backend!.receive(2000);
        if (!msg) continue;

        consecutiveErrors = 0;

        const props = msg.properties();
        const id = props.id;
        const value = msg.value();

        // Route to ID-specific subscriber
        if (id) {
          const sub = this.idSubscribers.get(id);
          if (sub) {
            sub.queue.push(value);
          }
        }

        // Broadcast to all-subscribers
        for (const sub of this.allSubscribers.values()) {
          sub.queue.push(value);
        }

        await this.backend!.acknowledge(msg);
      } catch (err) {
        if (!this.running) break;
        consecutiveErrors++;
        if (consecutiveErrors <= 3) {
          console.error("[Subscriber] Error:", err);
        } else if (consecutiveErrors === 4) {
          console.error("[Subscriber] Suppressing further errors (will retry with backoff)");
        }
        // Exponential backoff: 1s, 2s, 4s, max 10s
        const delay = Math.min(1000 * Math.pow(2, consecutiveErrors - 1), 10_000);
        await new Promise((r) => setTimeout(r, delay));
      }
    }
  }
}
