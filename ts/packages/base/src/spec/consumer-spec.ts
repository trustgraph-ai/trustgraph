/**
 * Consumer specification — declares a message consumer for a flow.
 *
 * Python reference: trustgraph-base/trustgraph/base/consumer_spec.py
 */

import { Effect } from "effect";
import type { Spec } from "./types.js";
import type { SpecRuntimeRequirements } from "./types.js";
import type { Flow, FlowDefinition } from "../processor/flow.js";
import {
  ConsumerFactory,
  type EffectMessageHandler,
} from "../messaging/runtime.js";
import {
  type PubSubError,
} from "../errors.js";

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
  };
}
