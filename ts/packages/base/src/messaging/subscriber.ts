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
export interface AsyncQueue<T> {
  readonly push: (item: T) => void;
  readonly pop: (timeoutMs?: number) => Promise<T>;
  readonly length: number;
}

export function makeAsyncQueue<T>(): AsyncQueue<T> {
  const buffer: T[] = [];
  const waiters: Array<(value: T) => void> = [];

  return {
    push: (item) => {
      const waiter = waiters.shift();
      if (waiter !== undefined) {
        waiter(item);
      } else {
        buffer.push(item);
      }
    },
    pop: async (timeoutMs) => {
      const buffered = buffer.shift();
      if (buffered !== undefined) return buffered;

      return new Promise<T>((resolve, reject) => {
        let timer: ReturnType<typeof setTimeout> | undefined;

        const waiter = (value: T) => {
          if (timer !== undefined) clearTimeout(timer);
          resolve(value);
        };

        waiters.push(waiter);

        if (timeoutMs !== undefined) {
          timer = setTimeout(() => {
            const idx = waiters.indexOf(waiter);
            if (idx !== -1) waiters.splice(idx, 1);
            reject(new Error(`Queue.pop timed out after ${timeoutMs}ms`));
          }, timeoutMs);
        }
      });
    },
    get length() {
      return buffer.length;
    },
  };
}

export interface Subscriber<T> {
  readonly start: () => Promise<void>;
  readonly stop: () => Promise<void>;
  readonly subscribe: (id: string) => AsyncQueue<T>;
  readonly subscribeAll: (id: string) => AsyncQueue<T>;
  readonly unsubscribe: (id: string) => void;
  readonly unsubscribeAll: (id: string) => void;
}

export function makeSubscriber<T>(
  pubsub: PubSubBackend,
  topic: string,
  subscription: string,
): Subscriber<T> {
  let backend: BackendConsumer<T> | null = null;
  let running = false;

  // ID-specific subscriptions (request/response correlation)
  const idSubscribers = new Map<string, Resolver<T>>();
  // Wildcard subscribers (receive all messages)
  const allSubscribers = new Map<string, Resolver<T>>();

  const dispatchLoop = async (): Promise<void> => {
    let consecutiveErrors = 0;
    while (running) {
      try {
        const currentBackend = backend;
        if (currentBackend === null) throw new Error("Subscriber backend not started");

        const msg = await currentBackend.receive(2000);
        if (msg === null) continue;

        consecutiveErrors = 0;

        const props = msg.properties();
        const id = props.id;
        const value = msg.value();

        // Route to ID-specific subscriber
        if (id !== undefined && id.length > 0) {
          const sub = idSubscribers.get(id);
          if (sub !== undefined) {
            sub.queue.push(value);
          }
        }

        // Broadcast to all-subscribers
        for (const sub of allSubscribers.values()) {
          sub.queue.push(value);
        }

        await currentBackend.acknowledge(msg);
      } catch (err) {
        if (!running) break;
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
  };

  return {
    start: async () => {
      backend = await pubsub.createConsumer<T>({
        topic,
        subscription,
      });
      running = true;
      // Start the dispatch loop (fire and forget; runs until stop).
      dispatchLoop().catch((err) => {
        if (running === true) console.error("[Subscriber] dispatch loop error:", err);
      });
    },
    stop: async () => {
      running = false;
      if (backend !== null) {
        await backend.close();
        backend = null;
      }
    },
    subscribe: (id) => {
      const queue = makeAsyncQueue<T>();
      idSubscribers.set(id, { queue });
      return queue;
    },
    subscribeAll: (id) => {
      const queue = makeAsyncQueue<T>();
      allSubscribers.set(id, { queue });
      return queue;
    },
    unsubscribe: (id) => {
      idSubscribers.delete(id);
    },
    unsubscribeAll: (id) => {
      allSubscribers.delete(id);
    },
  };
}
