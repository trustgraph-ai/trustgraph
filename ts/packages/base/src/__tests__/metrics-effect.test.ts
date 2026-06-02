import { describe, expect, it } from "@effect/vitest";
import { Effect, Metric } from "effect";
import {
  formatPrometheusMetrics,
  makeConsumerMetrics,
  makeProducerMetrics,
} from "../metrics/index.js";

const withFreshMetrics = <A, E, R>(effect: Effect.Effect<A, E, R>) =>
  effect.pipe(Effect.provideService(Metric.MetricRegistry, new Map()));

describe("Effect metrics", () => {
  it.effect(
    "formats producer metrics through Effect Prometheus exporter",
    Effect.fnUntraced(function* () {
      const output = yield* withFreshMetrics(
        Effect.gen(function* () {
          const metrics = makeProducerMetrics("processor-a", "flow-a", "producer-a");
          yield* metrics.inc;
          yield* metrics.inc;
          return yield* formatPrometheusMetrics;
        }),
      );

      expect(output).toContain("# HELP tg_producer_items_total Producer items sent");
      expect(output).toContain("# TYPE tg_producer_items_total counter");
      expect(output).toContain('processor="processor-a"');
      expect(output).toContain('flow="flow-a"');
      expect(output).toContain('name="producer-a"');
      expect(output).toMatch(/tg_producer_items_total\{[^}]*\} 2/);
    }),
  );

  it.effect(
    "formats consumer metric timers and counters",
    Effect.fnUntraced(function* () {
      const output = yield* withFreshMetrics(
        Effect.gen(function* () {
          const metrics = makeConsumerMetrics("processor-a", "flow-a", "consumer-a");
          yield* metrics.recordTime(1.25);
          yield* metrics.process("success");
          yield* metrics.process("error");
          yield* metrics.rateLimit;
          return yield* formatPrometheusMetrics;
        }),
      );

      expect(output).toContain("# TYPE tg_consumer_request_duration_seconds histogram");
      expect(output).toMatch(/tg_consumer_request_duration_seconds_count\{[^}]*\} 1/);
      expect(output).toMatch(/tg_consumer_request_duration_seconds_sum\{[^}]*\} 1.25/);
      expect(output).toMatch(/tg_consumer_processing_total\{[^}]*status="success"[^}]*\} 1/);
      expect(output).toMatch(/tg_consumer_processing_total\{[^}]*status="error"[^}]*\} 1/);
      expect(output).toMatch(/tg_consumer_rate_limit_total\{[^}]*\} 1/);
    }),
  );
});
