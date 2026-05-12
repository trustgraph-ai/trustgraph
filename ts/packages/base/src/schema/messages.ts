/**
 * Schema-backed message types for service communication.
 *
 * Python reference: trustgraph-base/trustgraph/schema/services/
 */

import * as S from "effect/Schema";
import { Term, TgError, Triple } from "./primitives.js";

const UnknownRecord = S.Record(S.String, S.Unknown);
const MutableArray = <A extends S.Top>(schema: A) => schema.pipe(S.Array, S.mutable);
const OptionalMutableArray = <A extends S.Top>(schema: A) => schema.pipe(S.Array, S.mutable, S.optionalKey);
const StringArray = MutableArray(S.String);
const NumberArray = MutableArray(S.Number);
const NumberArrays = MutableArray(NumberArray);

// Text completion
export const TextCompletionRequest = S.Struct({
  system: S.String,
  prompt: S.String,
  model: S.optionalKey(S.String),
  temperature: S.optionalKey(S.Number),
  streaming: S.optionalKey(S.Boolean),
});
export type TextCompletionRequest = typeof TextCompletionRequest.Type;

export const TextCompletionResponse = S.Struct({
  response: S.String,
  model: S.optionalKey(S.String),
  inToken: S.optionalKey(S.Number),
  outToken: S.optionalKey(S.Number),
  error: S.optionalKey(TgError),
  endOfStream: S.optionalKey(S.Boolean),
});
export type TextCompletionResponse = typeof TextCompletionResponse.Type;

// Embeddings
export const EmbeddingsRequest = S.Struct({
  text: StringArray,
  model: S.optionalKey(S.String),
});
export type EmbeddingsRequest = typeof EmbeddingsRequest.Type;

export const EmbeddingsResponse = S.Struct({
  vectors: NumberArrays,
  error: S.optionalKey(TgError),
});
export type EmbeddingsResponse = typeof EmbeddingsResponse.Type;

// Graph RAG
export const GraphRagRequest = S.Struct({
  query: S.String,
  collection: S.optionalKey(S.String),
  entityLimit: S.optionalKey(S.Number),
  tripleLimit: S.optionalKey(S.Number),
  maxSubgraphSize: S.optionalKey(S.Number),
  maxPathLength: S.optionalKey(S.Number),
  streaming: S.optionalKey(S.Boolean),
});
export type GraphRagRequest = typeof GraphRagRequest.Type;

export const GraphRagResponse = S.StructWithRest(
  S.Struct({
    response: S.String,
    error: S.optionalKey(TgError),
    endOfStream: S.optionalKey(S.Boolean),
    message_type: S.optionalKey(S.Union([S.Literal("chunk"), S.Literal("explain")])),
    explain_id: S.optionalKey(S.String),
    explain_triples: OptionalMutableArray(Triple),
  }),
  [UnknownRecord],
);
export type GraphRagResponse = typeof GraphRagResponse.Type;

// Document RAG
export const DocumentRagRequest = S.Struct({
  query: S.String,
  collection: S.optionalKey(S.String),
  streaming: S.optionalKey(S.Boolean),
});
export type DocumentRagRequest = typeof DocumentRagRequest.Type;

export const DocumentRagResponse = S.Struct({
  response: S.String,
  error: S.optionalKey(TgError),
  endOfStream: S.optionalKey(S.Boolean),
});
export type DocumentRagResponse = typeof DocumentRagResponse.Type;

// Agent
export const AgentRequest = S.Struct({
  question: S.String,
  collection: S.optionalKey(S.String),
  streaming: S.optionalKey(S.Boolean),
  group: S.optionalKey(StringArray),
  state: S.optionalKey(S.String),
});
export type AgentRequest = typeof AgentRequest.Type;

export const AgentResponse = S.Struct({
  chunk_type: S.optionalKey(S.Union([
    S.Literal("thought"),
    S.Literal("observation"),
    S.Literal("answer"),
    S.Literal("error"),
    S.Literal("explain"),
  ])),
  content: S.optionalKey(S.String),
  end_of_message: S.optionalKey(S.Boolean),
  end_of_dialog: S.optionalKey(S.Boolean),
  answer: S.optionalKey(S.String),
  error: S.optionalKey(TgError),
  endOfStream: S.optionalKey(S.Boolean),
  endOfSession: S.optionalKey(S.Boolean),
  explain_id: S.optionalKey(S.String),
  explain_graph: S.optionalKey(S.String),
  explain_triples: OptionalMutableArray(S.Unknown),
  message_type: S.optionalKey(S.String),
});
export type AgentResponse = typeof AgentResponse.Type;

// Triples query
export const TriplesQueryRequest = S.Struct({
  s: S.optionalKey(Term),
  p: S.optionalKey(Term),
  o: S.optionalKey(Term),
  collection: S.optionalKey(S.String),
  limit: S.optionalKey(S.Number),
});
export type TriplesQueryRequest = typeof TriplesQueryRequest.Type;

