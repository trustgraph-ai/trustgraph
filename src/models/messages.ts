import { Triple, Term } from "./Triple";

// FIXME: Better types?
export type Request = object;
export type Response = object;
export type Error = object | string;

export interface ResponseError {
  type?: string;
  message: string;
}

export interface RequestMessage {
  id: string;
  service: string;
  request: Request;
  flow?: string;
}

export interface ApiResponse {
  id: string;
  response: Response;
}

export interface Metadata {
  id?: string;
  metadata?: Triple[];
  user?: string;
  collection?: string;
}

export interface EntityEmbeddings {
  entity?: Term;
  vectors?: number[][];
}

export interface GraphEmbeddings {
  metadata?: Metadata;
  entities?: EntityEmbeddings[];
}

export interface TextCompletionRequest {
  system: string;
  prompt: string;
  streaming?: boolean;
}

export interface TextCompletionResponse {
  response: string;
  // Streaming fields
  end_of_stream?: boolean;
  error?: {
    message: string;
    type?: string;
  };
  // Token usage (appears in final message)
  in_token?: number;
  out_token?: number;
  model?: string;
}

export interface GraphRagRequest {
  query: string;
  user?: string;
  collection?: string;
  "entity-limit"?: number; // Default: 50
  "triple-limit"?: number; // Default: 30
  "max-subgraph-size"?: number; // Default: 1000
  "max-path-length"?: number; // Default: 2
  streaming?: boolean;
}

export interface GraphRagResponse {
  response: string;
  // Streaming fields
  chunk?: string;
  end_of_stream?: boolean;
  error?: {
    message: string;
    type?: string;
  };
  // Token usage (appears in final message)
  in_token?: number;
  out_token?: number;
  model?: string;
  // Explainability fields
  message_type?: "chunk" | "explain";
  explain_id?: string;
  explain_graph?: string;  // Named graph where explain data is stored (e.g., urn:graph:retrieval)
  end_of_session?: boolean;
}

export interface DocumentRagRequest {
  query: string;
  user?: string;
  collection?: string;
  "doc-limit"?: number; // Default: 20
  streaming?: boolean;
}

export interface DocumentRagResponse {
  response: string;
  // Streaming fields
  chunk?: string;
  end_of_stream?: boolean;
  error?: {
    message: string;
    type?: string;
  };
  // Token usage (appears in final message)
  in_token?: number;
  out_token?: number;
  model?: string;
  // Explainability fields
  message_type?: "chunk" | "explain";
  explain_id?: string;
  explain_graph?: string;
  end_of_session?: boolean;
}

export interface AgentRequest {
  question: string;
  user?: string;
  streaming?: boolean;
}

export interface AgentResponse {
  // Streaming response format (new protocol)
  chunk_type?: "thought" | "action" | "observation" | "answer" | "final-answer" | "explain" | "error";
  content?: string;
  end_of_message?: boolean;
  end_of_dialog?: boolean;

  // Legacy fields for backward compatibility with non-streaming
  thought?: string;
  observation?: string;
  answer?: string;
  error?: ResponseError;

  // Token usage (appears in final message)
  in_token?: number;
  out_token?: number;
  model?: string;

  // Explainability fields
  message_type?: "chunk" | "explain";
  explain_id?: string;
  explain_graph?: string;
}

export interface EmbeddingsRequest {
  texts: string[];
}

export interface EmbeddingsResponse {
  vectors: number[][];  // One vector per input text
}

export interface GraphEmbeddingsQueryRequest {
  vector: number[];  // Single query vector
  limit: number;
  user?: string;
  collection?: string;
}

export interface EntityMatch {
  entity: Term | null;
  score: number;
}

export interface GraphEmbeddingsQueryResponse {
  entities: EntityMatch[];
}

export interface TriplesQueryRequest {
  s?: Term;
  p?: Term;
  o?: Term;
  g?: string;  // Named graph URI filter (plain string, not Term)
  limit: number;
  user?: string;
  collection?: string;
}

export interface TriplesQueryResponse {
  response: Triple[];
}

export interface RowsQueryRequest {
  query: string;
  user?: string;
  collection?: string;
  variables?: Record<string, unknown>;
  operation_name?: string;
}

export interface RowsQueryResponse {
  data?: Record<string, unknown>;
  errors?: Record<string, unknown>[];
  extensions?: Record<string, unknown>;
  values?: unknown[];
}

export interface NlpQueryRequest {
  question: string;
  max_results?: number;
}

export interface NlpQueryResponse {
  graphql_query?: string;
  variables?: Record<string, unknown>;
  detected_schemas?: Record<string, unknown>[];
  confidence?: number;
}

export interface StructuredQueryRequest {
  question: string;
  user?: string;
  collection?: string;
}

export interface StructuredQueryResponse {
  data?: Record<string, unknown>;
  errors?: Record<string, unknown>[];
}

export interface RowEmbeddingsQueryRequest {
  vector: number[];  // Single query vector
  schema_name: string;
  user?: string;
  collection?: string;
  index_name?: string;
  limit?: number;
}

export interface RowEmbeddingsMatch {
  index_name: string;
  index_value: string[];
  text: string;
  score: number;
}

export interface RowEmbeddingsQueryResponse {
  matches?: RowEmbeddingsMatch[];
  error?: {
    message: string;
    type?: string;
  };
}

