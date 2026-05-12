/**
 * Producer specification — declares a message producer for a flow.
 *
 * Python reference: trustgraph-base/trustgraph/base/producer_spec.py
 */

import { Effect } from "effect";
import type { Spec } from "./types.js";
import type { PubSubBackend } from "../backend/types.js";
import type { Flow, FlowDefinition } from "../processor/flow.js";
import {
  ProducerFactory,
  type EffectProducer,
} from "../messaging/runtime.js";

export class ProducerSpec<T> implements Spec {
  public readonly name: string;

  constructor(name: string) {
    this.name = name;
  }

  addEffect(flow: Flow, definition: FlowDefinition) {
    const spec = this;
    return Effect.gen(function* () {
      const topic = definition.topics?.[spec.name] ?? spec.name;
      const factory = yield* ProducerFactory;
      const producer = yield* factory.make<T>({ topic });
      flow.registerProducer(spec.name, producer as EffectProducer<unknown>);
    });
  }

  async add(flow: Flow, pubsub: PubSubBackend, definition: FlowDefinition): Promise<void> {
    await flow.runInCompatibilityScope(this.addEffect(flow, definition), pubsub);
  }
}
