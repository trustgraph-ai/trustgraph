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
  FlowProcessor,
  ConsumerSpec,
  RequestResponseSpec,
  type ProcessorConfig,
  type FlowContext,
  type EntityContexts,
  type EmbeddingsRequest,
  type EmbeddingsResponse,
} from "@trustgraph/base";
import { QdrantGraphEmbeddingsStore } from "./qdrant-graph.js";

export class GraphEmbeddingsStoreService extends FlowProcessor {
  private store: QdrantGraphEmbeddingsStore;

  constructor(config: ProcessorConfig) {
    super(config);
    this.store = new QdrantGraphEmbeddingsStore();

    this.registerSpecification(
      new ConsumerSpec<EntityContexts>(
        "store-graph-embeddings-input",
        this.onMessage.bind(this),
      ),
    );
    this.registerSpecification(
      new RequestResponseSpec<EmbeddingsRequest, EmbeddingsResponse>(
        "embeddings-client",
        "embeddings-request",
        "embeddings-response",
      ),
    );

    console.log("[GraphEmbeddingsStore] Service initialized");
  }

  private async onMessage(
    msg: EntityContexts,
    properties: Record<string, string>,
    flowCtx: FlowContext,
  ): Promise<void> {
    if (!msg.entities || msg.entities.length === 0) return;

    const embeddingsClient =
      flowCtx.flow.requestor<EmbeddingsRequest, EmbeddingsResponse>("embeddings-client");

    const user = msg.metadata?.user ?? "default";
    const collection = msg.metadata?.collection ?? "default";

    // Get text contexts for vectorization
    const texts = msg.entities.map((e) => e.context);

    // Call embeddings service
    const embResponse = await embeddingsClient.request({ text: texts });
    if (embResponse.error) {
      console.error(
        "[GraphEmbeddingsStore] Embeddings error:",
        embResponse.error.message,
      );
      return;
    }

    // Store entity+vector pairs
    const entities = msg.entities.map((e, i) => ({
      entity: e.entity,
      vector: embResponse.vectors[i],
      chunkId: e.chunkId,
    }));

    await this.store.store({ user, collection, entities });

    console.log(
      `[GraphEmbeddingsStore] Stored ${entities.length} embeddings for ${user}/${collection}`,
    );
  }
}

export async function run(): Promise<void> {
  await GraphEmbeddingsStoreService.launch("graph-embeddings-store");
}
