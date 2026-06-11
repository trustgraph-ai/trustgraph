/**
 * Effect-native metrics and Prometheus formatting helpers.
 *
 * Python reference: trustgraph-base/trustgraph/base/metrics.py
 */

import type { Effect, } from "effect";
import { Metric } from "effect";
import { PrometheusMetrics } from "effect/unstable/observability";

export const prometheusContentType = "text/plain; version=0.0.4; charset=utf-8";

const consumerRequestDuration = Metric.histogram("tg_consumer_request_duration_seconds", {
  description: "Consumer request processing time",
  boundaries: Metric.exponentialBoundaries({ start: 0.005, factor: 2, count: 12 }),
});

const consumerProcessing = Metric.counter("tg_consumer_processing_total", {
  description: "Consumer processing outcomes",
  incremental: true,
});

const consumerRateLimit = Metric.counter("tg_consumer_rate_limit_total", {
  description: "Consumer rate limit events",
  incremental: true,
});

const producerItems = Metric.counter("tg_producer_items_total", {
  description: "Producer items sent",
  incremental: true,
});

export interface ConsumerMetrics {
  readonly recordTime: (seconds: number) => Effect.Effect<void>;
  readonly process: (status: "success" | "error") => Effect.Effect<void>;
  readonly rateLimit: Effect.Effect<void>;
}

export function makeConsumerMetrics(
  processor: string,
  flow: string,
  name: string,
): ConsumerMetrics {
  const labels = { processor, flow, name };
  const requestHistogram = Metric.withAttributes(consumerRequestDuration, labels);
  const rateLimitCounter = Metric.withAttributes(consumerRateLimit, labels);

  return {
    recordTime: (seconds) => Metric.update(requestHistogram, seconds),
    process: (status) =>
      Metric.update(
        Metric.withAttributes(consumerProcessing, { ...labels, status }),
        1,
      ),
    rateLimit: Metric.update(rateLimitCounter, 1),
  };
}

export interface ProducerMetrics {
  readonly inc: Effect.Effect<void>;
}

export function makeProducerMetrics(
  processor: string,
  flow: string,
  name: string,
): ProducerMetrics {
  const labels = { processor, flow, name };
  const counter = Metric.withAttributes(producerItems, labels);

  return {
    inc: Metric.update(counter, 1),
  };
}

export const formatPrometheusMetrics = PrometheusMetrics.format();
