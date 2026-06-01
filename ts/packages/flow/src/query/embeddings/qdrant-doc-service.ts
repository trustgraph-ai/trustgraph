/**
 * Document embeddings query service — finds similar document chunks in Qdrant.
 *
 * Wraps QdrantDocEmbeddingsQuery as a NATS consumer so Document RAG can look up
 * chunks by vector similarity over the message bus.
 *
 * Python reference: trustgraph-flow/trustgraph/query/doc_embeddings/qdrant/service.py
 */

import {
  FlowProcessor,
  ConsumerSpec,
  ProducerSpec,
  type ProcessorConfig,
  type FlowContext,
  type FlowResourceNotFoundError,
  type MessagingDeliveryError,
  type DocumentEmbeddingsRequest,
  type DocumentEmbeddingsResponse,
  type Spec,
} from "@trustgraph/base";
import { makeFlowProcessorProgram } from "@trustgraph/base";
import { Effect } from "effect";
import {
  QdrantDocEmbeddingsQueryLive,
  QdrantDocEmbeddingsQueryService,
  makeQdrantDocEmbeddingsQueryService,
  type QdrantDocQueryConfig,
} from "./qdrant-doc.js";

const onDocEmbeddingsQueryMessage = Effect.fn("DocEmbeddingsQueryService.onMessage")(function* (
  msg: DocumentEmbeddingsRequest,
  properties: Record<string, string>,
  flowCtx: FlowContext<QdrantDocEmbeddingsQueryService>,
) {
  const requestId = properties.id;
  if (requestId === undefined || requestId.length === 0) return;

  const producer = yield* flowCtx.flow.producerEffect<DocumentEmbeddingsResponse>("document-embeddings-response");
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
  new ConsumerSpec<
    DocumentEmbeddingsRequest,
    FlowResourceNotFoundError | MessagingDeliveryError,
    QdrantDocEmbeddingsQueryService
  >("document-embeddings-request", onDocEmbeddingsQueryMessage),
  new ProducerSpec<DocumentEmbeddingsResponse>("document-embeddings-response"),
];

export class DocEmbeddingsQueryService extends FlowProcessor<QdrantDocEmbeddingsQueryService> {
  private readonly query = makeQdrantDocEmbeddingsQueryService();

  constructor(config: ProcessorConfig) {
    super(config);

    for (const spec of makeDocEmbeddingsQuerySpecs()) {
      this.registerSpecification(spec);
    }

    console.log("[DocEmbeddingsQuery] Service initialized");
  }

  override startEffect() {
    return super.startEffect().pipe(
      Effect.provideService(
        QdrantDocEmbeddingsQueryService,
        QdrantDocEmbeddingsQueryService.of(this.query),
      ),
    );
  }
}

export const program = makeFlowProcessorProgram<ProcessorConfig & QdrantDocQueryConfig, never, QdrantDocEmbeddingsQueryService>({
  id: "doc-embeddings-query",
  specs: () => makeDocEmbeddingsQuerySpecs(),
  layer: (config) => QdrantDocEmbeddingsQueryLive(config),
});

export async function run(): Promise<void> {
  await Effect.runPromise(program);
}
