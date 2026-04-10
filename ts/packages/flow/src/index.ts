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

// ReAct agent
export { AgentService } from "./agent/react/index.js";

// MCP tool service
export { McpToolService } from "./agent/mcp-tool/index.js";

// Tool filtering
export { filterToolsByGroupAndState, getNextState } from "./agent/tool-filter.js";

// Librarian service
export { LibrarianService, type LibrarianServiceConfig } from "./librarian/service.js";
export { CollectionManager, type CollectionEntry } from "./librarian/collection-manager.js";

// Chunking service
export { recursiveSplit } from "./chunking/recursive-splitter.js";
export { ChunkingService } from "./chunking/service.js";

// Knowledge extraction service
export { KnowledgeExtractService } from "./extract/knowledge-extract.js";

// Knowledge core service
export { KnowledgeCoreService, type KnowledgeCoreServiceConfig } from "./cores/service.js";

// Ollama text completion
export { OllamaProcessor } from "./model/text-completion/ollama.js";

// PDF decoder
export { PdfDecoderService } from "./decoding/pdf-decoder.js";

// Query services (FlowProcessor wrappers)
export { TriplesQueryService } from "./query/triples/falkordb-service.js";
export { GraphEmbeddingsQueryService } from "./query/embeddings/qdrant-graph-service.js";
export { DocEmbeddingsQueryService } from "./query/embeddings/qdrant-doc-service.js";

// Retrieval services (FlowProcessor wrappers)
export { GraphRagService } from "./retrieval/graph-rag-service.js";
export { DocumentRagService } from "./retrieval/document-rag-service.js";

// Flow manager service
export { FlowManagerService } from "./flow-manager/service.js";

// Azure OpenAI text completion
export { AzureOpenAIProcessor } from "./model/text-completion/azure-openai.js";

// OpenAI-compatible text completion
export { OpenAICompatibleProcessor } from "./model/text-completion/openai-compatible.js";

// Mistral text completion
export { MistralProcessor } from "./model/text-completion/mistral.js";
