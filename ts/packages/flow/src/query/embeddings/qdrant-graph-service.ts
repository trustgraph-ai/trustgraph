/**
 * Graph embeddings query service — finds similar entities in Qdrant via FlowProcessor.
 *
 * Wraps QdrantGraphEmbeddingsQuery as a NATS consumer so Graph RAG can look up
 * entities by vector similarity over the message bus.
 *
 * Python reference: trustgraph-flow/trustgraph/query/graph_embeddings/qdrant/service.py
 */

import {
  makeFlowProcessor,
  makeConsumerSpec,
  makeProducerSpec,
  processorLifecycleError,
  type ProcessorConfig,
  type FlowProcessorRuntime,
  type FlowProcessorStartEffect,
  type FlowContext,
  type FlowResourceNotFoundError,
  type MessagingDeliveryError,
  type GraphEmbeddingsRequest,
  type GraphEmbeddingsResponse,
  type Spec,
} from "@trustgraph/base";
import { NodeRuntime } from "@effect/platform-node";
import { makeFlowProcessorProgram } from "@trustgraph/base";
import { Effect } from "effect";
import {
  QdrantGraphEmbeddingsQueryLive,
  QdrantGraphEmbeddingsQueryService,
  makeQdrantGraphEmbeddingsQueryServiceEffect,
  type QdrantGraphQueryConfig,
  type QdrantGraphEmbeddingsQueryError,
} from "./qdrant-graph.js";

const GraphEmbeddingsResponseProducer = makeProducerSpec<GraphEmbeddingsResponse>("graph-embeddings-response");

const onGraphEmbeddingsQueryMessage = Effect.fn("GraphEmbeddingsQueryService.onMessage")(function* (
  msg: GraphEmbeddingsRequest,
  properties: Record<string, string>,
  flowCtx: FlowContext<QdrantGraphEmbeddingsQueryService>,
) {
  const requestId = properties.id;
  if (requestId === undefined || requestId.length === 0) return;

  const producer = yield* flowCtx.flow.producerEffect(GraphEmbeddingsResponseProducer);
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
  makeConsumerSpec<
    GraphEmbeddingsRequest,
    FlowResourceNotFoundError | MessagingDeliveryError,
    QdrantGraphEmbeddingsQueryService
  >("graph-embeddings-request", onGraphEmbeddingsQueryMessage),
  GraphEmbeddingsResponseProducer,
];

export type GraphEmbeddingsQueryService = FlowProcessorRuntime<QdrantGraphEmbeddingsQueryService>;

const provideQdrantGraphEmbeddingsQuery = (processorId: string) =>
  Effect.fn("GraphEmbeddingsQueryService.provideQdrant")(function* (
    effect: FlowProcessorStartEffect<QdrantGraphEmbeddingsQueryService>,
  ) {
    const query = yield* makeQdrantGraphEmbeddingsQueryServiceEffect().pipe(
      Effect.mapError((error) => processorLifecycleError(processorId, "qdrant-graph-query-connect", error)),
    );
    yield* effect.pipe(
      Effect.provideService(
        QdrantGraphEmbeddingsQueryService,
        QdrantGraphEmbeddingsQueryService.of(query),
      ),
    );
  });

export function makeGraphEmbeddingsQueryService(config: ProcessorConfig): GraphEmbeddingsQueryService {
  return makeFlowProcessor(config, {
    specifications: makeGraphEmbeddingsQuerySpecs(),
    provide: provideQdrantGraphEmbeddingsQuery(config.id),
  });
}

export const GraphEmbeddingsQueryService = makeGraphEmbeddingsQueryService;

export const program = makeFlowProcessorProgram<
  ProcessorConfig & QdrantGraphQueryConfig,
  QdrantGraphEmbeddingsQueryError,
  QdrantGraphEmbeddingsQueryService
>({
  id: "graph-embeddings-query",
  specs: () => makeGraphEmbeddingsQuerySpecs(),
  layer: (config) => QdrantGraphEmbeddingsQueryLive(config),
});

export function runMain(): void {
  NodeRuntime.runMain(program);
}
