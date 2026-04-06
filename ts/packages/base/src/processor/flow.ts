/**
 * Runtime flow instance — created by FlowProcessor for each configured flow.
 *
 * Python reference: trustgraph-base/trustgraph/base/flow.py
 */

import type { PubSubBackend } from "../backend/types.js";
import type { Spec } from "../spec/types.js";
import type { Producer } from "../messaging/producer.js";
import type { Consumer } from "../messaging/consumer.js";
import type { RequestResponse } from "../messaging/request-response.js";

export interface FlowDefinition {
  /** Topic overrides keyed by spec name */
  topics?: Record<string, string>;
  /** Parameter values keyed by spec name */
  parameters?: Record<string, unknown>;
}

export class Flow {
  private producers = new Map<string, Producer<unknown>>();
  private consumers = new Map<string, Consumer<unknown>>();
  private requestors = new Map<string, RequestResponse<unknown, unknown>>();
  private parameters = new Map<string, unknown>();

  constructor(
    public readonly name: string,
    public readonly processorId: string,
    private readonly pubsub: PubSubBackend,
    private readonly definition: FlowDefinition,
    private readonly specifications: Spec[],
  ) {}

  async start(): Promise<void> {
    for (const spec of this.specifications) {
      await spec.add(this, this.pubsub, this.definition);
    }

    // Start all consumers, passing this Flow instance via FlowContext
    for (const consumer of this.consumers.values()) {
      consumer.start({ id: this.processorId, name: this.name, flow: this }).catch((err) => {
        console.error(`[Flow:${this.name}] Consumer error:`, err);
      });
    }
  }

  async stop(): Promise<void> {
    for (const consumer of this.consumers.values()) {
      await consumer.stop();
    }
    for (const producer of this.producers.values()) {
      await producer.stop();
    }
    for (const rr of this.requestors.values()) {
      await rr.stop();
    }
  }

  registerProducer(name: string, producer: Producer<unknown>): void {
    this.producers.set(name, producer);
  }

  registerConsumer(name: string, consumer: Consumer<unknown>): void {
    this.consumers.set(name, consumer);
  }

  registerRequestor(name: string, rr: RequestResponse<unknown, unknown>): void {
    this.requestors.set(name, rr);
  }

  setParameter(name: string, value: unknown): void {
    this.parameters.set(name, value);
  }

  producer<T>(name: string): Producer<T> {
    const p = this.producers.get(name);
    if (!p) throw new Error(`Producer "${name}" not found in flow "${this.name}"`);
    return p as Producer<T>;
  }

  consumer<T>(name: string): Consumer<T> {
    const c = this.consumers.get(name);
    if (!c) throw new Error(`Consumer "${name}" not found in flow "${this.name}"`);
    return c as Consumer<T>;
  }

  requestor<TReq, TRes>(name: string): RequestResponse<TReq, TRes> {
    const rr = this.requestors.get(name);
    if (!rr) throw new Error(`Requestor "${name}" not found in flow "${this.name}"`);
    return rr as RequestResponse<TReq, TRes>;
  }

  parameter<T>(name: string): T {
    const v = this.parameters.get(name);
    if (v === undefined) throw new Error(`Parameter "${name}" not found in flow "${this.name}"`);
    return v as T;
  }
}