export interface LoadDocumentRequest {
  id?: string;
  data: string;
  metadata?: Triple[];
}

export type LoadDocumentResponse = void;

export interface LoadTextRequest {
  id?: string;
  text: string;
  charset?: string;
  metadata?: Triple[];
}

export type LoadTextResponse = void;

export interface DocumentMetadata {
  id?: string;
  time?: number;
  kind?: string;
  title?: string;
  comments?: string;
  metadata?: Triple[];
  user?: string;
  tags?: string[];
  "document-type"?: string;
}

export interface ProcessingMetadata {
  id?: string;
  "document-id"?: string;
  time?: number;
  flow?: string;
  user?: string;
  collection?: string;
  tags?: string[];
}

export interface LibraryRequest {
  operation: string;
  "document-id"?: string;
  "processing-id"?: string;
  "document-metadata"?: DocumentMetadata;
  "processing-metadata"?: ProcessingMetadata;
  content?: string;
  user?: string;
  collection?: string;
  metadata?: Triple[];
  id?: string;
  flow?: string;
}

export interface LibraryResponse {
  error: Error;
  "document-metadata"?: DocumentMetadata;
  content?: string;
  "document-metadatas"?: DocumentMetadata[];
  "processing-metadata"?: ProcessingMetadata;
}

export interface KnowledgeRequest {
  operation: string;
  user?: string;
  id?: string;
  flow?: string;
  collection?: string;
  triples?: Triple[];
  "graph-embeddings"?: GraphEmbeddings;
}

export interface KnowledgeResponse {
  error?: Error;
  ids?: string[];
  eos?: boolean;
  triples?: Triple[];
  "graph-embeddings"?: GraphEmbeddings;
}

export interface FlowRequest {
  operation: string;
  "blueprint-name"?: string;
  "blueprint-definition"?: string;
  description?: string;
  "flow-id"?: string;
  parameters?: Record<string, unknown>;
  user?: string;
}

export interface FlowResponse {
  "blueprint-names"?: string[];
  "flow-ids"?: string[];
  ids?: string[];
  flow?: string;
  "blueprint-definition"?: string;
  description?: string;
  error?:
    | {
        message?: string;
      }
    | Error;
}

export interface PromptRequest {
  id: string;
  terms: Record<string, unknown>;
  streaming?: boolean;
}

export interface PromptResponse {
  text: string;
  // Streaming fields
  end_of_stream?: boolean;
  error?: {
    message: string;
    type?: string;
  };
  // Token usage (appears in final message)
  in_token?: number;
  out_token?: number;
  model?: string;
}

export type ConfigRequest = object;
export type ConfigResponse = object;

// Chunked Upload Types

export interface ChunkedUploadDocumentMetadata {
  id: string;
  time: number;
  kind: string;
  title: string;
  comments?: string;
  metadata?: Triple[];
  user: string;
  collection?: string;
  tags?: string[];
}

export interface BeginUploadRequest {
  operation: "begin-upload";
  "document-metadata": ChunkedUploadDocumentMetadata;
  "total-size": number;
  "chunk-size"?: number;
}

export interface BeginUploadResponse {
  "upload-id": string;
  "chunk-size": number;
  "total-chunks": number;
  error?: ResponseError;
}

export interface UploadChunkRequest {
  operation: "upload-chunk";
  "upload-id": string;
  "chunk-index": number;
  content: string;  // base64-encoded
  user: string;
}

export interface UploadChunkResponse {
  "upload-id": string;
  "chunk-index": number;
  "chunks-received": number;
  "total-chunks": number;
  "bytes-received": number;
  "total-bytes": number;
  error?: ResponseError;
}

export interface CompleteUploadRequest {
  operation: "complete-upload";
  "upload-id": string;
  user: string;
}

export interface CompleteUploadResponse {
  "document-id": string;
  "object-id": string;
  error?: ResponseError;
}

export interface GetUploadStatusRequest {
  operation: "get-upload-status";
  "upload-id": string;
  user: string;
}

export interface GetUploadStatusResponse {
  "upload-id": string;
  "upload-state": "in-progress" | "completed" | "expired";
  "chunks-received": number;
  "total-chunks": number;
  "received-chunks": number[];
  "missing-chunks": number[];
  "bytes-received": number;
  "total-bytes": number;
  error?: ResponseError;
}

export interface AbortUploadRequest {
  operation: "abort-upload";
  "upload-id": string;
  user: string;
}

export interface AbortUploadResponse {
  error?: ResponseError;
}

export interface ListUploadsRequest {
  operation: "list-uploads";
  user: string;
}

export interface UploadSession {
  "upload-id": string;
  "document-id": string;
  "document-metadata-json": string;
  "total-size": number;
  "chunk-size": number;
  "total-chunks": number;
  "chunks-received": number;
  "created-at": string;
}

export interface ListUploadsResponse {
  "upload-sessions": UploadSession[];
  error?: ResponseError;
}

export interface StreamDocumentRequest {
  operation: "stream-document";
  "document-id": string;
  "chunk-size"?: number;
  user: string;
}

export interface StreamDocumentResponse {
  content: string;  // base64-encoded chunk
  "chunk-index": number;
  "total-chunks": number;
  error?: ResponseError;
}
