/**
 * Producer specification — declares a message producer for a flow.
 *
 * Python reference: trustgraph-base/trustgraph/base/producer_spec.py
 */

import { Effect } from "effect";
import type { Spec } from "./types.js";
import type { Flow, FlowDefinition } from "../processor/flow.js";
import {
  flowResourceNotFoundError,
  type FlowResourceNotFoundError,
} from "../errors.js";
import {
  type EffectProducer,
  ProducerFactory,
} from "../messaging/runtime.js";

declare const ProducerSpecType: unique symbol;

export interface ProducerSpec<T> extends Spec {
  readonly [ProducerSpecType]?: (_: T) => T;
  readonly producerEffect: <Requirements = never>(
    flow: Flow<Requirements>,
  ) => Effect.Effect<EffectProducer<T>, FlowResourceNotFoundError>;
}

export function makeProducerSpec<T>(name: string): ProducerSpec<T> {
  const producers = new WeakMap<object, EffectProducer<T>>();

  const registerProducer = <Requirements>(
    flow: Flow<Requirements>,
    producer: EffectProducer<T>,
  ) =>
    Effect.sync(() => {
      producers.set(flow, producer);
    });

  const unregisterProducer = <Requirements>(
    flow: Flow<Requirements>,
    producer: EffectProducer<T>,
  ) =>
    Effect.sync(() => {
      if (producers.get(flow) === producer) {
        producers.delete(flow);
      }
    });

  const producerEffect = <Requirements>(
    flow: Flow<Requirements>,
  ): Effect.Effect<EffectProducer<T>, FlowResourceNotFoundError> => {
    const producer = producers.get(flow);
    return producer === undefined
      ? Effect.fail(flowResourceNotFoundError(flow.name, "producer", name))
      : Effect.succeed(producer);
  };

  const addEffect = Effect.fn("ProducerSpec.addEffect")(function* (
    flow: Flow,
    definition: FlowDefinition,
  ) {
      const topic = definition.topics?.[name] ?? name;
      const factory = yield* ProducerFactory;
      const producer = yield* factory.make<T>({ topic });
      flow.registerProducer(name, producer);
      yield* registerProducer(flow, producer);
      yield* Effect.addFinalizer(() => unregisterProducer(flow, producer));
  });

  return {
    name,
    producerEffect,
    addEffect,
    add: (flow, pubsub, definition, context) =>
      flow.runInCompatibilityScope(addEffect(flow, definition), pubsub, context),
  };
}
