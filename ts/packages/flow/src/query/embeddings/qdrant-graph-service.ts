/**
 * Graph embeddings query service — finds similar entities in Qdrant via FlowProcessor.
 *
 * Wraps QdrantGraphEmbeddingsQuery as a NATS consumer so Graph RAG can look up
 * entities by vector similarity over the message bus.
 *
 * Python reference: trustgraph-flow/trustgraph/query/graph_embeddings/qdrant/service.py
 */

import {
  FlowProcessor,
  ConsumerSpec,
  ProducerSpec,
  type ProcessorConfig,
  type FlowContext,
  type FlowResourceNotFoundError,
  type MessagingDeliveryError,
  type GraphEmbeddingsRequest,
  type GraphEmbeddingsResponse,
  type Spec,
} from "@trustgraph/base";
import { makeFlowProcessorProgram } from "@trustgraph/base";
import { Effect } from "effect";
import {
  QdrantGraphEmbeddingsQueryLive,
  QdrantGraphEmbeddingsQueryService,
  makeQdrantGraphEmbeddingsQueryService,
  type QdrantGraphQueryConfig,
} from "./qdrant-graph.js";

const onGraphEmbeddingsQueryMessage = Effect.fn("GraphEmbeddingsQueryService.onMessage")(function* (
  msg: GraphEmbeddingsRequest,
  properties: Record<string, string>,
  flowCtx: FlowContext<QdrantGraphEmbeddingsQueryService>,
) {
  const requestId = properties.id;
  if (requestId === undefined || requestId.length === 0) return;

  const producer = yield* flowCtx.flow.producerEffect<GraphEmbeddingsResponse>("graph-embeddings-response");
  const query = yield* QdrantGraphEmbeddingsQueryService;
  const user = msg.user ?? "default";
  const collection = msg.collection ?? "default";
  yield* Effect.log(
    `[GraphEmbeddingsQuery] Request: user=${user}, collection=${collection}, vectors=${msg.vectors?.length ?? 0}, limit=${msg.limit}`,
  );

  const allEntities: GraphEmbeddingsResponse["entities"] = [];

  for (const vector of msg.vectors ?? []) {
    const matches = yield* query.query({
      vector,
      user,
      collection,
      limit: msg.limit ?? 50,
    }).pipe(
      Effect.catch((error) =>
        Effect.logError("[GraphEmbeddingsQuery] Query failed", {
          error: error.message,
          operation: error.operation,
        }).pipe(
          Effect.flatMap(() =>
            producer.send(requestId, {
              entities: [],
              error: { type: "query-error", message: error.message },
            })
          ),
          Effect.as(null),
        ),
      ),
    );
    if (matches === null) return;

    for (const match of matches) {
      allEntities.push(match.entity);
    }
  }

  yield* producer.send(requestId, { entities: allEntities });
});

export const makeGraphEmbeddingsQuerySpecs = (): ReadonlyArray<Spec<QdrantGraphEmbeddingsQueryService>> => [
  new ConsumerSpec<
    GraphEmbeddingsRequest,
    FlowResourceNotFoundError | MessagingDeliveryError,
    QdrantGraphEmbeddingsQueryService
  >("graph-embeddings-request", onGraphEmbeddingsQueryMessage),
  new ProducerSpec<GraphEmbeddingsResponse>("graph-embeddings-response"),
];

export class GraphEmbeddingsQueryService extends FlowProcessor<QdrantGraphEmbeddingsQueryService> {
  private readonly query = makeQdrantGraphEmbeddingsQueryService();

  constructor(config: ProcessorConfig) {
    super(config);

    for (const spec of makeGraphEmbeddingsQuerySpecs()) {
      this.registerSpecification(spec);
    }

    console.log("[GraphEmbeddingsQuery] Service initialized");
  }

  override startEffect() {
    return super.startEffect().pipe(
      Effect.provideService(
        QdrantGraphEmbeddingsQueryService,
        QdrantGraphEmbeddingsQueryService.of(this.query),
      ),
    );
  }
}

export const program = makeFlowProcessorProgram<ProcessorConfig & QdrantGraphQueryConfig, never, QdrantGraphEmbeddingsQueryService>({
  id: "graph-embeddings-query",
  specs: () => makeGraphEmbeddingsQuerySpecs(),
  layer: (config) => QdrantGraphEmbeddingsQueryLive(config),
});

export async function run(): Promise<void> {
  await Effect.runPromise(program);
}