export const TriplesQueryResponse = S.Struct({
  triples: MutableArray(Triple),
  error: S.optionalKey(TgError),
});
export type TriplesQueryResponse = typeof TriplesQueryResponse.Type;

// Graph embeddings query
export const GraphEmbeddingsRequest = S.Struct({
  vectors: NumberArrays,
  user: S.optionalKey(S.String),
  limit: S.optionalKey(S.Number),
  collection: S.optionalKey(S.String),
});
export type GraphEmbeddingsRequest = typeof GraphEmbeddingsRequest.Type;

export const GraphEmbeddingsResponse = S.Struct({
  entities: MutableArray(Term),
  error: S.optionalKey(TgError),
});
export type GraphEmbeddingsResponse = typeof GraphEmbeddingsResponse.Type;

// Document embeddings query
export const DocumentEmbeddingsRequest = S.Struct({
  vectors: NumberArrays,
  limit: S.optionalKey(S.Number),
  user: S.optionalKey(S.String),
  collection: S.optionalKey(S.String),
});
export type DocumentEmbeddingsRequest = typeof DocumentEmbeddingsRequest.Type;

const DocumentEmbeddingChunk = S.Struct({
  chunkId: S.String,
  score: S.Number,
  content: S.optionalKey(S.String),
});

export const DocumentEmbeddingsResponse = S.Struct({
  chunks: MutableArray(DocumentEmbeddingChunk),
  error: S.optionalKey(TgError),
});
export type DocumentEmbeddingsResponse = typeof DocumentEmbeddingsResponse.Type;

// Config
export const ConfigOperation = S.Union([
  S.Literal("get"),
  S.Literal("list"),
  S.Literal("delete"),
  S.Literal("put"),
  S.Literal("config"),
  S.Literal("getvalues"),
]);
export type ConfigOperation = typeof ConfigOperation.Type;

export const ConfigRequest = S.Struct({
  operation: ConfigOperation,
  keys: S.optionalKey(StringArray),
  values: S.optionalKey(UnknownRecord),
  type: S.optionalKey(S.String),
});
export type ConfigRequest = typeof ConfigRequest.Type;

export const ConfigResponse = S.Struct({
  version: S.optionalKey(S.Number),
  values: S.optionalKey(S.Unknown),
  directory: S.optionalKey(StringArray),
  config: S.optionalKey(UnknownRecord),
  error: S.optionalKey(TgError),
});
export type ConfigResponse = typeof ConfigResponse.Type;

// Prompt
export const PromptRequest = S.Struct({
  name: S.String,
  variables: S.optionalKey(S.Record(S.String, S.String)),
});
export type PromptRequest = typeof PromptRequest.Type;

export const PromptResponse = S.Struct({
  system: S.String,
  prompt: S.String,
  error: S.optionalKey(TgError),
});
export type PromptResponse = typeof PromptResponse.Type;

// Pipeline types
export const PipelineMetadata = S.Struct({
  id: S.String,
  root: S.String,
  user: S.String,
  collection: S.String,
});
export type PipelineMetadata = typeof PipelineMetadata.Type;

export const Document = S.Struct({
  metadata: PipelineMetadata,
  documentId: S.String,
});
export type Document = typeof Document.Type;

export const TextDocument = S.Struct({
  metadata: PipelineMetadata,
  text: S.String,
  documentId: S.String,
});
export type TextDocument = typeof TextDocument.Type;

export const Chunk = S.Struct({
  metadata: PipelineMetadata,
  chunk: S.String,
  documentId: S.String,
});
export type Chunk = typeof Chunk.Type;

export const EntityContext = S.Struct({
  entity: Term,
  context: S.String,
  chunkId: S.String,
});
export type EntityContext = typeof EntityContext.Type;

export const EntityContexts = S.Struct({
  metadata: PipelineMetadata,
  entities: MutableArray(EntityContext),
});
export type EntityContexts = typeof EntityContexts.Type;

export const Triples = S.Struct({
  metadata: PipelineMetadata,
  triples: MutableArray(Triple),
});
export type Triples = typeof Triples.Type;

// Document metadata
export const DocumentMetadata = S.Struct({
  id: S.String,
  time: S.Number,
  kind: S.String,
  title: S.String,
  comments: S.String,
  user: S.String,
  tags: StringArray,
  parentId: S.optionalKey(S.String),
  documentType: S.String,
  metadata: OptionalMutableArray(Triple),
});
export type DocumentMetadata = typeof DocumentMetadata.Type;

export const ProcessingMetadata = S.Struct({
  id: S.String,
  documentId: S.String,
  time: S.Number,
  flow: S.String,
  user: S.String,
  collection: S.String,
  tags: StringArray,
});
export type ProcessingMetadata = typeof ProcessingMetadata.Type;

// Librarian
export const LibrarianOperation = S.Literals([
  "add-document",
  "remove-document",
  "list-documents",
  "get-document-metadata",
  "get-document-content",
  "add-child-document",
  "list-children",
  "add-processing",
  "remove-processing",
  "list-processing",
]);
export type LibrarianOperation = typeof LibrarianOperation.Type;

