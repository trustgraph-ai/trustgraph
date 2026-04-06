/**
 * Producer specification — declares a message producer for a flow.
 *
 * Python reference: trustgraph-base/trustgraph/base/producer_spec.py
 */

import type { Spec } from "./types.js";
import type { PubSubBackend } from "../backend/types.js";
import type { Flow, FlowDefinition } from "../processor/flow.js";
import { Producer } from "../messaging/producer.js";

export class ProducerSpec<T> implements Spec {
  constructor(public readonly name: string) {}

  async add(flow: Flow, pubsub: PubSubBackend, definition: FlowDefinition): Promise<void> {
    const topic = definition.topics?.[this.name] ?? this.name;
    const producer = new Producer<T>(pubsub, topic);
    await producer.start();
    flow.registerProducer(this.name, producer as Producer<unknown>);
  }
}
