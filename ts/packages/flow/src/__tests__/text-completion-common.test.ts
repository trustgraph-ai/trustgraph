import { describe, expect, it } from "@effect/vitest";
import type { LlmChunk } from "@trustgraph/base";
import { Effect, Layer, ManagedRuntime, Stream } from "effect";
import { AiError, LanguageModel } from "effect/unstable/ai";
import {
  llmStreamPart,
  makeLanguageModelProvider,
  providerRuntimeError,
  providerStatusError,
  streamTextCompletionChunks,
  textFromContent,
  toAsyncGenerator,
} from "../model/text-completion/common.js";

const languageModelRuntime = ManagedRuntime.make(Layer.empty);

const usage = (inputTokens: number, outputTokens: number) => ({
  inputTokens: {
    uncached: undefined,
    total: inputTokens,
    cacheRead: undefined,
    cacheWrite: undefined,
  },
  outputTokens: {
    total: outputTokens,
    text: undefined,
    reasoning: undefined,
  },
});

const finishPart = (inputTokens: number, outputTokens: number) => ({
  type: "finish",
  reason: "stop",
  usage: usage(inputTokens, outputTokens),
  response: undefined,
});

const aiError = (reason: AiError.AiErrorReason) =>
  new AiError.AiError({
    module: "FakeLanguageModel",
    method: "generateText",
    reason,
  });

const emptyChunkIterator = (): AsyncIterable<LlmChunk> => ({
  [Symbol.asyncIterator]: () => ({
    next: () => Promise.resolve({ done: true, value: undefined }),
  }),
});

describe("text completion common helpers", () => {
  it("maps provider rate-limit status fields to tagged retry errors", () => {
    expect(providerStatusError("test-provider", { status: 429 })).toMatchObject({
      _tag: "TooManyRequestsError",
      message: "Rate limit exceeded",
    });

    expect(providerStatusError("test-provider", { statusCode: 429 })).toMatchObject({
      _tag: "TooManyRequestsError",
      message: "Rate limit exceeded",
    });
  });

  it("maps fallback generator throw failures into tagged provider errors", async () => {
    const generator = toAsyncGenerator(
      emptyChunkIterator(),
      (error) => providerRuntimeError("test-provider", error),
    );

    await expect(generator.throw("provider failed")).rejects.toMatchObject({
      _tag: "TextCompletionProviderError",
      provider: "test-provider",
      message: "provider failed",
    });
  });

  it.effect(
    "builds streaming chunks from async iterables with final token totals",
    Effect.fnUntraced(function* () {
      const chunks = yield* Stream.runCollect(
        streamTextCompletionChunks(
          Stream.toAsyncIterable(Stream.fromArray([
            { text: "", inToken: 3 },
            { text: "hello" },
            { outToken: 5 },
          ])),
          {
            model: "unit-model",
            mapError: (error) => providerRuntimeError("test-provider", error),
            extract: (chunk) => llmStreamPart(chunk),
          },
        ),
      );

      expect(Array.from(chunks)).toEqual([
        {
          text: "hello",
          inToken: null,
          outToken: null,
          model: "unit-model",
          isFinal: false,
        },
        {
          text: "",
          inToken: 3,
          outToken: 5,
          model: "unit-model",
          isFinal: true,
        },
      ]);
    }),
  );

  it("narrows provider content payloads without type assertions", () => {
    expect(textFromContent("direct")).toBe("direct");
    expect(textFromContent([{ text: "a" }, { text: "b" }, { wrong: "skip" }])).toBe("ab");
    expect(textFromContent([{ text: 1 }])).toBe("");
  });

  it("adapts Effect LanguageModel generateText responses to LlmProvider results", async () => {
    const provider = makeLanguageModelProvider({
      provider: "FakeLanguageModel",
      defaultModel: "fake-model",
      defaultTemperature: 0.1,
      runtime: languageModelRuntime,
      makeLanguageModel: ({ model, temperature }) =>
        LanguageModel.make({
          generateText: () =>
            Effect.succeed([
              { type: "text", text: `model=${model};temperature=${temperature}` },
              finishPart(11, 7),
            ]),
          streamText: () => Stream.empty,
        }),
    });

    await expect(provider.generateContent("system", "prompt", "override-model", 0.4)).resolves.toEqual({
      text: "model=override-model;temperature=0.4",
      inToken: 11,
      outToken: 7,
      model: "override-model",
    });
  });

  it("adapts Effect LanguageModel stream parts to TrustGraph chunks", async () => {
    const provider = makeLanguageModelProvider({
      provider: "FakeLanguageModel",
      defaultModel: "fake-stream-model",
      defaultTemperature: 0,
      runtime: languageModelRuntime,
      makeLanguageModel: () =>
        LanguageModel.make({
          generateText: () =>
            Effect.succeed([
              { type: "text", text: "unused" },
              finishPart(1, 1),
            ]),
          streamText: () =>
            Stream.fromArray([
              { type: "text-delta", id: "part-1", delta: "hel" },
              { type: "text-delta", id: "part-1", delta: "lo" },
              finishPart(13, 8),
            ]),
        }),
    });

    const chunks: Array<LlmChunk> = [];
    for await (const chunk of provider.generateContentStream("system", "prompt")) {
      chunks.push(chunk);
    }

    expect(chunks).toEqual([
      {
        text: "hel",
        inToken: null,
        outToken: null,
        model: "fake-stream-model",
        isFinal: false,
      },
      {
        text: "lo",
        inToken: null,
        outToken: null,
        model: "fake-stream-model",
        isFinal: false,
      },
      {
        text: "",
        inToken: 13,
        outToken: 8,
        model: "fake-stream-model",
        isFinal: true,
      },
    ]);
  });

  it("maps Effect AI rate and quota failures to TrustGraph retry errors", async () => {
    const reasons = [
      new AiError.RateLimitError({}),
      new AiError.QuotaExhaustedError({}),
    ];

    for (const reason of reasons) {
      const provider = makeLanguageModelProvider({
        provider: "FakeLanguageModel",
        defaultModel: "fake-model",
        defaultTemperature: 0,
        runtime: languageModelRuntime,
        makeLanguageModel: () =>
          LanguageModel.make({
            generateText: () => Effect.fail(aiError(reason)),
            streamText: () => Stream.fail(aiError(reason)),
          }),
      });

      await expect(provider.generateContent("system", "prompt")).rejects.toMatchObject({
        _tag: "TooManyRequestsError",
        message: "Rate limit exceeded",
      });
    }
  });
});
