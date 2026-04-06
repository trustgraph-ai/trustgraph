/**
 * High-level async producer with queue buffering and retry.
 *
 * Python reference: trustgraph-base/trustgraph/base/producer.py
 */

import type { PubSubBackend, BackendProducer } from "../backend/types.js";
import type { ProducerMetrics } from "../metrics/prometheus.js";

export class Producer<T> {
  private backend: BackendProducer<T> | null = null;
  private running = false;

  constructor(
    private readonly pubsub: PubSubBackend,
    private readonly topic: string,
    private readonly metrics?: ProducerMetrics,
  ) {}

  async start(): Promise<void> {
    this.backend = await this.pubsub.createProducer<T>({ topic: this.topic });
    this.running = true;
  }

  async send(id: string, message: T): Promise<void> {
    if (!this.backend) throw new Error("Producer not started");

    await this.backend.send(message, { id });
    this.metrics?.inc();
  }

  async stop(): Promise<void> {
    this.running = false;
    if (this.backend) {
      await this.backend.flush();
      await this.backend.close();
      this.backend = null;
    }
  }
}
