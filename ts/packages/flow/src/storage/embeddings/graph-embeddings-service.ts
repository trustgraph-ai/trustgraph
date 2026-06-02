/**
 * Graph embeddings store service — vectorizes entity contexts and writes to Qdrant.
 *
 * A FlowProcessor that:
 * 1. Consumes EntityContexts messages
 * 2. Calls the embeddings service to vectorize entity context strings
 * 3. Writes entity+vector pairs to Qdrant using QdrantGraphEmbeddingsStore
 *
 * Python reference: trustgraph-flow/trustgraph/storage/graph_embeddings/qdrant/service.py
 */

import {
  makeFlowProcessor,
  makeConsumerSpec,
  makeRequestResponseSpec,
  type ProcessorConfig,
  type FlowProcessorRuntime,
  type FlowContext,
  type FlowResourceNotFoundError,
  type MessagingDeliveryError,
  type MessagingTimeoutError,
  type EntityContexts,
  type EmbeddingsRequest,
  type EmbeddingsResponse,
  type Spec,
} from "@trustgraph/base";
import { NodeRuntime } from "@effect/platform-node";
import { makeFlowProcessorProgram } from "@trustgraph/base";
import { Effect, Layer, ManagedRuntime } from "effect";
import {
  QdrantGraphEmbeddingsStoreLive,
  QdrantGraphEmbeddingsStoreService,
  makeQdrantGraphEmbeddingsStoreService,
  type QdrantGraphEmbeddingsConfig,
  type QdrantGraphEmbeddingsStoreError,
} from "./qdrant-graph.js";

type GraphEmbeddingsStoreRequirements = QdrantGraphEmbeddingsStoreService;
type GraphEmbeddingsStoreError =
  | FlowResourceNotFoundError
  | MessagingDeliveryError
  | MessagingTimeoutError
  | QdrantGraphEmbeddingsStoreError;

const onGraphEmbeddingsStoreMessage = Effect.fn("GraphEmbeddingsStoreService.onMessage")(function* (
  msg: EntityContexts,
  _properties: Record<string, string>,
  flowCtx: FlowContext<GraphEmbeddingsStoreRequirements>,
): Effect.fn.Return<void, GraphEmbeddingsStoreError, GraphEmbeddingsStoreRequirements> {
  if (msg.entities.length === 0) return;

  const embeddingsClient =
    yield* flowCtx.flow.requestorEffect<EmbeddingsRequest, EmbeddingsResponse>("embeddings-client");

  const user = msg.metadata?.user ?? "default";
  const collection = msg.metadata?.collection ?? "default";
  const texts = msg.entities.map((entity) => entity.context);

  const embResponse = yield* embeddingsClient.request({ text: texts });
  if (embResponse.error !== undefined) {
    yield* Effect.logError("[GraphEmbeddingsStore] Embeddings error", {
      error: embResponse.error.message,
    });
    return;
  }

  const entities = msg.entities.map((entity, index) => ({
    entity: entity.entity,
    vector: embResponse.vectors[index],
    chunkId: entity.chunkId,
  }));
  const store = yield* QdrantGraphEmbeddingsStoreService;

  yield* store.store({ user, collection, entities });

  yield* Effect.log(
    `[GraphEmbeddingsStore] Stored ${entities.length} embeddings for ${user}/${collection}`,
  );
});

export const makeGraphEmbeddingsStoreSpecs = (): ReadonlyArray<Spec<GraphEmbeddingsStoreRequirements>> => [
  makeConsumerSpec<EntityContexts, GraphEmbeddingsStoreError, GraphEmbeddingsStoreRequirements>(
    "store-graph-embeddings-input",
    onGraphEmbeddingsStoreMessage,
  ),
  makeRequestResponseSpec<EmbeddingsRequest, EmbeddingsResponse>(
    "embeddings-client",
    "embeddings-request",
    "embeddings-response",
  ),
];

export type GraphEmbeddingsStoreService = FlowProcessorRuntime<GraphEmbeddingsStoreRequirements>;

export function makeGraphEmbeddingsStoreService(config: ProcessorConfig): GraphEmbeddingsStoreService {
  const store = makeQdrantGraphEmbeddingsStoreService();
  const service = makeFlowProcessor(config, {
    specifications: makeGraphEmbeddingsStoreSpecs(),
    provide: (effect) =>
      effect.pipe(
        Effect.provideService(
          QdrantGraphEmbeddingsStoreService,
          QdrantGraphEmbeddingsStoreService.of(store),
        ),
      ),
  });
  Effect.runSync(Effect.log("[GraphEmbeddingsStore] Service initialized"));
  return service;
}

export const GraphEmbeddingsStoreService = makeGraphEmbeddingsStoreService;

export const program = makeFlowProcessorProgram<
  ProcessorConfig & QdrantGraphEmbeddingsConfig,
  never,
  GraphEmbeddingsStoreRequirements
>({
  id: "graph-embeddings-store",
  specs: () => makeGraphEmbeddingsStoreSpecs(),
  layer: (config) => QdrantGraphEmbeddingsStoreLive(config),
});

const graphEmbeddingsStoreRuntime = ManagedRuntime.make(Layer.empty);

export function run(): Promise<void> {
  return graphEmbeddingsStoreRuntime.runPromise(program);
}

export function runMain(): void {
  NodeRuntime.runMain(program);
}
