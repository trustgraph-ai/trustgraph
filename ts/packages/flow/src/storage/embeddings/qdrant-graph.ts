/**
 * Qdrant graph embeddings write service.
 *
 * Stores entity/vector pairs in Qdrant for graph embeddings lookup.
 * Collection naming: t_{user}_{collection}_{dimension}
 * Collections are lazily created on first write with cosine distance.
 *
 * Python reference: trustgraph-flow/trustgraph/storage/graph_embeddings/qdrant/write.py
 */

import { QdrantClient } from "@qdrant/js-client-rest";
import type { Term } from "@trustgraph/base";

export interface QdrantGraphEmbeddingsConfig {
  url?: string;
  apiKey?: string;
}

export interface GraphEmbeddingEntity {
  entity: Term;
  vector: number[];
  chunkId?: string;
}

export interface GraphEmbeddingsMessage {
  user: string;
  collection: string;
  entities: GraphEmbeddingEntity[];
}

function getTermValue(term: Term): string | null {
  switch (term.type) {
    case "IRI":
      return term.iri;
    case "LITERAL":
      return term.value;
    case "BLANK":
      return term.id;
    case "TRIPLE":
      return null;
  }
}

export class QdrantGraphEmbeddingsStore {
  private client: QdrantClient;
  private knownCollections = new Set<string>();

  constructor(config: QdrantGraphEmbeddingsConfig = {}) {
    const url = config.url ?? process.env.QDRANT_URL ?? "http://localhost:6333";
    const apiKey = config.apiKey ?? process.env.QDRANT_API_KEY;

    this.client = new QdrantClient({
      url,
      ...(apiKey !== undefined && apiKey.length > 0 ? { apiKey } : {}),
    });

    console.log("[QdrantGraphEmbeddings] Store initialized");
  }

  private collectionName(user: string, collection: string, dim: number): string {
    return `t_${user}_${collection}_${dim}`;
  }

  private async ensureCollection(name: string, dim: number): Promise<void> {
    if (this.knownCollections.has(name)) return;

    const exists = await this.client.collectionExists(name);
    if (!exists.exists) {
      console.log(`[QdrantGraphEmbeddings] Creating collection ${name} (dim=${dim})`);
      await this.client.createCollection(name, {
        vectors: { size: dim, distance: "Cosine" },
      });
    }

    this.knownCollections.add(name);
  }

  async store(message: GraphEmbeddingsMessage): Promise<void> {
    for (const entry of message.entities) {
      const entityValue = getTermValue(entry.entity);
      if (entityValue === null || entityValue.length === 0) continue;
      if (entry.vector.length === 0) continue;

      const dim = entry.vector.length;
      const name = this.collectionName(message.user, message.collection, dim);

      await this.ensureCollection(name, dim);

      const payload: Record<string, unknown> = { entity: entityValue };
      if (entry.chunkId !== undefined && entry.chunkId.length > 0) {
        payload.chunk_id = entry.chunkId;
      }

      await this.client.upsert(name, {
        points: [
          {
            id: crypto.randomUUID(),
            vector: entry.vector,
            payload,
          },
        ],
      });
    }
  }

  async deleteCollection(user: string, collection: string): Promise<void> {
    const prefix = `t_${user}_${collection}_`;

    const allCollections = await this.client.getCollections();
    const matching = allCollections.collections.filter((c) =>
      c.name.startsWith(prefix),
    );

    if (matching.length === 0) {
      console.log(`[QdrantGraphEmbeddings] No collections matching prefix ${prefix}`);
      return;
    }

    for (const coll of matching) {
      await this.client.deleteCollection(coll.name);
      this.knownCollections.delete(coll.name);
      console.log(`[QdrantGraphEmbeddings] Deleted collection: ${coll.name}`);
    }

    console.log(
      `[QdrantGraphEmbeddings] Deleted ${matching.length} collection(s) for ${user}/${collection}`,
    );
  }
}
