// @trustgraph/flow — processing services

export { createGateway, type GatewayConfig } from "./gateway/index.js";
export { OpenAIProcessor } from "./model/text-completion/openai.js";
export { ClaudeProcessor } from "./model/text-completion/claude.js";
export { GraphRag, type GraphRagConfig, type GraphRagClients } from "./retrieval/graph-rag.js";
export { DocumentRag, type DocumentRagClients } from "./retrieval/document-rag.js";
export { FalkorDBTriplesStore, type FalkorDBConfig } from "./storage/triples/falkordb.js";
export { FalkorDBTriplesQuery, type FalkorDBQueryConfig } from "./query/triples/falkordb.js";

// Qdrant embeddings storage
export {
  QdrantDocEmbeddingsStore,
  type QdrantDocEmbeddingsConfig,
  type DocEmbeddingsMessage,
  type DocEmbeddingChunk,
} from "./storage/embeddings/qdrant-doc.js";
export {
  QdrantGraphEmbeddingsStore,
  type QdrantGraphEmbeddingsConfig,
  type GraphEmbeddingsMessage,
  type GraphEmbeddingEntity,
} from "./storage/embeddings/qdrant-graph.js";

// Qdrant embeddings query
export {
  QdrantDocEmbeddingsQuery,
  type QdrantDocQueryConfig,
  type ChunkMatch,
  type DocEmbeddingsQueryRequest,
} from "./query/embeddings/qdrant-doc.js";
export {
  QdrantGraphEmbeddingsQuery,
  type QdrantGraphQueryConfig,
  type EntityMatch,
  type GraphEmbeddingsQueryRequest,
} from "./query/embeddings/qdrant-graph.js";

// Embeddings services
export { OllamaEmbeddingsProcessor, type OllamaEmbeddingsConfig } from "./embeddings/ollama.js";

// Prompt template service
export { PromptTemplateService, type PromptTemplate, type PromptTemplateConfig } from "./prompt/template.js";

// Config service
export { ConfigService, type ConfigServiceConfig } from "./config/service.js";
