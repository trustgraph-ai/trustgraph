/**
 * Document embeddings query service — finds similar document chunks in Qdrant.
 *
 * Wraps QdrantDocEmbeddingsQuery as a NATS consumer so Document RAG can look up
 * chunks by vector similarity over the message bus.
 *
 * Python reference: trustgraph-flow/trustgraph/query/doc_embeddings/qdrant/service.py
 */

import {
  makeFlowProcessor,
  makeConsumerSpec,
  makeProducerSpec,
  type ProcessorConfig,
  type FlowProcessorRuntime,
  type FlowContext,
  type FlowResourceNotFoundError,
  type MessagingDeliveryError,
  type DocumentEmbeddingsRequest,
  type DocumentEmbeddingsResponse,
  type Spec,
} from "@trustgraph/base";
import { NodeRuntime } from "@effect/platform-node";
import { makeFlowProcessorProgram } from "@trustgraph/base";
import { Effect, Layer, ManagedRuntime } from "effect";
import {
  QdrantDocEmbeddingsQueryLive,
  QdrantDocEmbeddingsQueryService,
  makeQdrantDocEmbeddingsQueryService,
  type QdrantDocQueryConfig,
} from "./qdrant-doc.js";

const DocumentEmbeddingsResponseProducer = makeProducerSpec<DocumentEmbeddingsResponse>("document-embeddings-response");

const onDocEmbeddingsQueryMessage = Effect.fn("DocEmbeddingsQueryService.onMessage")(function* (
  msg: DocumentEmbeddingsRequest,
  properties: Record<string, string>,
  flowCtx: FlowContext<QdrantDocEmbeddingsQueryService>,
) {
  const requestId = properties.id;
  if (requestId === undefined || requestId.length === 0) return;

  const producer = yield* flowCtx.flow.producerEffect(DocumentEmbeddingsResponseProducer);
  const query = yield* QdrantDocEmbeddingsQueryService;
  const collection = msg.collection ?? "default";
  const allChunks: DocumentEmbeddingsResponse["chunks"] = [];

  for (const vector of msg.vectors ?? []) {
    const matches = yield* query.query({
      vector,
      user: msg.user ?? "default",
      collection,
      limit: msg.limit ?? 10,
    }).pipe(
      Effect.catch((error) =>
        Effect.logError("[DocEmbeddingsQuery] Query failed", {
          error: error.message,
          operation: error.operation,
        }).pipe(
          Effect.flatMap(() =>
            producer.send(requestId, {
              chunks: [],
              error: { type: "query-error", message: error.message },
            })
          ),
          Effect.as(null),
        ),
      ),
    );
    if (matches === null) return;

    for (const match of matches) {
      allChunks.push({
        chunkId: match.chunkId,
        score: match.score,
        ...(match.content !== undefined ? { content: match.content } : {}),
      });
    }
  }

  yield* producer.send(requestId, { chunks: allChunks });
});

export const makeDocEmbeddingsQuerySpecs = (): ReadonlyArray<Spec<QdrantDocEmbeddingsQueryService>> => [
  makeConsumerSpec<
    DocumentEmbeddingsRequest,
    FlowResourceNotFoundError | MessagingDeliveryError,
    QdrantDocEmbeddingsQueryService
  >("document-embeddings-request", onDocEmbeddingsQueryMessage),
  DocumentEmbeddingsResponseProducer,
];

export type DocEmbeddingsQueryService = FlowProcessorRuntime<QdrantDocEmbeddingsQueryService>;

export function makeDocEmbeddingsQueryService(config: ProcessorConfig): DocEmbeddingsQueryService {
  const query = makeQdrantDocEmbeddingsQueryService();
  const service = makeFlowProcessor(config, {
    specifications: makeDocEmbeddingsQuerySpecs(),
    provide: (effect) =>
      effect.pipe(
        Effect.provideService(
          QdrantDocEmbeddingsQueryService,
          QdrantDocEmbeddingsQueryService.of(query),
        ),
      ),
  });
  Effect.runSync(Effect.log("[DocEmbeddingsQuery] Service initialized"));
  return service;
}

export const DocEmbeddingsQueryService = makeDocEmbeddingsQueryService;

export const program = makeFlowProcessorProgram<ProcessorConfig & QdrantDocQueryConfig, never, QdrantDocEmbeddingsQueryService>({
  id: "doc-embeddings-query",
  specs: () => makeDocEmbeddingsQuerySpecs(),
  layer: (config) => QdrantDocEmbeddingsQueryLive(config),
});

const docEmbeddingsQueryRuntime = ManagedRuntime.make(Layer.empty);

export function run(): Promise<void> {
  return docEmbeddingsQueryRuntime.runPromise(program);
}

export function runMain(): void {
  NodeRuntime.runMain(program);
}
