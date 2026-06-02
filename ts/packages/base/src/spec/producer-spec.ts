/**
 * Producer specification — declares a message producer for a flow.
 *
 * Python reference: trustgraph-base/trustgraph/base/producer_spec.py
 */

import { Effect } from "effect";
import type { Spec } from "./types.js";
import type { Flow, FlowDefinition } from "../processor/flow.js";
import {
  ProducerFactory,
  type EffectProducer,
} from "../messaging/runtime.js";

declare const ProducerSpecType: unique symbol;

export interface ProducerSpec<T> extends Spec {
  readonly [ProducerSpecType]?: (_: T) => T;
}

export function makeProducerSpec<T>(name: string): ProducerSpec<T> {
  const addEffect = Effect.fn("ProducerSpec.addEffect")(function* (
    flow: Flow,
    definition: FlowDefinition,
  ) {
      const topic = definition.topics?.[name] ?? name;
      const factory = yield* ProducerFactory;
      const producer = yield* factory.make<T>({ topic });
      flow.registerProducer(name, producer as EffectProducer<unknown>);
  });

  return {
    name,
    addEffect,
    add: async (flow, pubsub, definition) => {
      await flow.runInCompatibilityScope(addEffect(flow, definition), pubsub);
    },
  };
}
