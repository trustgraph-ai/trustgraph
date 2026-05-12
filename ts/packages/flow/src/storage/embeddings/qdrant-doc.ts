/**
 * Qdrant document embeddings write service.
 *
 * Stores document chunk embeddings in Qdrant for later similarity search.
 * Collection naming: d_{user}_{collection}_{dimension}
 * Collections are lazily created on first write with cosine distance.
 *
 * Python reference: trustgraph-flow/trustgraph/storage/doc_embeddings/qdrant/write.py
 */

import { QdrantClient } from "@qdrant/js-client-rest";

export interface QdrantDocEmbeddingsConfig {
  url?: string;
  apiKey?: string;
}

export interface DocEmbeddingChunk {
  chunkId: string;
  vector: number[];
  content?: string;
}

export interface DocEmbeddingsMessage {
  user: string;
  collection: string;
  chunks: DocEmbeddingChunk[];
}

export class QdrantDocEmbeddingsStore {
  private client: QdrantClient;
  private knownCollections = new Set<string>();

  constructor(config: QdrantDocEmbeddingsConfig = {}) {
    const url = config.url ?? process.env.QDRANT_URL ?? "http://localhost:6333";
    const apiKey = config.apiKey ?? process.env.QDRANT_API_KEY;

    this.client = new QdrantClient({
      url,
      ...(apiKey !== undefined && apiKey.length > 0 ? { apiKey } : {}),
    });

    console.log("[QdrantDocEmbeddings] Store initialized");
  }

  private collectionName(user: string, collection: string, dim: number): string {
    return `d_${user}_${collection}_${dim}`;
  }

  private async ensureCollection(name: string, dim: number): Promise<void> {
    if (this.knownCollections.has(name)) return;

    const exists = await this.client.collectionExists(name);
    if (!exists.exists) {
      console.log(`[QdrantDocEmbeddings] Creating collection ${name} (dim=${dim})`);
      await this.client.createCollection(name, {
        vectors: { size: dim, distance: "Cosine" },
      });
    }

    this.knownCollections.add(name);
  }

  async store(message: DocEmbeddingsMessage): Promise<void> {
    for (const chunk of message.chunks) {
      if (chunk.chunkId.length === 0) continue;
      if (chunk.vector.length === 0) continue;

      const dim = chunk.vector.length;
      const name = this.collectionName(message.user, message.collection, dim);

      await this.ensureCollection(name, dim);

      await this.client.upsert(name, {
        points: [
          {
            id: crypto.randomUUID(),
            vector: chunk.vector,
            payload: {
              chunk_id: chunk.chunkId,
              ...(chunk.content !== undefined && chunk.content.length > 0
                ? { content: chunk.content }
                : {}),
            },
          },
        ],
      });
    }
  }

  async deleteCollection(user: string, collection: string): Promise<void> {
    const prefix = `d_${user}_${collection}_`;

    const allCollections = await this.client.getCollections();
    const matching = allCollections.collections.filter((c) =>
      c.name.startsWith(prefix),
    );

    if (matching.length === 0) {
      console.log(`[QdrantDocEmbeddings] No collections matching prefix ${prefix}`);
      return;
    }

    for (const coll of matching) {
      await this.client.deleteCollection(coll.name);
      this.knownCollections.delete(coll.name);
      console.log(`[QdrantDocEmbeddings] Deleted collection: ${coll.name}`);
    }

    console.log(
      `[QdrantDocEmbeddings] Deleted ${matching.length} collection(s) for ${user}/${collection}`,
    );
  }
}
