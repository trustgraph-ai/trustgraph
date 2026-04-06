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
}

export interface AgentResponse {
  answer: string;
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
