import { describe, expect, it } from "@effect/vitest";
import { Effect } from "effect";
import { makeOllamaEmbeddings } from "../embeddings/ollama.js";

describe("Ollama embeddings provider", () => {
  it.effect(
    "posts embedding requests to Ollama",
    Effect.fnUntraced(function* () {
      const calls: Array<{ readonly input: RequestInfo | URL; readonly init?: RequestInit }> = [];
      const fetchImpl = ((input: RequestInfo | URL, init?: RequestInit) => {
        calls.push(init === undefined ? { input } : { input, init });
        return Promise.resolve(
          new Response(JSON.stringify({ embeddings: [[1, 2, 3]] }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }) as typeof fetch;
      const embeddings = makeOllamaEmbeddings({
        id: "embeddings",
        model: "default-model",
        ollamaHost: "http://ollama.local",
        fetch: fetchImpl,
      });

      const vectors = yield* embeddings.embed(["alpha"], "override-model");

      expect(vectors).toEqual([[1, 2, 3]]);
      expect(calls).toHaveLength(1);
      expect(String(calls[0]?.input)).toBe("http://ollama.local/api/embed");
      expect(calls[0]?.init?.method).toBe("POST");
      expect(JSON.parse(String(calls[0]?.init?.body))).toEqual({
        model: "override-model",
        input: ["alpha"],
      });
    }),
  );

  it.effect(
    "does not call Ollama for empty requests",
    Effect.fnUntraced(function* () {
      const calls: Array<RequestInfo | URL> = [];
      const fetchImpl = ((input: RequestInfo | URL) => {
        calls.push(input);
        return Promise.resolve(new Response(JSON.stringify({ embeddings: [] })));
      }) as typeof fetch;
      const embeddings = makeOllamaEmbeddings({
        id: "embeddings",
        fetch: fetchImpl,
      });

      const vectors = yield* embeddings.embed([]);

      expect(vectors).toEqual([]);
      expect(calls).toEqual([]);
    }),
  );

  it.effect(
    "maps failed Ollama responses to EmbeddingsError",
    Effect.fnUntraced(function* () {
      const fetchImpl = (() =>
        Promise.resolve(
          new Response("not found", {
            status: 404,
          }),
        )) as typeof fetch;
      const embeddings = makeOllamaEmbeddings({
        id: "embeddings",
        ollamaHost: "http://ollama.local",
        fetch: fetchImpl,
      });

      const error = yield* embeddings.embed(["alpha"]).pipe(Effect.flip);

      expect(error._tag).toBe("EmbeddingsError");
      expect(error.operation).toBe("ollama.embed");
      expect(error.provider).toBe("ollama");
      expect(error.message).toContain("Ollama embeddings request failed (404): not found");
    }),
  );
});
