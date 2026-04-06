/**
 * Consumer specification — declares a message consumer for a flow.
 *
 * Python reference: trustgraph-base/trustgraph/base/consumer_spec.py
 */

import type { Spec } from "./types.js";
import type { PubSubBackend } from "../backend/types.js";
import type { Flow, FlowDefinition } from "../processor/flow.js";
import { Consumer, type MessageHandler } from "../messaging/consumer.js";

export class ConsumerSpec<T> implements Spec {
  constructor(
    public readonly name: string,
    private readonly handler: MessageHandler<T>,
    private readonly concurrency = 1,
  ) {}

  async add(flow: Flow, pubsub: PubSubBackend, definition: FlowDefinition): Promise<void> {
    const topic = definition.topics?.[this.name] ?? this.name;

    const consumer = new Consumer<T>({
      pubsub,
      topic,
      subscription: `${flow.processorId}-${flow.name}-${this.name}`,
      handler: this.handler,
      concurrency: this.concurrency,
    });

    flow.registerConsumer(this.name, consumer as Consumer<unknown>);
  }
}
