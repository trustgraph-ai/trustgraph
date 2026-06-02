import { describe, expect, it } from "@effect/vitest";
import type { LlmChunk } from "@trustgraph/base";
import { Effect, Stream } from "effect";
import {
  llmStreamPart,
  providerRuntimeError,
  providerStatusError,
  streamTextCompletionChunks,
  textFromContent,
  toAsyncGenerator,
} from "../model/text-completion/common.js";

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
});
