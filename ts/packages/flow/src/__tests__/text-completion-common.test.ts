import { describe, expect, it } from "@effect/vitest";
import type { LlmChunk } from "@trustgraph/base";
import { providerRuntimeError, toAsyncGenerator } from "../model/text-completion/common.js";

const emptyChunkIterator = (): AsyncIterable<LlmChunk> => ({
  [Symbol.asyncIterator]: () => ({
    next: () => Promise.resolve({ done: true, value: undefined }),
  }),
});

describe("text completion common helpers", () => {
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
});
