/**
 * Prometheus metrics wrappers.
 *
 * Python reference: trustgraph-base/trustgraph/base/metrics.py
 */

import { Counter, Histogram, Registry, collectDefaultMetrics } from "prom-client";

export const registry = new Registry();
collectDefaultMetrics({ register: registry });

export class ConsumerMetrics {
  private requestHistogram: Histogram;
  private processingCounter: Counter;
  private rateLimitCounter: Counter;

  constructor(processor: string, flow: string, name: string) {
    this.requestHistogram = new Histogram({
      name: "tg_consumer_request_duration_seconds",
      help: "Consumer request processing time",
      labelNames: ["processor", "flow", "name"],
      registers: [registry],
    });

    this.processingCounter = new Counter({
      name: "tg_consumer_processing_total",
      help: "Consumer processing outcomes",
      labelNames: ["processor", "flow", "name", "status"],
      registers: [registry],
    });

    this.rateLimitCounter = new Counter({
      name: "tg_consumer_rate_limit_total",
      help: "Consumer rate limit events",
      labelNames: ["processor", "flow", "name"],
      registers: [registry],
    });
  }

  recordTime(seconds: number): void {
    this.requestHistogram.observe(seconds);
  }

  process(status: "success" | "error"): void {
    this.processingCounter.inc({ status });
  }

  rateLimit(): void {
    this.rateLimitCounter.inc();
  }
}

export class ProducerMetrics {
  private counter: Counter;

  constructor(processor: string, flow: string, name: string) {
    this.counter = new Counter({
      name: "tg_producer_items_total",
      help: "Producer items sent",
      labelNames: ["processor", "flow", "name"],
      registers: [registry],
    });
  }

  inc(): void {
    this.counter.inc();
  }
}
