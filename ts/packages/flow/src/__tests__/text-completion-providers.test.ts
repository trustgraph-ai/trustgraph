import { describe, expect, it } from "@effect/vitest";
import { Llm } from "@trustgraph/base";
import { ConfigProvider, Effect } from "effect";
import { makeAzureOpenAIProviderEffect } from "../model/text-completion/azure-openai.js";
import { makeClaudeProviderEffect } from "../model/text-completion/claude.js";
import { makeTextCompletionLayer } from "../model/text-completion/common.js";
import { makeMistralProviderEffect } from "../model/text-completion/mistral.js";
import { makeOllamaProviderEffect } from "../model/text-completion/ollama.js";
import { makeOpenAICompatibleProviderEffect } from "../model/text-completion/openai-compatible.js";
import { makeOpenAIProviderEffect } from "../model/text-completion/openai.js";

const emptyConfig = ConfigProvider.layer(
  ConfigProvider.fromEnv({ env: {} }),
);

describe("text completion provider construction", () => {
  it.effect(
    "constructs providers from explicit config through Effect",
    Effect.fnUntraced(function* () {
      const providers = yield* Effect.all([
        makeOpenAIProviderEffect({ id: "openai", apiKey: "test-key" }),
        makeOpenAICompatibleProviderEffect({
          id: "openai-compatible",
          baseUrl: "http://localhost:1234/v1",
        }),
        makeAzureOpenAIProviderEffect({
          id: "azure-openai",
          apiKey: "test-key",
          endpoint: "https://example.openai.azure.com",
        }),
        makeClaudeProviderEffect({ id: "claude", apiKey: "test-key" }),
        makeMistralProviderEffect({ id: "mistral", apiKey: "test-key" }),
        makeOllamaProviderEffect({
          id: "ollama",
          ollamaUrl: "http://localhost:11434",
        }),
      ]).pipe(
        Effect.provide(emptyConfig),
      );

      expect(providers.map((provider) => provider.supportsStreaming())).toEqual([
        true,
        true,
        true,
        true,
        true,
        true,
      ]);
    }),
  );

  it.effect(
    "provides Llm through the shared Effect layer helper",
    Effect.fnUntraced(function* () {
      const llm = yield* Effect.gen(function* () {
        return yield* Llm;
      }).pipe(
        Effect.provide(
          makeTextCompletionLayer(makeOllamaProviderEffect({
            id: "ollama",
            ollamaUrl: "http://localhost:11434",
          })),
        ),
        Effect.provide(emptyConfig),
      );

      expect(llm.supportsStreaming()).toBe(true);
    }),
  );

  it.effect(
    "fails missing required config as a tagged config error",
    Effect.fnUntraced(function* () {
      const error = yield* makeOpenAIProviderEffect({ id: "openai" }).pipe(
        Effect.flip,
        Effect.provide(emptyConfig),
      );

      expect(error).toMatchObject({
        _tag: "TextCompletionConfigError",
        provider: "OpenAI",
        key: "OPENAI_TOKEN",
      });
    }),
  );
});
