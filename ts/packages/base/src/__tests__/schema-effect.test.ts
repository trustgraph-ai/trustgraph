import { describe, expect, it } from "@effect/vitest";
import { ConfigProvider, Duration, Effect } from "effect";
import * as S from "effect/Schema";
import {
  ConfigRequest,
  GraphRagResponse,
  Term,
  TextCompletionRequest,
  Triple,
  loadMessagingRuntimeConfig,
  loadProcessorRuntimeConfig,
} from "../index.js";

describe("Effect schemas", () => {
  it.effect(
    "decode existing text-completion wire payloads",
    Effect.fnUntraced(function* () {
      const request = yield* S.decodeUnknownEffect(TextCompletionRequest)({
        system: "system",
        prompt: "hello",
        streaming: true,
      });

      expect(request.prompt).toBe("hello");
      expect(request.streaming).toBe(true);
    }),
  );

  it.effect(
    "decode recursive RDF terms",
    Effect.fnUntraced(function* () {
      const term = yield* S.decodeUnknownEffect(Term)({
        type: "TRIPLE",
        triple: {
          s: { type: "IRI", iri: "urn:s" },
          p: { type: "IRI", iri: "urn:p" },
          o: { type: "LITERAL", value: "object" },
        },
      });

      expect(term.type).toBe("TRIPLE");
    }),
  );

  it.effect(
    "decode triples with named graph strings",
    Effect.fnUntraced(function* () {
      const triple = yield* S.decodeUnknownEffect(Triple)({
        s: { type: "IRI", iri: "urn:s" },
        p: { type: "IRI", iri: "urn:p" },
        o: { type: "LITERAL", value: "object" },
        g: "urn:graph",
      });

      expect(triple.g).toBe("urn:graph");
    }),
  );

  it.effect(
    "preserve gateway response extension fields",
    Effect.fnUntraced(function* () {
      const response = yield* S.decodeUnknownEffect(GraphRagResponse)({
        response: "ok",
        message_type: "explain",
        explain_id: "e1",
        providerTrace: { kept: true },
      });

      expect(response.providerTrace).toEqual({ kept: true });
    }),
  );

  it.effect(
    "decode config requests",
    Effect.fnUntraced(function* () {
      const request = yield* S.decodeUnknownEffect(ConfigRequest)({
        operation: "put",
        keys: ["flows"],
        values: { default: { topics: {} } },
      });

      expect(request.operation).toBe("put");
    }),
  );
});

describe("Effect runtime config", () => {
  it.effect(
    "loads processor settings from existing env names",
    Effect.fnUntraced(function* () {
      const provider = ConfigProvider.fromEnv({
        env: {
          NATS_URL: "nats://example:4222",
          METRICS_PORT: "9000",
        },
      });

      const config = yield* Effect.provide(
        loadProcessorRuntimeConfig("svc", { manageProcessSignals: false }),
        ConfigProvider.layer(provider),
      );

      expect(config).toEqual({
        id: "svc",
        pubsubUrl: "nats://example:4222",
        metricsPort: 9000,
        manageProcessSignals: false,
      });
    }),
  );

  it.effect(
    "loads messaging durations from legacy millisecond env values",
    Effect.fnUntraced(function* () {
      const provider = ConfigProvider.fromEnv({
        env: {
          TG_CONSUMER_RECEIVE_TIMEOUT_MS: "5",
          TG_CONSUMER_ERROR_BACKOFF_MS: "10",
          TG_RATE_LIMIT_RETRY_MS: "15",
          TG_RATE_LIMIT_TIMEOUT_MS: "20",
          TG_REQUEST_TIMEOUT_MS: "25",
        },
      });

      const config = yield* Effect.provide(
        loadMessagingRuntimeConfig(),
        ConfigProvider.layer(provider),
      );

      expect(Duration.toMillis(config.consumerReceiveTimeout)).toBe(5);
      expect(Duration.toMillis(config.consumerErrorBackoff)).toBe(10);
      expect(Duration.toMillis(config.rateLimitRetry)).toBe(15);
      expect(Duration.toMillis(config.rateLimitTimeout)).toBe(20);
      expect(Duration.toMillis(config.requestTimeout)).toBe(25);
    }),
  );

  it.effect(
    "loads messaging durations from Effect duration env values",
    Effect.fnUntraced(function* () {
      const provider = ConfigProvider.fromEnv({
        env: {
          TG_CONSUMER_RECEIVE_TIMEOUT_MS: "2 seconds",
          TG_CONSUMER_ERROR_BACKOFF_MS: "3 seconds",
          TG_RATE_LIMIT_RETRY_MS: "4 seconds",
          TG_RATE_LIMIT_TIMEOUT_MS: "5 seconds",
          TG_REQUEST_TIMEOUT_MS: "6 seconds",
        },
      });

      const config = yield* Effect.provide(
        loadMessagingRuntimeConfig(),
        ConfigProvider.layer(provider),
      );

      expect(Duration.toMillis(config.consumerReceiveTimeout)).toBe(2_000);
      expect(Duration.toMillis(config.consumerErrorBackoff)).toBe(3_000);
      expect(Duration.toMillis(config.rateLimitRetry)).toBe(4_000);
      expect(Duration.toMillis(config.rateLimitTimeout)).toBe(5_000);
      expect(Duration.toMillis(config.requestTimeout)).toBe(6_000);
    }),
  );
});
