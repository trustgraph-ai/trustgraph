/**
 * High-level consumer with concurrency, retry, and rate-limit handling.
 *
 * Python reference: trustgraph-base/trustgraph/base/consumer.py
 */

import type { PubSubBackend } from "../backend/types.js";
import { PubSub } from "../backend/pubsub.js";
import type { Flow } from "../processor/flow.js";
import {
  MessagingHandlerError,
  TooManyRequestsError,
  messagingHandlerError,
  messagingLifecycleError,
} from "../errors.js";
import { Effect, Exit, Layer, ManagedRuntime, Scope } from "effect";
import * as P from "effect/Predicate";
import * as S from "effect/Schema";
import { loadMessagingRuntimeConfig } from "../runtime/messaging-config.js";
import { makeEffectConsumerFromPubSub, type EffectConsumer } from "./runtime.js";

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

interface ConsumerRuntime {
  readonly scope: Scope.Closeable;
  readonly consumer: EffectConsumer;
}

const consumerRuntime = ManagedRuntime.make(Layer.empty);

export function makeConsumer<T>(options: ConsumerOptions<T>): Consumer<T> {
  let runtime: ConsumerRuntime | null = null;
  const isTooManyRequestsError = S.is(TooManyRequestsError);

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

  return {
    start: (flow) =>
      P.isNotNull(runtime)
        ? Promise.resolve()
        : consumerRuntime.runPromise(
            Effect.gen(function* () {
              const scope = yield* Scope.make();
              const startConsumer = Effect.gen(function* () {
                const config = yield* loadMessagingRuntimeConfig();
                const consumer = yield* makeEffectConsumerFromPubSub<T, TooManyRequestsError | MessagingHandlerError, never>(
                  PubSub.fromBackend(options.pubsub),
                  config,
                  {
                    topic: options.topic,
                    subscription: options.subscription,
                    handler: runHandler,
                    ...(options.concurrency === undefined ? {} : { concurrency: options.concurrency }),
                    initialPosition: options.initialPosition ?? "latest",
                    ...(options.rateLimitRetryMs === undefined ? {} : { rateLimitRetryMs: options.rateLimitRetryMs }),
                    ...(options.rateLimitTimeoutMs === undefined
                      ? {}
                      : { rateLimitTimeoutMs: options.rateLimitTimeoutMs }),
                  },
                  flow,
                ).pipe(
                  Scope.provide(scope),
                  Effect.mapError((error) =>
                    messagingLifecycleError(`${options.topic}:${options.subscription}`, "create-consumer", error)
                  ),
                );
                runtime = { scope, consumer };
              });

              yield* startConsumer.pipe(
                Effect.onError((cause) => Scope.close(scope, Exit.failCause(cause))),
              );
            }),
          ),
    stop: () => {
      const current = runtime;
      runtime = null;
      return current === null
        ? Promise.resolve()
        : consumerRuntime.runPromise(
            current.consumer.stop.pipe(
              Effect.ensuring(Scope.close(current.scope, Exit.void)),
            ),
          );
    },
  };
}
