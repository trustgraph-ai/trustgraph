/**
 * Message types for service communication.
 *
 * Python reference: trustgraph-base/trustgraph/schema/services/
 */

import type { TgError, Triple, Term, RowSchema } from "./primitives.js";

// Text completion
export interface TextCompletionRequest {
  system: string;
  prompt: string;
  model?: string;
  temperature?: number;
  streaming?: boolean;
}

export interface TextCompletionResponse {
  response: string;
  model?: string;
  inToken?: number;
  outToken?: number;
  error?: TgError;
  endOfStream?: boolean;
}

// Embeddings
export interface EmbeddingsRequest {
  text: string[];
  model?: string;
}

export interface EmbeddingsResponse {
  vectors: number[][];
  error?: TgError;
}

// Graph RAG
export interface GraphRagRequest {
  query: string;
  collection?: string;
  entityLimit?: number;
  tripleLimit?: number;
  maxSubgraphSize?: number;
  maxPathLength?: number;
  streaming?: boolean;
}

export interface GraphRagResponse {
  response: string;
  error?: TgError;
  endOfStream?: boolean;
}

// Document RAG
export interface DocumentRagRequest {
  query: string;
  collection?: string;
  streaming?: boolean;
}

export interface DocumentRagResponse {
  response: string;
  error?: TgError;
  endOfStream?: boolean;
}

// Agent
export interface AgentRequest {
  question: string;
  collection?: string;
  streaming?: boolean;
  group?: string[];
  state?: string;
}

export interface AgentResponse {
  /** Streaming chunk type */
  chunk_type?: "thought" | "observation" | "answer" | "error";
  content?: string;
  end_of_message?: boolean;
  end_of_dialog?: boolean;
  /** Legacy non-streaming fields */
  answer?: string;
  error?: TgError;
  endOfStream?: boolean;
  endOfSession?: boolean;
}

// Triples query
export interface TriplesQueryRequest {
  s?: Term;
  p?: Term;
  o?: Term;
  collection?: string;
  limit?: number;
}

export interface TriplesQueryResponse {
  triples: Triple[];
  error?: TgError;
}

// Graph embeddings query
export interface GraphEmbeddingsRequest {
  vectors: number[][];
  limit?: number;
  collection?: string;
}

export interface GraphEmbeddingsResponse {
  entities: Term[];
  error?: TgError;
}

// Document embeddings query
export interface DocumentEmbeddingsRequest {
  vectors: number[][];
  limit?: number;
  collection?: string;
}

export interface DocumentEmbeddingsResponse {
  chunks: Array<{ chunkId: string; score: number }>;
  error?: TgError;
}

// Config
export type ConfigOperation = "get" | "list" | "delete" | "put" | "config";

export interface ConfigRequest {
  operation: ConfigOperation;
  keys?: string[];
  values?: Record<string, unknown>;
}

export interface ConfigResponse {
  version?: number;
  values?: Record<string, unknown>;
  directory?: string[];
  config?: Record<string, unknown>;
  error?: TgError;
}

// Prompt
export interface PromptRequest {
  name: string;
  variables?: Record<string, string>;
}

export interface PromptResponse {
  system: string;
  prompt: string;
  error?: TgError;
}

// ---------- Pipeline types ----------

export interface PipelineMetadata {
  id: string;
  root: string;
  user: string;
  collection: string;
}

/** Document message — triggers the decode pipeline for a librarian document. */
export interface Document {
  metadata: PipelineMetadata;
  documentId: string;
}

export interface TextDocument {
  metadata: PipelineMetadata;
  text: string;
  documentId: string;
}

export interface Chunk {
  metadata: PipelineMetadata;
  chunk: string;
  documentId: string;
}

export interface EntityContext {
  entity: Term;
  context: string;
  chunkId: string;
}

export interface EntityContexts {
  metadata: PipelineMetadata;
  entities: EntityContext[];
}

export interface Triples {
  metadata: PipelineMetadata;
  triples: Triple[];
}

// ---------- Document metadata ----------

export interface DocumentMetadata {
  id: string;
  time: number;
  kind: string;
  title: string;
  comments: string;
  user: string;
  tags: string[];
  parentId?: string;
  documentType: string; // "source" | "page" | "chunk" | "extracted"
  metadata?: Triple[];
}

export interface ProcessingMetadata {
  id: string;
  documentId: string;
  time: number;
  flow: string;
  user: string;
  collection: string;
  tags: string[];
}

// ---------- Librarian ----------

export type LibrarianOperation =
  | "add-document"
  | "remove-document"
  | "list-documents"
  | "get-document-metadata"
  | "get-document-content"
  | "add-child-document"
  | "list-children"
  | "add-processing"
  | "remove-processing"
  | "list-processing";

export interface LibrarianRequest {
  operation: LibrarianOperation;
  documentId?: string;
  processingId?: string;
  documentMetadata?: DocumentMetadata;
  processingMetadata?: ProcessingMetadata;
  content?: string; // base64
  user?: string;
  collection?: string;
}

export interface LibrarianResponse {
  error?: TgError;
  documentMetadata?: DocumentMetadata;
  content?: string; // base64
  documents?: DocumentMetadata[];
  processing?: ProcessingMetadata[];
}

// ---------- Knowledge core ----------

export type KnowledgeOperation =
  | "list-kg-cores"
  | "get-kg-core"
  | "delete-kg-core"
  | "put-kg-core"
  | "load-kg-core";

export interface KnowledgeRequest {
  operation: KnowledgeOperation;
  user?: string;
  id?: string;
  flow?: string;
  collection?: string;
  triples?: Triple[];
  graphEmbeddings?: { entity: Term; vectors: number[][] }[];
}

export interface KnowledgeResponse {
  error?: TgError;
  ids?: string[];
  eos?: boolean;
  triples?: Triple[];
  graphEmbeddings?: { entity: Term; vectors: number[][] }[];
}

// ---------- Collection management ----------

export type CollectionOperation =
  | "list-collections"
  | "update-collection"
  | "delete-collection";

export interface CollectionManagementRequest {
  operation: CollectionOperation;
  user?: string;
  collection?: string;
  name?: string;
  description?: string;
  tags?: string[];
}

export interface CollectionManagementResponse {
  error?: TgError;
  collections?: { user: string; collection: string; name: string; description: string; tags: string[] }[];
}

// ---------- Flow management ----------

// Flow request/response use kebab-case wire format to match the client.
// Access fields via bracket notation: request["flow-id"]
export interface FlowRequest {
  operation: string;
  [key: string]: unknown;
}

export interface FlowResponse {
  error?: TgError;
  [key: string]: unknown;
}
