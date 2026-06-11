/**
 * High-level consumer with concurrency, retry, and rate-limit handling.
 *
 * Python reference: trustgraph-base/trustgraph/base/consumer.py
 */

import type { PubSubBackend } from "../backend/types.js";
import { PubSub } from "../backend/pubsub.js";
import type { Flow } from "../processor/flow.js";
import type {
  MessagingHandlerError,
  MessagingLifecycleError,
} from "../errors.js";
import {
  TooManyRequestsError,
  messagingHandlerError,
  messagingLifecycleError,
} from "../errors.js";
import type { Config as EffectConfig, } from "effect";
import { Effect, Exit, Scope } from "effect";
import * as P from "effect/Predicate";
import * as S from "effect/Schema";
import { loadMessagingRuntimeConfig } from "../runtime/index.ts";
import type {
  EffectConsumer,
} from "./runtime.js";
import {
  makeEffectConsumerFromPubSub,
} from "./runtime.js";

export type MessageHandler<T> = (
  message: T,
  properties: Record<string, string>,
  flow: FlowContext,
) => Effect.Effect<void, TooManyRequestsError | MessagingHandlerError>;

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
  readonly start: (
    flow: FlowContext,
  ) => Effect.Effect<void, MessagingLifecycleError | EffectConfig.ConfigError>;
  readonly stop: Effect.Effect<void, MessagingLifecycleError>;
}

interface ConsumerRuntime {
  readonly scope: Scope.Closeable;
  readonly consumer: EffectConsumer;
}

export function makeConsumer<T>(options: ConsumerOptions<T>): Consumer<T> {
  let runtime: ConsumerRuntime | null = null;
  const isTooManyRequestsError = S.is(TooManyRequestsError);

  const runHandler = (
    message: T,
    properties: Record<string, string>,
    flow: FlowContext,
  ): Effect.Effect<void, TooManyRequestsError | MessagingHandlerError> =>
    options.handler(message, properties, flow).pipe(
      Effect.mapError((error) =>
        isTooManyRequestsError(error)
          ? error
          : messagingHandlerError(options.topic, options.subscription, error)
      ),
    );

  return {
    start: (flow) =>
      P.isNotNull(runtime)
        ? Effect.void
        : Effect.gen(function* () {
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
    stop: Effect.suspend(() => {
      const current = runtime;
      runtime = null;
      return current === null
        ? Effect.void
        : current.consumer.stop.pipe(
            Effect.ensuring(Scope.close(current.scope, Exit.void)),
          );
    }),
  };
}
