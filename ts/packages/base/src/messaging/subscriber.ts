/**
 * Fan-out subscriber: routes responses to waiting callers by request ID.
 *
 * Python reference: trustgraph-base/trustgraph/base/subscriber.py
 */

import type { PubSubBackend, BackendConsumer } from "../backend/types.js";
import { Duration, Effect, Fiber } from "effect";
import { messagingDeliveryError, messagingLifecycleError, messagingTimeoutError } from "../errors.js";

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
    pop: (timeoutMs) => {
      const buffered = buffer.shift();
      if (buffered !== undefined) return Promise.resolve(buffered);

      const take = Effect.callback<T>((resume) => {
        const waiter = (value: T) => {
          resume(Effect.succeed(value));
        };

        waiters.push(waiter);

        return Effect.sync(() => {
          const idx = waiters.indexOf(waiter);
          if (idx !== -1) waiters.splice(idx, 1);
        });
      });

      return Effect.runPromise(
        timeoutMs === undefined
          ? take
          : take.pipe(
              Effect.timeout(Duration.millis(timeoutMs)),
              Effect.catchTag("TimeoutError", () =>
                Effect.fail(messagingTimeoutError("queue.pop", timeoutMs)),
              ),
            ),
      );
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
  let fiber: Fiber.Fiber<void, never> | null = null;

  // ID-specific subscriptions (request/response correlation)
  const idSubscribers = new Map<string, Resolver<T>>();
  // Wildcard subscribers (receive all messages)
  const allSubscribers = new Map<string, Resolver<T>>();

  const dispatchLoop = Effect.fn("Subscriber.dispatchLoop")(function* () {
    let consecutiveErrors = 0;
    const dispatchOnce = Effect.fn("Subscriber.dispatchOnce")(function* () {
          const currentBackend = backend;
          if (currentBackend === null) {
            return yield* messagingLifecycleError(
              `${topic}:${subscription}`,
              "dispatch",
              "Subscriber backend not started",
            );
          }

          const msg = yield* Effect.tryPromise({
            try: () => currentBackend.receive(2000),
            catch: (error) => messagingDeliveryError(topic, "receive", error),
          });
          if (msg === null) return;

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

          yield* Effect.tryPromise({
            try: () => currentBackend.acknowledge(msg),
            catch: (error) => messagingDeliveryError(topic, "acknowledge", error),
          });
    });

    yield* Effect.whileLoop({
      while: () => running,
      body: () =>
        dispatchOnce().pipe(
          Effect.catch((error) => {
            if (!running) return Effect.void;
            consecutiveErrors++;
            const logEffect = consecutiveErrors <= 3
              ? Effect.logError("[Subscriber] Error", { error })
              : consecutiveErrors === 4
                ? Effect.logError("[Subscriber] Suppressing further errors (will retry with backoff)", { error })
                : Effect.void;
            const delay = Math.min(1000 * 2 ** (consecutiveErrors - 1), 10_000);
            return logEffect.pipe(Effect.flatMap(() => Effect.sleep(Duration.millis(delay))));
          }),
        ),
      step: () => undefined,
    });
  });

  return {
    start: () =>
      Effect.runPromise(
        Effect.gen(function* () {
          backend = yield* Effect.tryPromise({
            try: () =>
              pubsub.createConsumer<T>({
                topic,
                subscription,
              }),
            catch: (error) =>
              messagingLifecycleError(`${topic}:${subscription}`, "create-consumer", error),
          });
          running = true;
          fiber = yield* dispatchLoop().pipe(Effect.forkDetach);
        }),
      ),
    stop: () =>
      Effect.runPromise(
        Effect.gen(function* () {
          running = false;
          const activeFiber = fiber;
          fiber = null;
          if (activeFiber !== null) {
            yield* Fiber.interrupt(activeFiber);
          }
          const currentBackend = backend;
          if (currentBackend !== null) {
            backend = null;
            yield* Effect.tryPromise({
              try: () => currentBackend.close(),
              catch: (error) =>
                messagingLifecycleError(`${topic}:${subscription}`, "close-consumer", error),
            });
          }
        }),
      ),
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
