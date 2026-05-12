/**
 * High-level async producer with queue buffering and retry.
 *
 * Python reference: trustgraph-base/trustgraph/base/producer.py
 */

import type { PubSubBackend, BackendProducer } from "../backend/types.js";
import type { ProducerMetrics } from "../metrics/prometheus.js";
import { Effect } from "effect";
import { makeEffectProducerHandle, type EffectProducer } from "./runtime.js";

export class Producer<T> {
  private backend: BackendProducer<T> | null = null;
  private effectProducer: EffectProducer<T> | null = null;
  private readonly pubsub: PubSubBackend;
  private readonly topic: string;
  private readonly metrics: ProducerMetrics | undefined;

  constructor(pubsub: PubSubBackend, topic: string, metrics?: ProducerMetrics) {
    this.pubsub = pubsub;
    this.topic = topic;
    this.metrics = metrics;
  }

  async start(): Promise<void> {
    this.backend = await this.pubsub.createProducer<T>({ topic: this.topic });
    this.effectProducer = makeEffectProducerHandle(this.backend, {
      topic: this.topic,
      ...(this.metrics === undefined ? {} : { metrics: this.metrics }),
    });
  }

  async send(id: string, message: T): Promise<void> {
    if (this.effectProducer === null) throw new Error("Producer not started");

    await Effect.runPromise(this.effectProducer.send(id, message));
  }

  async stop(): Promise<void> {
    if (this.effectProducer !== null) {
      await Effect.runPromise(
        this.effectProducer.flush.pipe(
          Effect.flatMap(() => this.effectProducer === null ? Effect.void : this.effectProducer.close),
        ),
      );
      this.effectProducer = null;
      this.backend = null;
    }
  }
}
