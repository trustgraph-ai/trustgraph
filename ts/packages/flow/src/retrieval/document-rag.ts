/**
 * Document RAG retrieval pipeline.
 *
 * Python reference: trustgraph-flow/trustgraph/retrieval/document_rag/
 */

import type {
  DocumentEmbeddingsRequest,
  DocumentEmbeddingsResponse,
  EmbeddingsRequest,
  EmbeddingsResponse,
  EffectRequestResponse,
  PromptRequest,
  PromptResponse,
  TextCompletionRequest,
  TextCompletionResponse,
} from "@trustgraph/base";
import { errorMessage } from "@trustgraph/base";
import { Context, Effect, Layer } from "effect";
import * as S from "effect/Schema";

export interface DocumentRagClients {
  llm: EffectRequestResponse<TextCompletionRequest, TextCompletionResponse>;
  embeddings: EffectRequestResponse<EmbeddingsRequest, EmbeddingsResponse>;
  docEmbeddings: EffectRequestResponse<DocumentEmbeddingsRequest, DocumentEmbeddingsResponse>;
  prompt: EffectRequestResponse<PromptRequest, PromptResponse>;
}

export type ChunkCallback = (text: string, endOfStream: boolean) => Promise<void>;

export interface DocumentRagQueryOptions {
  readonly collection?: string;
  readonly streaming?: boolean;
  readonly chunkCallback?: ChunkCallback;
}

export class DocumentRagEngineError extends S.TaggedErrorClass<DocumentRagEngineError>()(
  "DocumentRagEngineError",
  {
    message: S.String,
    operation: S.String,
    cause: S.DefectWithStack,
  },
) {}

export interface DocumentRagEngineShape {
  readonly query: (
    clients: DocumentRagClients,
    queryText: string,
    options?: DocumentRagQueryOptions,
  ) => Effect.Effect<string, DocumentRagEngineError>;
}

export class DocumentRagEngine extends Context.Service<DocumentRagEngine, DocumentRagEngineShape>()(
  "@trustgraph/flow/retrieval/document-rag/DocumentRagEngine",
) {}

const documentRagError = (operation: string, cause: unknown) =>
  DocumentRagEngineError.make({
    operation,
    cause,
    message: errorMessage(cause),
  });

export function makeDocumentRagEngine(): DocumentRagEngineShape {
  return {
    query: Effect.fn("DocumentRagEngine.query")((
      clients: DocumentRagClients,
      queryText: string,
      options?: DocumentRagQueryOptions,
    ) => queryDocumentRag(clients, queryText, options),
    ),
  };
}

export const DocumentRagLive: Layer.Layer<DocumentRagEngine> = Layer.succeed(
  DocumentRagEngine,
  DocumentRagEngine.of(makeDocumentRagEngine()),
);

export interface DocumentRag {
  readonly query: (
    queryText: string,
    options?: DocumentRagQueryOptions,
  ) => Promise<string>;
}

export function makeDocumentRag(clients: DocumentRagClients): DocumentRag {
  const engine = makeDocumentRagEngine();
  return {
    query: (queryText, options) =>
      Effect.runPromise(engine.query(clients, queryText, options)),
  };
}

function queryDocumentRag(
  clients: DocumentRagClients,
  queryText: string,
  options?: DocumentRagQueryOptions,
): Effect.Effect<string, DocumentRagEngineError> {
  return Effect.gen(function* () {
    const collection = options?.collection ?? "default";

    const embResp = yield* clients.embeddings.request({ text: [queryText] }).pipe(
      Effect.mapError((cause) => documentRagError("embeddings", cause)),
    );
    const vectors = embResp.vectors;

    const docResp = yield* clients.docEmbeddings.request({
        vectors,
        limit: 10,
        collection,
        user: "default",
      }).pipe(
        Effect.mapError((cause) => documentRagError("document-embeddings", cause)),
      );
    const chunks = docResp.chunks ?? [];
    yield* Effect.log(`[DocumentRag] Found ${chunks.length} matching chunks`);

    const context = chunks
      .flatMap((chunk) =>
        chunk.content !== undefined && chunk.content.length > 0 ? [chunk.content] : [],
      )
      .join("\n\n---\n\n");

    const promptResp = yield* clients.prompt.request({
        name: "document-rag-synthesize",
        variables: { query: queryText, context },
      }).pipe(
        Effect.mapError((cause) => documentRagError("prompt", cause)),
      );

    const resp = yield* clients.llm.request({
        system: promptResp.system,
        prompt: promptResp.prompt,
      }).pipe(
        Effect.mapError((cause) => documentRagError("llm", cause)),
      );

    return resp.response;
  });
}
