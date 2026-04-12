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
  type DocumentEmbeddingsRequest,
  type DocumentEmbeddingsResponse,
} from "@trustgraph/base";
import { QdrantDocEmbeddingsQuery } from "./qdrant-doc.js";

export class DocEmbeddingsQueryService extends FlowProcessor {
  private query: QdrantDocEmbeddingsQuery;

  constructor(config: ProcessorConfig) {
    super(config);
    this.query = new QdrantDocEmbeddingsQuery();

    this.registerSpecification(
      new ConsumerSpec<DocumentEmbeddingsRequest>(
        "document-embeddings-request",
        this.onMessage.bind(this),
      ),
    );
    this.registerSpecification(
      new ProducerSpec<DocumentEmbeddingsResponse>("document-embeddings-response"),
    );

    console.log("[DocEmbeddingsQuery] Service initialized");
  }

  private async onMessage(
    msg: DocumentEmbeddingsRequest,
    properties: Record<string, string>,
    flowCtx: FlowContext,
  ): Promise<void> {
    const requestId = properties.id;
    if (!requestId) return;

    const producer = flowCtx.flow.producer<DocumentEmbeddingsResponse>("document-embeddings-response");
    const collection = msg.collection ?? "default";

    try {
      const allChunks: DocumentEmbeddingsResponse["chunks"] = [];

      for (const vector of msg.vectors ?? []) {
        const matches = await this.query.query({
          vector,
          user: msg.user ?? "default",
          collection,
          limit: msg.limit ?? 10,
        });

        for (const match of matches) {
          allChunks.push({
            chunkId: match.chunkId,
            score: match.score,
            content: match.content,
          });
        }
      }

      await producer.send(requestId, { chunks: allChunks });
    } catch (err) {
      console.error("[DocEmbeddingsQuery] Query failed:", err);
      await producer.send(requestId, {
        chunks: [],
        error: { type: "query-error", message: String(err) },
      });
    }
  }
}

export async function run(): Promise<void> {
  await DocEmbeddingsQueryService.launch("doc-embeddings-query");
}