export const LibrarianRequest = S.Struct({
  operation: LibrarianOperation,
  documentId: S.optionalKey(S.String),
  processingId: S.optionalKey(S.String),
  documentMetadata: S.optionalKey(DocumentMetadata),
  processingMetadata: S.optionalKey(ProcessingMetadata),
  content: S.optionalKey(S.String),
  user: S.optionalKey(S.String),
  collection: S.optionalKey(S.String),
});
export type LibrarianRequest = typeof LibrarianRequest.Type;

export const LibrarianResponse = S.Struct({
  error: S.optionalKey(TgError),
  documentMetadata: S.optionalKey(DocumentMetadata),
  content: S.optionalKey(S.String),
  documents: OptionalMutableArray(DocumentMetadata),
  processing: OptionalMutableArray(ProcessingMetadata),
});
export type LibrarianResponse = typeof LibrarianResponse.Type;

// Knowledge core
export const KnowledgeOperation = S.Literals([
  "list-kg-cores",
  "get-kg-core",
  "delete-kg-core",
  "put-kg-core",
  "load-kg-core",
]);
export type KnowledgeOperation = typeof KnowledgeOperation.Type;

const GraphEmbedding = S.Struct({
  entity: Term,
  vectors: NumberArrays,
});

export const KnowledgeRequest = S.Struct({
  operation: KnowledgeOperation,
  user: S.optionalKey(S.String),
  id: S.optionalKey(S.String),
  flow: S.optionalKey(S.String),
  collection: S.optionalKey(S.String),
  triples: OptionalMutableArray(Triple),
  graphEmbeddings: OptionalMutableArray(GraphEmbedding),
});
export type KnowledgeRequest = typeof KnowledgeRequest.Type;

export const KnowledgeResponse = S.Struct({
  error: S.optionalKey(TgError),
  ids: S.optionalKey(StringArray),
  eos: S.optionalKey(S.Boolean),
  triples: OptionalMutableArray(Triple),
  graphEmbeddings: OptionalMutableArray(GraphEmbedding),
});
export type KnowledgeResponse = typeof KnowledgeResponse.Type;

// Collection management
export const CollectionOperation = S.Literals([
  "list-collections",
  "update-collection",
  "delete-collection",
]);
export type CollectionOperation = typeof CollectionOperation.Type;

const CollectionEntry = S.Struct({
  user: S.String,
  collection: S.String,
  name: S.String,
  description: S.String,
  tags: StringArray,
});

export const CollectionManagementRequest = S.Struct({
  operation: CollectionOperation,
  user: S.optionalKey(S.String),
  collection: S.optionalKey(S.String),
  name: S.optionalKey(S.String),
  description: S.optionalKey(S.String),
  tags: S.optionalKey(StringArray),
});
export type CollectionManagementRequest = typeof CollectionManagementRequest.Type;

export const CollectionManagementResponse = S.Struct({
  error: S.optionalKey(TgError),
  collections: OptionalMutableArray(CollectionEntry),
});
export type CollectionManagementResponse = typeof CollectionManagementResponse.Type;

// Tool invocation (MCP tools)
export const ToolRequest = S.Struct({
  name: S.String,
  parameters: S.String,
});
export type ToolRequest = typeof ToolRequest.Type;

export const ToolResponse = S.Struct({
  error: S.optionalKey(TgError),
  text: S.optionalKey(S.String),
  object: S.optionalKey(S.String),
});
export type ToolResponse = typeof ToolResponse.Type;

// Flow management
export const FlowRequest = S.StructWithRest(
  S.Struct({
    operation: S.String,
  }),
  [UnknownRecord],
);
export type FlowRequest = typeof FlowRequest.Type;

export const FlowResponse = S.StructWithRest(
  S.Struct({
    error: S.optionalKey(TgError),
  }),
  [UnknownRecord],
);
export type FlowResponse = typeof FlowResponse.Type;

export const ServiceMessageSchemas = {
  TextCompletionRequest,
  TextCompletionResponse,
  EmbeddingsRequest,
  EmbeddingsResponse,
  GraphRagRequest,
  GraphRagResponse,
  DocumentRagRequest,
  DocumentRagResponse,
  AgentRequest,
  AgentResponse,
  TriplesQueryRequest,
  TriplesQueryResponse,
  GraphEmbeddingsRequest,
  GraphEmbeddingsResponse,
  DocumentEmbeddingsRequest,
  DocumentEmbeddingsResponse,
  ConfigRequest,
  ConfigResponse,
  PromptRequest,
  PromptResponse,
  LibrarianRequest,
  LibrarianResponse,
  KnowledgeRequest,
  KnowledgeResponse,
  CollectionManagementRequest,
  CollectionManagementResponse,
  ToolRequest,
  ToolResponse,
  FlowRequest,
  FlowResponse,
} as const;
