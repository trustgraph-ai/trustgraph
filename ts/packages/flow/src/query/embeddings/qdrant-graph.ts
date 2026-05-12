/**
 * Qdrant graph embeddings query service.
 *
 * Input: vector, user, collection, limit
 * Output: list of Term entities with scores, deduplicated by entity value
 *
 * Queries limit*2 points and deduplicates by entity value to ensure
 * we return up to `limit` unique entities.
 *
 * Python reference: trustgraph-flow/trustgraph/query/graph_embeddings/qdrant/service.py
 */

import { QdrantClient } from "@qdrant/js-client-rest";
import type { Term } from "@trustgraph/base";

export interface QdrantGraphQueryConfig {
  url?: string;
  apiKey?: string;
}

export interface EntityMatch {
  entity: Term;
  score: number;
}

export interface GraphEmbeddingsQueryRequest {
  vector: number[];
  user: string;
  collection: string;
  limit: number;
}

function createTerm(value: string): Term {
  if (value.startsWith("http://") || value.startsWith("https://")) {
    return { type: "IRI", iri: value };
  }
  return { type: "LITERAL", value };
}

export class QdrantGraphEmbeddingsQuery {
  private client: QdrantClient;

  constructor(config: QdrantGraphQueryConfig = {}) {
    const url = config.url ?? process.env.QDRANT_URL ?? "http://localhost:6333";
    const apiKey = config.apiKey ?? process.env.QDRANT_API_KEY;

    this.client = new QdrantClient({
      url,
      ...(apiKey !== undefined && apiKey.length > 0 ? { apiKey } : {}),
    });

    console.log("[QdrantGraphQuery] Query service initialized");
  }

  async query(request: GraphEmbeddingsQueryRequest): Promise<EntityMatch[]> {
    const { vector, user, collection, limit } = request;

    if (vector.length === 0) {
      return [];
    }

    const dim = vector.length;
    const collectionName = `t_${user}_${collection}_${dim}`;

    // Check if collection exists -- return empty if not
    const exists = await this.client.collectionExists(collectionName);
    if (!exists.exists) {
      console.log(
        `[QdrantGraphQuery] Collection ${collectionName} does not exist, returning empty results`,
      );
      return [];
    }

    // Query 2x the limit so we have a better chance of getting `limit`
    // unique entities after deduplication (same heuristic as Python impl)
    const searchResult = await this.client.search(collectionName, {
      vector,
      limit: limit * 2,
      with_payload: true,
    });

    const entitySet = new Set<string>();
    const entities: EntityMatch[] = [];

    for (const point of searchResult) {
      const payload = point.payload as Record<string, unknown> | undefined;
      const entityValue = payload?.entity as string | undefined;
      if (entityValue === undefined || entityValue.length === 0) continue;

      // Deduplicate by entity value, keeping the highest score (results are
      // already sorted by score descending from Qdrant)
      if (!entitySet.has(entityValue)) {
        entitySet.add(entityValue);
        entities.push({
          entity: createTerm(entityValue),
          score: point.score,
        });
      }

      // Stop once we have enough unique entities
      if (entities.length >= limit) break;
    }

    return entities;
  }
}
