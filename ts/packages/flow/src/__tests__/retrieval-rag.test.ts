import { describe, expect, it } from "@effect/vitest";
import { Effect } from "effect";
import type {
  DocumentEmbeddingsRequest,
  DocumentEmbeddingsResponse,
  EmbeddingsRequest,
  EmbeddingsResponse,
  EffectRequestResponse,
  GraphEmbeddingsRequest,
  GraphEmbeddingsResponse,
  PromptRequest,
  PromptResponse,
  TextCompletionRequest,
  TextCompletionResponse,
  TriplesQueryRequest,
  TriplesQueryResponse,
} from "@trustgraph/base";
import type { DocumentRagClients } from "../retrieval/document-rag.js";
import { makeDocumentRagEngine, } from "../retrieval/document-rag.js";
import type { GraphRagClients } from "../retrieval/graph-rag.js";
import { makeGraphRagEngine, } from "../retrieval/graph-rag.js";

const requestor = <TReq, TRes>(
  handler: (request: TReq) => TRes,
): EffectRequestResponse<TReq, TRes> => ({
  request: (request) => Effect.succeed(handler(request)),
  stop: Effect.void,
});

describe("RAG engines", () => {
  it.effect(
    "runs Graph RAG without per-request service objects",
    Effect.fnUntraced(function* () {
      const prompts: Array<PromptRequest> = [];
      const triplesRequests: Array<TriplesQueryRequest> = [];
      let synthesisContext = "";

      const clients: GraphRagClients = {
        prompt: requestor<PromptRequest, PromptResponse>((request) => {
          prompts.push(request);
          if (request.name === "extract-concepts") {
            return { system: "extract-system", prompt: "extract-prompt" };
          }
          synthesisContext = String(request.variables?.context ?? "");
          return { system: "synth-system", prompt: "synth-prompt" };
        }),
        llm: requestor<TextCompletionRequest, TextCompletionResponse>((request) => {
          if (request.prompt === "extract-prompt") {
            return { response: "alpha\nbeta", endOfStream: true };
          }
          return { response: `answer:${request.prompt}`, endOfStream: true };
        }),
        embeddings: requestor<EmbeddingsRequest, EmbeddingsResponse>((request) => {
          expect(request.text).toEqual(["alpha", "beta"]);
          return { vectors: [[1], [2]] };
        }),
        graphEmbeddings: requestor<GraphEmbeddingsRequest, GraphEmbeddingsResponse>((request) => {
          expect(request.collection).toBe("project");
          return {
            entities: [{ type: "IRI", iri: "https://example.test/entity/a" }],
          };
        }),
        triples: requestor<TriplesQueryRequest, TriplesQueryResponse>((request) => {
          triplesRequests.push(request);
          return {
            triples: [
              {
                s: { type: "IRI", iri: "https://example.test/entity/a" },
                p: { type: "IRI", iri: "https://example.test/relation" },
                o: { type: "LITERAL", value: "related value" },
              },
            ],
          };
        }),
      };

      const engine = makeGraphRagEngine();
      const result = yield* engine.query(
        clients,
        "who is related?",
        { collection: "project" },
        { maxPathLength: 1 },
      );

      expect(result.answer).toBe("answer:synth-prompt");
      expect(result.subgraph).toHaveLength(1);
      expect(prompts.map((prompt) => prompt.name)).toEqual([
        "extract-concepts",
        "graph-rag-synthesize",
      ]);
      expect(triplesRequests).toHaveLength(1);
      expect(synthesisContext).toContain("https://example.test/entity/a");
      expect(synthesisContext).toContain("related value");
    }),
  );

  it.effect(
    "builds Document RAG synthesis context from returned chunks",
    Effect.fnUntraced(function* () {
      let synthesisContext = "";
      const clients: DocumentRagClients = {
        embeddings: requestor<EmbeddingsRequest, EmbeddingsResponse>((request) => {
          expect(request.text).toEqual(["explain docs"]);
          return { vectors: [[0.1, 0.2]] };
        }),
        docEmbeddings: requestor<DocumentEmbeddingsRequest, DocumentEmbeddingsResponse>((request) => {
          expect(request.collection).toBe("docs");
          return {
            chunks: [
              { chunkId: "1", score: 0.9, content: "first chunk" },
              { chunkId: "2", score: 0.8, content: "" },
              { chunkId: "3", score: 0.7, content: "second chunk" },
            ],
          };
        }),
        prompt: requestor<PromptRequest, PromptResponse>((request) => {
          synthesisContext = String(request.variables?.context ?? "");
          return { system: "doc-system", prompt: "doc-prompt" };
        }),
        llm: requestor<TextCompletionRequest, TextCompletionResponse>((request) => ({
          response: `doc-answer:${request.prompt}`,
          endOfStream: true,
        })),
      };

      const engine = makeDocumentRagEngine();
      const response = yield* engine.query(clients, "explain docs", { collection: "docs" });

      expect(response).toBe("doc-answer:doc-prompt");
      expect(synthesisContext).toBe("first chunk\n\n---\n\nsecond chunk");
    }),
  );
});
