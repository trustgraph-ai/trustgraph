import { describe, expect, it } from "@effect/vitest";
import { ConfigProvider, Effect } from "effect";
import * as S from "effect/Schema";
import {
  ConfigRequest,
  GraphRagResponse,
  Term,
  TextCompletionRequest,
  Triple,
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
});
