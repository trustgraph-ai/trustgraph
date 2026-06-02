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
  FlowRequestor,
  PromptRequest,
  PromptResponse,
  TextCompletionRequest,
  TextCompletionResponse,
} from "@trustgraph/base";
import { errorMessage } from "@trustgraph/base";
import { Context, Effect, Layer } from "effect";
import * as S from "effect/Schema";

export interface DocumentRagClients {
  llm: FlowRequestor<TextCompletionRequest, TextCompletionResponse>;
  embeddings: FlowRequestor<EmbeddingsRequest, EmbeddingsResponse>;
  docEmbeddings: FlowRequestor<DocumentEmbeddingsRequest, DocumentEmbeddingsResponse>;
  prompt: FlowRequestor<PromptRequest, PromptResponse>;
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

    const embResp = yield* Effect.tryPromise({
      try: () => clients.embeddings.request({ text: [queryText] }),
      catch: (cause) => documentRagError("embeddings", cause),
    });
    const vectors = embResp.vectors;

    const docResp = yield* Effect.tryPromise({
      try: () => clients.docEmbeddings.request({
        vectors,
        limit: 10,
        collection,
        user: "default",
      }),
      catch: (cause) => documentRagError("document-embeddings", cause),
    });
    const chunks = docResp.chunks ?? [];
    yield* Effect.log(`[DocumentRag] Found ${chunks.length} matching chunks`);

    const context = chunks
      .flatMap((chunk) =>
        chunk.content !== undefined && chunk.content.length > 0 ? [chunk.content] : [],
      )
      .join("\n\n---\n\n");

    const promptResp = yield* Effect.tryPromise({
      try: () => clients.prompt.request({
        name: "document-rag-synthesize",
        variables: { query: queryText, context },
      }),
      catch: (cause) => documentRagError("prompt", cause),
    });

    const resp = yield* Effect.tryPromise({
      try: () => clients.llm.request({
        system: promptResp.system,
        prompt: promptResp.prompt,
      }),
      catch: (cause) => documentRagError("llm", cause),
    });

    return resp.response;
  });
}
