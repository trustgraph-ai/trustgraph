/**
 * Prometheus metrics wrappers.
 *
 * Python reference: trustgraph-base/trustgraph/base/metrics.py
 */

import { Counter, Histogram, Registry, collectDefaultMetrics } from "prom-client";

export const registry = new Registry();
collectDefaultMetrics({ register: registry });

export interface ConsumerMetrics {
  readonly recordTime: (seconds: number) => void;
  readonly process: (status: "success" | "error") => void;
  readonly rateLimit: () => void;
}

export function makeConsumerMetrics(
  processor: string,
  flow: string,
  name: string,
): ConsumerMetrics {
  const labels = { processor, flow, name };
  const requestHistogram = new Histogram({
      name: "tg_consumer_request_duration_seconds",
      help: "Consumer request processing time",
      labelNames: ["processor", "flow", "name"],
      registers: [registry],
  });

  const processingCounter = new Counter({
      name: "tg_consumer_processing_total",
      help: "Consumer processing outcomes",
      labelNames: ["processor", "flow", "name", "status"],
      registers: [registry],
  });

  const rateLimitCounter = new Counter({
      name: "tg_consumer_rate_limit_total",
      help: "Consumer rate limit events",
      labelNames: ["processor", "flow", "name"],
      registers: [registry],
  });

  return {
    recordTime: (seconds) => requestHistogram.observe(labels, seconds),
    process: (status) => processingCounter.inc({ ...labels, status }),
    rateLimit: () => rateLimitCounter.inc(labels),
  };
}

export interface ProducerMetrics {
  readonly inc: () => void;
}

export function makeProducerMetrics(
  processor: string,
  flow: string,
  name: string,
): ProducerMetrics {
  const labels = { processor, flow, name };
  const counter = new Counter({
      name: "tg_producer_items_total",
      help: "Producer items sent",
      labelNames: ["processor", "flow", "name"],
      registers: [registry],
  });

  return {
    inc: () => counter.inc(labels),
  };
}
