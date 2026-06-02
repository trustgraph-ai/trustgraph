/**
 * Consumer specification — declares a message consumer for a flow.
 *
 * Python reference: trustgraph-base/trustgraph/base/consumer_spec.py
 */

import { Effect } from "effect";
import * as S from "effect/Schema";
import type { Spec } from "./types.js";
import type { SpecRuntimeRequirements } from "./types.js";
import type { Flow, FlowDefinition } from "../processor/flow.js";
import { type MessageHandler } from "../messaging/consumer.js";
import {
  ConsumerFactory,
  type EffectMessageHandler,
} from "../messaging/runtime.js";
import {
  messagingHandlerError,
  TooManyRequestsError,
  type MessagingHandlerError,
  type PubSubError,
} from "../errors.js";

const isTooManyRequestsError = S.is(TooManyRequestsError);

declare const ConsumerSpecType: unique symbol;

export interface ConsumerSpec<T, E = never, R = never> extends Spec<R> {
  readonly [ConsumerSpecType]?: {
    readonly message: T;
    readonly error: E;
  };
  readonly addEffect: (
    flow: Flow<R>,
    definition: FlowDefinition,
  ) => Effect.Effect<void, PubSubError, SpecRuntimeRequirements | R>;
}

export function makeConsumerSpec<T, E = never, R = never>(
  name: string,
  handler: EffectMessageHandler<T, E, R>,
  concurrency = 1,
): ConsumerSpec<T, E, R> {
  const addEffect = Effect.fn("ConsumerSpec.addEffect")(function* (
    flow: Flow<R>,
    definition: FlowDefinition,
  ) {
      const topic = definition.topics?.[name] ?? name;
      const factory = yield* ConsumerFactory;
      const consumer = yield* factory.run<T, E, R>(
        {
          topic,
          subscription: `${flow.processorId}-${flow.name}-${name}`,
          handler,
          concurrency,
        },
        { id: flow.processorId, name: flow.name, flow },
      );
      flow.registerConsumer(name, consumer);
  });

  return {
    name,
    addEffect,
    add: async (flow, pubsub, definition) => {
      const effect = addEffect(flow as Flow<R>, definition) as Effect.Effect<
        void,
        PubSubError,
        SpecRuntimeRequirements
      >;
      await flow.runInCompatibilityScope(effect, pubsub);
    },
  };
}

export function makeConsumerSpecFromPromise<T>(
  name: string,
  handler: MessageHandler<T>,
  concurrency = 1,
): ConsumerSpec<T, TooManyRequestsError | MessagingHandlerError> {
  return makeConsumerSpec<T, TooManyRequestsError | MessagingHandlerError>(
    name,
    (message, properties, flow) =>
      Effect.tryPromise({
        try: () => handler(message, properties, flow),
        catch: (error) =>
          isTooManyRequestsError(error)
            ? error
            : messagingHandlerError(name, `${flow.id}-${flow.name}-${name}`, error),
      }),
    concurrency,
  );
}
