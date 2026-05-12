/**
 * Qdrant document embeddings query service.
 *
 * Input: vector, user, collection, limit
 * Output: list of { chunkId, score } matches
 *
 * Python reference: trustgraph-flow/trustgraph/query/doc_embeddings/qdrant/service.py
 */

import { QdrantClient } from "@qdrant/js-client-rest";

export interface QdrantDocQueryConfig {
  url?: string;
  apiKey?: string;
}

export interface ChunkMatch {
  chunkId: string;
  score: number;
  content?: string;
}

export interface DocEmbeddingsQueryRequest {
  vector: number[];
  user: string;
  collection: string;
  limit: number;
}

export class QdrantDocEmbeddingsQuery {
  private client: QdrantClient;

  constructor(config: QdrantDocQueryConfig = {}) {
    const url = config.url ?? process.env.QDRANT_URL ?? "http://localhost:6333";
    const apiKey = config.apiKey ?? process.env.QDRANT_API_KEY;

    this.client = new QdrantClient({
      url,
      ...(apiKey !== undefined && apiKey.length > 0 ? { apiKey } : {}),
    });

    console.log("[QdrantDocQuery] Query service initialized");
  }

  async query(request: DocEmbeddingsQueryRequest): Promise<ChunkMatch[]> {
    const { vector, user, collection, limit } = request;

    if (vector.length === 0) {
      return [];
    }

    const dim = vector.length;
    const collectionName = `d_${user}_${collection}_${dim}`;

    // Check if collection exists -- return empty if not
    const exists = await this.client.collectionExists(collectionName);
    if (!exists.exists) {
      console.log(
        `[QdrantDocQuery] Collection ${collectionName} does not exist, returning empty results`,
      );
      return [];
    }

    const searchResult = await this.client.search(collectionName, {
      vector,
      limit,
      with_payload: true,
    });

    const chunks: ChunkMatch[] = [];
    for (const point of searchResult) {
      const payload = point.payload as Record<string, unknown> | undefined;
      const chunkId = payload?.chunk_id as string | undefined;
      if (chunkId !== undefined && chunkId.length > 0) {
        chunks.push({
          chunkId,
          score: point.score,
          ...(typeof payload?.content === "string" ? { content: payload.content } : {}),
        });
      }
    }

    return chunks;
  }
}
