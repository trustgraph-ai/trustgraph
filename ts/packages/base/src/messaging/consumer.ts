/**
 * High-level consumer with concurrency, retry, and rate-limit handling.
 *
 * Python reference: trustgraph-base/trustgraph/base/consumer.py
 */

import type { BackendConsumer, Message, PubSubBackend } from "../backend/types.js";
import type { Flow } from "../processor/flow.js";
import {
  MessagingHandlerError,
  TooManyRequestsError,
  messagingDeliveryError,
  messagingHandlerError,
  messagingLifecycleError,
  messagingTimeoutError,
} from "../errors.js";
import { Duration, Effect, Schedule } from "effect";
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

declare const ConsumerMessageType: unique symbol;

export interface Consumer<T> {
  readonly [ConsumerMessageType]?: (_: T) => T;
  readonly start: (flow: FlowContext) => Promise<void>;
  readonly stop: () => Promise<void>;
}

export function makeConsumer<T>(options: ConsumerOptions<T>): Consumer<T> {
  let backend: BackendConsumer<T> | null = null;
  let running = false;
  const isTooManyRequestsError = S.is(TooManyRequestsError);
  const concurrency = options.concurrency ?? 1;
  const rateLimitRetryMs = options.rateLimitRetryMs ?? 10_000;
  const rateLimitTimeoutMs = options.rateLimitTimeoutMs ?? 7_200_000;

  const runHandler = (
    message: T,
    properties: Record<string, string>,
    flow: FlowContext,
  ): Effect.Effect<void, TooManyRequestsError | MessagingHandlerError> =>
    Effect.tryPromise({
      try: () => options.handler(message, properties, flow),
      catch: (error) =>
        isTooManyRequestsError(error)
          ? error
          : messagingHandlerError(options.topic, options.subscription, error),
    });

  const handleWithRetry = Effect.fn("Consumer.handleWithRetry")(function* (
    message: Message<T>,
    flow: FlowContext,
  ) {
    const callHandler = runHandler(message.value(), message.properties(), flow);
    yield* callHandler.pipe(
      Effect.tapError((error) =>
        isTooManyRequestsError(error)
          ? Effect.logWarning("[Consumer] Rate limited, retrying", {
              topic: options.topic,
              subscription: options.subscription,
              retryMs: rateLimitRetryMs,
            })
          : Effect.void,
      ),
      Effect.retry({
        schedule: Schedule.spaced(Duration.millis(rateLimitRetryMs)),
        while: isTooManyRequestsError,
      }),
      Effect.timeoutOrElse({
        duration: Duration.millis(rateLimitTimeoutMs),
        orElse: () => Effect.fail(messagingTimeoutError("rate-limit", rateLimitTimeoutMs)),
      }),
      Effect.mapError((error) =>
        isTooManyRequestsError(error)
          ? messagingHandlerError(options.topic, options.subscription, error)
          : error,
      ),
    );
  });

  const consumeOnce = Effect.fn("Consumer.consumeOnce")(function* (flow: FlowContext) {
    const currentBackend = backend;
    if (currentBackend === null) {
      return yield* messagingLifecycleError(
        `${options.topic}:${options.subscription}`,
        "receive",
        "Consumer backend not started",
      );
    }

    const message = yield* Effect.tryPromise({
      try: () => currentBackend.receive(2000),
      catch: (error) => messagingDeliveryError(options.topic, "receive", error),
    });
    if (message === null) return;

    yield* handleWithRetry(message, flow).pipe(
      Effect.flatMap(() =>
        Effect.tryPromise({
          try: () => currentBackend.acknowledge(message),
          catch: (error) => messagingDeliveryError(options.topic, "acknowledge", error),
        }),
      ),
      Effect.catch((error) =>
        Effect.tryPromise({
          try: () => currentBackend.negativeAcknowledge(message),
          catch: (nakError) => messagingDeliveryError(options.topic, "negative-acknowledge", nakError),
        }).pipe(
          Effect.catch((nakError) =>
            Effect.logError("[Consumer] Failed to negative-acknowledge message", {
              error: nakError.message,
              topic: nakError.topic,
            }),
          ),
          Effect.flatMap(() => Effect.fail(error)),
        ),
      ),
    );
  });

  const consumeLoop = Effect.fn("Consumer.consumeLoop")(function* (flow: FlowContext) {
    yield* Effect.whileLoop({
      while: () => running,
      body: () =>
        consumeOnce(flow).pipe(
          Effect.catch((error) => {
            if (!running) return Effect.void;
            return Effect.logError("[Consumer] Error in consume loop", {
              error: error.message,
              topic: options.topic,
              subscription: options.subscription,
            }).pipe(
              Effect.flatMap(() => Effect.sleep(Duration.millis(1000))),
            );
          }),
        ),
      step: () => undefined,
    });
  });

  return {
    start: (flow) =>
      Effect.runPromise(
        Effect.gen(function* () {
          backend = yield* Effect.tryPromise({
            try: () =>
              options.pubsub.createConsumer<T>({
                topic: options.topic,
                subscription: options.subscription,
                initialPosition: options.initialPosition ?? "latest",
              }),
            catch: (error) =>
              messagingLifecycleError(`${options.topic}:${options.subscription}`, "create-consumer", error),
          });

          running = true;

          const workerIndexes = Array.from({ length: concurrency }, (_value, index) => index);
          yield* Effect.forEach(workerIndexes, () => consumeLoop(flow), {
            concurrency: "unbounded",
            discard: true,
          });
        }),
      ),
    stop: () =>
      Effect.runPromise(
        Effect.gen(function* () {
          running = false;
          const currentBackend = backend;
          backend = null;
          if (currentBackend !== null) {
            yield* Effect.tryPromise({
              try: () => currentBackend.close(),
              catch: (error) =>
                messagingLifecycleError(`${options.topic}:${options.subscription}`, "close-consumer", error),
            });
          }
        }),
      ),
  };
}
