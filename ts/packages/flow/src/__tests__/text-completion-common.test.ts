import { describe, expect, it } from "@effect/vitest";
import { Context, Effect, Stream } from "effect";
import { AiError, LanguageModel, Response } from "effect/unstable/ai";
import {
  llmStreamPart,
  makeLanguageModelProvider,
  providerRuntimeError,
  providerStatusError,
  streamTextCompletionChunks,
  textFromContent,
} from "../model/text-completion/common.js";

const languageModelContext = Context.empty();

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

  it.effect(
    "adapts Effect LanguageModel generateText responses to LlmProvider results",
    Effect.fnUntraced(function* () {
      const provider = makeLanguageModelProvider({
        provider: "FakeLanguageModel",
        defaultModel: "fake-model",
        defaultTemperature: 0.1,
        context: languageModelContext,
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

      const result = yield* provider.generateContent("system", "prompt", "override-model", 0.4);
      expect(result).toEqual({
        text: "model=override-model;temperature=0.4",
        inToken: 11,
        outToken: 7,
        model: "override-model",
      });
    }),
  );

  it.effect(
    "adapts Effect LanguageModel stream parts to TrustGraph chunks",
    Effect.fnUntraced(function* () {
      const provider = makeLanguageModelProvider({
        provider: "FakeLanguageModel",
        defaultModel: "fake-stream-model",
        defaultTemperature: 0,
        context: languageModelContext,
        makeLanguageModel: () =>
          LanguageModel.make({
            generateText: () =>
              Effect.succeed([
                { type: "text", text: "unused" },
                finishPart(1, 1),
              ]),
            streamText: () =>
              Stream.fromArray([
                Response.makePart("text-start", { id: "part-1" }),
                { type: "text-delta", id: "part-1", delta: "hel" },
                { type: "text-delta", id: "part-1", delta: "lo" },
                finishPart(13, 8),
              ]),
          }),
      });

      const chunks = yield* Stream.runCollect(
        provider.generateContentStream("system", "prompt"),
      );

      expect(Array.from(chunks)).toEqual([
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
    }),
  );

  it.effect(
    "maps Effect AI rate and quota failures to TrustGraph retry errors",
    Effect.fnUntraced(function* () {
      const reasons = [
        new AiError.RateLimitError({}),
        new AiError.QuotaExhaustedError({}),
      ];

      for (const reason of reasons) {
        const provider = makeLanguageModelProvider({
          provider: "FakeLanguageModel",
          defaultModel: "fake-model",
          defaultTemperature: 0,
          context: languageModelContext,
          makeLanguageModel: () =>
            LanguageModel.make({
              generateText: () => Effect.fail(aiError(reason)),
              streamText: () => Stream.fail(aiError(reason)),
            }),
        });

        const generateError = yield* provider.generateContent("system", "prompt").pipe(
          Effect.flip,
        );
        expect(generateError).toMatchObject({
          _tag: "TooManyRequestsError",
          message: "Rate limit exceeded",
        });

        const streamError = yield* Stream.runCollect(
          provider.generateContentStream("system", "prompt"),
        ).pipe(
          Effect.flip,
        );
        expect(streamError).toMatchObject({
          _tag: "TooManyRequestsError",
          message: "Rate limit exceeded",
        });
      }
    }),
  );
});
