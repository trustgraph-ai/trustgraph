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
  type GraphEmbeddingsRequest,
  type GraphEmbeddingsResponse,
} from "@trustgraph/base";
import { QdrantGraphEmbeddingsQuery } from "./qdrant-graph.js";

export class GraphEmbeddingsQueryService extends FlowProcessor {
  private query: QdrantGraphEmbeddingsQuery;

  constructor(config: ProcessorConfig) {
    super(config);
    this.query = new QdrantGraphEmbeddingsQuery();

    this.registerSpecification(
      new ConsumerSpec<GraphEmbeddingsRequest>(
        "graph-embeddings-request",
        this.onMessage.bind(this),
      ),
    );
    this.registerSpecification(
      new ProducerSpec<GraphEmbeddingsResponse>("graph-embeddings-response"),
    );

    console.log("[GraphEmbeddingsQuery] Service initialized");
  }

  private async onMessage(
    msg: GraphEmbeddingsRequest,
    properties: Record<string, string>,
    flowCtx: FlowContext,
  ): Promise<void> {
    const requestId = properties.id;
    if (!requestId) return;

    const producer = flowCtx.flow.producer<GraphEmbeddingsResponse>("graph-embeddings-response");
    const user = msg.collection ?? "default";
    const collection = msg.collection ?? "default";

    try {
      // Query for each vector and aggregate results
      const allEntities: GraphEmbeddingsResponse["entities"] = [];

      for (const vector of msg.vectors ?? []) {
        const matches = await this.query.query({
          vector,
          user,
          collection,
          limit: msg.limit ?? 50,
        });

        for (const match of matches) {
          allEntities.push(match.entity);
        }
      }

      await producer.send(requestId, { entities: allEntities });
    } catch (err) {
      console.error("[GraphEmbeddingsQuery] Query failed:", err);
      await producer.send(requestId, {
        entities: [],
        error: { type: "query-error", message: String(err) },
      });
    }
  }
}

export async function run(): Promise<void> {
  await GraphEmbeddingsQueryService.launch("graph-embeddings-query");
}
