import { Schema as S } from "effect";
import { Term, Triple } from "./Triple.js";

export type Request = object;
export type Response = object;
export type WireError = object | string;

const UnknownRecord = S.Record(S.String, S.Unknown);
const WireErrorValue = S.Union([S.String, UnknownRecord]);
const TypedMessageError = S.Struct({
  message: S.String,
  type: S.optionalKey(S.String),
});
const OptionalMessageError = S.Struct({
  message: S.optionalKey(S.String),
});

const NumberArray = S.Array(S.Finite).pipe(S.mutable);
const NumberMatrix = S.Array(NumberArray).pipe(S.mutable);
const TripleArray = S.Array(Triple).pipe(S.mutable);
const StringArray = S.Array(S.String).pipe(S.mutable);

export class ResponseError extends S.Class<ResponseError>("ResponseError")({
  type: S.optionalKey(S.String),
  message: S.String,
}, { description: "TrustGraph response error payload." }) {}

export class RequestMessage extends S.Class<RequestMessage>("RequestMessage")({
  id: S.String,
  service: S.String,
  request: UnknownRecord,
  flow: S.optionalKey(S.String),
}, { description: "Envelope sent to a TrustGraph service." }) {}

export class ApiResponse extends S.Class<ApiResponse>("ApiResponse")({
  id: S.String,
  response: UnknownRecord,
}, { description: "Envelope returned from a TrustGraph service." }) {}

export class Metadata extends S.Class<Metadata>("Metadata")({
  id: S.optionalKey(S.String),
  metadata: S.optionalKey(TripleArray),
  user: S.optionalKey(S.String),
  collection: S.optionalKey(S.String),
}, { description: "Shared request metadata for TrustGraph wire messages." }) {}

export class EntityEmbeddings extends S.Class<EntityEmbeddings>("EntityEmbeddings")({
  entity: S.optionalKey(Term),
  vectors: S.optionalKey(NumberMatrix),
}, { description: "Embedding vectors associated with a graph entity." }) {}

export class GraphEmbeddings extends S.Class<GraphEmbeddings>("GraphEmbeddings")({
  metadata: S.optionalKey(Metadata),
  entities: S.optionalKey(S.Array(EntityEmbeddings).pipe(S.mutable)),
}, { description: "Graph embedding payload grouped by entity." }) {}

export class TextCompletionRequest extends S.Class<TextCompletionRequest>("TextCompletionRequest")({
  system: S.String,
  prompt: S.String,
  streaming: S.optionalKey(S.Boolean),
}, { description: "Text-completion request payload." }) {}

export class TextCompletionResponse extends S.Class<TextCompletionResponse>("TextCompletionResponse")({
  response: S.String,
  end_of_stream: S.optionalKey(S.Boolean),
  error: S.optionalKey(TypedMessageError),
  in_token: S.optionalKey(S.Finite),
  out_token: S.optionalKey(S.Finite),
  model: S.optionalKey(S.String),
}, { description: "Text-completion response payload." }) {}

export class GraphRagRequest extends S.Class<GraphRagRequest>("GraphRagRequest")({
  query: S.String,
  user: S.optionalKey(S.String),
  collection: S.optionalKey(S.String),
  "entity-limit": S.optionalKey(S.Finite),
  "triple-limit": S.optionalKey(S.Finite),
  "max-subgraph-size": S.optionalKey(S.Finite),
  "max-path-length": S.optionalKey(S.Finite),
  streaming: S.optionalKey(S.Boolean),
}, { description: "Graph RAG request payload." }) {}

export class GraphRagResponse extends S.Class<GraphRagResponse>("GraphRagResponse")({
  response: S.String,
  chunk: S.optionalKey(S.String),
  end_of_stream: S.optionalKey(S.Boolean),
  endOfStream: S.optionalKey(S.Boolean),
  error: S.optionalKey(TypedMessageError),
  in_token: S.optionalKey(S.Finite),
  out_token: S.optionalKey(S.Finite),
  model: S.optionalKey(S.String),
  message_type: S.optionalKey(S.Literals(["chunk", "explain"])),
  explain_id: S.optionalKey(S.String),
  explain_graph: S.optionalKey(S.String),
  explain_triples: S.optionalKey(S.Array(S.Unknown).pipe(S.mutable)),
  end_of_session: S.optionalKey(S.Boolean),
}, { description: "Graph RAG response payload." }) {}

export class DocumentRagRequest extends S.Class<DocumentRagRequest>("DocumentRagRequest")({
  query: S.String,
  user: S.optionalKey(S.String),
  collection: S.optionalKey(S.String),
  "doc-limit": S.optionalKey(S.Finite),
  streaming: S.optionalKey(S.Boolean),
}, { description: "Document RAG request payload." }) {}

export class DocumentRagResponse extends S.Class<DocumentRagResponse>("DocumentRagResponse")({
  response: S.String,
  chunk: S.optionalKey(S.String),
  end_of_stream: S.optionalKey(S.Boolean),
  endOfStream: S.optionalKey(S.Boolean),
  error: S.optionalKey(TypedMessageError),
  in_token: S.optionalKey(S.Finite),
  out_token: S.optionalKey(S.Finite),
  model: S.optionalKey(S.String),
  message_type: S.optionalKey(S.Literals(["chunk", "explain"])),
  explain_id: S.optionalKey(S.String),
  explain_graph: S.optionalKey(S.String),
  end_of_session: S.optionalKey(S.Boolean),
}, { description: "Document RAG response payload." }) {}

export class AgentRequest extends S.Class<AgentRequest>("AgentRequest")({
  question: S.String,
  user: S.optionalKey(S.String),
  collection: S.optionalKey(S.String),
  streaming: S.optionalKey(S.Boolean),
}, { description: "Agent request payload." }) {}

export class AgentResponse extends S.Class<AgentResponse>("AgentResponse")({
  chunk_type: S.optionalKey(S.Literals([
    "thought",
    "action",
    "observation",
    "answer",
    "final-answer",
    "explain",
    "error",
  ])),
  content: S.optionalKey(S.String),
  end_of_message: S.optionalKey(S.Boolean),
  end_of_dialog: S.optionalKey(S.Boolean),
  thought: S.optionalKey(S.String),
  observation: S.optionalKey(S.String),
  answer: S.optionalKey(S.String),
  error: S.optionalKey(ResponseError),
  in_token: S.optionalKey(S.Finite),
  out_token: S.optionalKey(S.Finite),
  model: S.optionalKey(S.String),
  message_type: S.optionalKey(S.Literals(["chunk", "explain"])),
  explain_id: S.optionalKey(S.String),
  explain_graph: S.optionalKey(S.String),
  explain_triples: S.optionalKey(S.Array(S.Unknown).pipe(S.mutable)),
}, { description: "Agent response payload." }) {}

export class EmbeddingsRequest extends S.Class<EmbeddingsRequest>("EmbeddingsRequest")({
  texts: StringArray,
}, { description: "Batch embeddings request payload." }) {}

export class EmbeddingsResponse extends S.Class<EmbeddingsResponse>("EmbeddingsResponse")({
  vectors: NumberMatrix,
}, { description: "Batch embeddings response payload." }) {}

export class GraphEmbeddingsQueryRequest extends S.Class<GraphEmbeddingsQueryRequest>("GraphEmbeddingsQueryRequest")({
  vector: NumberArray,
  limit: S.Finite,
  user: S.optionalKey(S.String),
  collection: S.optionalKey(S.String),
}, { description: "Graph embeddings query request payload." }) {}

export class EntityMatch extends S.Class<EntityMatch>("EntityMatch")({
  entity: S.NullOr(Term),
  score: S.Finite,
}, { description: "Scored graph-entity match." }) {}

export class GraphEmbeddingsQueryResponse extends S.Class<GraphEmbeddingsQueryResponse>("GraphEmbeddingsQueryResponse")({
  entities: S.Array(EntityMatch).pipe(S.mutable),
}, { description: "Graph embeddings query response payload." }) {}

export class TriplesQueryRequest extends S.Class<TriplesQueryRequest>("TriplesQueryRequest")({
  s: S.optionalKey(Term),
  p: S.optionalKey(Term),
  o: S.optionalKey(Term),
  g: S.optionalKey(S.String),
  limit: S.Finite,
  user: S.optionalKey(S.String),
  collection: S.optionalKey(S.String),
}, { description: "Triple pattern query request payload." }) {}

export class TriplesQueryResponse extends S.Class<TriplesQueryResponse>("TriplesQueryResponse")({
  triples: TripleArray,
  response: S.optionalKey(TripleArray),
}, { description: "Triple pattern query response payload." }) {}

export class RowsQueryRequest extends S.Class<RowsQueryRequest>("RowsQueryRequest")({
  query: S.String,
  user: S.optionalKey(S.String),
  collection: S.optionalKey(S.String),
  variables: S.optionalKey(UnknownRecord),
  operation_name: S.optionalKey(S.String),
}, { description: "Structured rows GraphQL request payload." }) {}

export class RowsQueryResponse extends S.Class<RowsQueryResponse>("RowsQueryResponse")({
  data: S.optionalKey(UnknownRecord),
  errors: S.optionalKey(S.Array(UnknownRecord).pipe(S.mutable)),
  extensions: S.optionalKey(UnknownRecord),
  values: S.optionalKey(S.Array(S.Unknown).pipe(S.mutable)),
}, { description: "Structured rows GraphQL response payload." }) {}

export class NlpQueryRequest extends S.Class<NlpQueryRequest>("NlpQueryRequest")({
  question: S.String,
  max_results: S.optionalKey(S.Finite),
}, { description: "Natural-language-to-GraphQL request payload." }) {}

export class NlpQueryResponse extends S.Class<NlpQueryResponse>("NlpQueryResponse")({
  graphql_query: S.optionalKey(S.String),
  variables: S.optionalKey(UnknownRecord),
  detected_schemas: S.optionalKey(S.Array(UnknownRecord).pipe(S.mutable)),
  confidence: S.optionalKey(S.Finite),
}, { description: "Natural-language-to-GraphQL response payload." }) {}

export class StructuredQueryRequest extends S.Class<StructuredQueryRequest>("StructuredQueryRequest")({
  question: S.String,
  user: S.optionalKey(S.String),
  collection: S.optionalKey(S.String),
}, { description: "Structured query request payload." }) {}

export class StructuredQueryResponse extends S.Class<StructuredQueryResponse>("StructuredQueryResponse")({
  data: S.optionalKey(UnknownRecord),
  errors: S.optionalKey(S.Array(UnknownRecord).pipe(S.mutable)),
}, { description: "Structured query response payload." }) {}

export class RowEmbeddingsQueryRequest extends S.Class<RowEmbeddingsQueryRequest>("RowEmbeddingsQueryRequest")({
  vector: NumberArray,
  schema_name: S.String,
  user: S.optionalKey(S.String),
  collection: S.optionalKey(S.String),
  index_name: S.optionalKey(S.String),
  limit: S.optionalKey(S.Finite),
}, { description: "Row embeddings query request payload." }) {}

export class RowEmbeddingsMatch extends S.Class<RowEmbeddingsMatch>("RowEmbeddingsMatch")({
  index_name: S.String,
  index_value: StringArray,
  text: S.String,
  score: S.Finite,
}, { description: "Scored row embeddings match." }) {}

export class RowEmbeddingsQueryResponse extends S.Class<RowEmbeddingsQueryResponse>("RowEmbeddingsQueryResponse")({
  matches: S.optionalKey(S.Array(RowEmbeddingsMatch).pipe(S.mutable)),
  error: S.optionalKey(TypedMessageError),
}, { description: "Row embeddings query response payload." }) {}

export class LoadDocumentRequest extends S.Class<LoadDocumentRequest>("LoadDocumentRequest")({
  id: S.optionalKey(S.String),
  data: S.String,
  metadata: S.optionalKey(TripleArray),
}, { description: "Flow-scoped document load request payload." }) {}

export type LoadDocumentResponse = void;

export class LoadTextRequest extends S.Class<LoadTextRequest>("LoadTextRequest")({
  id: S.optionalKey(S.String),
  text: S.String,
  charset: S.optionalKey(S.String),
  metadata: S.optionalKey(TripleArray),
}, { description: "Flow-scoped text load request payload." }) {}

export type LoadTextResponse = void;

export class DocumentMetadata extends S.Class<DocumentMetadata>("DocumentMetadata")({
  id: S.optionalKey(S.String),
  time: S.optionalKey(S.Finite),
  kind: S.optionalKey(S.String),
  title: S.optionalKey(S.String),
  comments: S.optionalKey(S.String),
  metadata: S.optionalKey(TripleArray),
  user: S.optionalKey(S.String),
  tags: S.optionalKey(StringArray),
  parentId: S.optionalKey(S.String),
  documentType: S.optionalKey(S.String),
  "parent-id": S.optionalKey(S.String),
  "document-type": S.optionalKey(S.String),
}, { description: "Library document metadata payload." }) {}

export class ProcessingMetadata extends S.Class<ProcessingMetadata>("ProcessingMetadata")({
  id: S.optionalKey(S.String),
  "document-id": S.optionalKey(S.String),
  documentId: S.optionalKey(S.String),
  time: S.optionalKey(S.Finite),
  flow: S.optionalKey(S.String),
  user: S.optionalKey(S.String),
  collection: S.optionalKey(S.String),
  tags: S.optionalKey(StringArray),
}, { description: "Library processing metadata payload." }) {}

export class LibraryRequest extends S.Class<LibraryRequest>("LibraryRequest")({
  operation: S.String,
  documentId: S.optionalKey(S.String),
  "document-id": S.optionalKey(S.String),
  processingId: S.optionalKey(S.String),
  "processing-id": S.optionalKey(S.String),
  "document-metadata": S.optionalKey(DocumentMetadata),
  documentMetadata: S.optionalKey(DocumentMetadata),
  "processing-metadata": S.optionalKey(ProcessingMetadata),
  content: S.optionalKey(S.String),
  user: S.optionalKey(S.String),
  collection: S.optionalKey(S.String),
  metadata: S.optionalKey(TripleArray),
  id: S.optionalKey(S.String),
  flow: S.optionalKey(S.String),
}, { description: "Library service request payload." }) {}

export class LibraryResponse extends S.Class<LibraryResponse>("LibraryResponse")({
  error: S.optionalKey(WireErrorValue),
  "document-metadata": S.optionalKey(DocumentMetadata),
  documentMetadata: S.optionalKey(DocumentMetadata),
  content: S.optionalKey(S.String),
  "document-metadatas": S.optionalKey(S.Array(DocumentMetadata).pipe(S.mutable)),
  documents: S.optionalKey(S.Array(DocumentMetadata).pipe(S.mutable)),
  "processing-metadata": S.optionalKey(ProcessingMetadata),
  "processing-metadatas": S.optionalKey(S.Array(ProcessingMetadata).pipe(S.mutable)),
  processing: S.optionalKey(S.Array(ProcessingMetadata).pipe(S.mutable)),
}, { description: "Library service response payload." }) {}

export class KnowledgeRequest extends S.Class<KnowledgeRequest>("KnowledgeRequest")({
  operation: S.String,
  user: S.optionalKey(S.String),
  id: S.optionalKey(S.String),
  flow: S.optionalKey(S.String),
  collection: S.optionalKey(S.String),
  triples: S.optionalKey(TripleArray),
  "graph-embeddings": S.optionalKey(GraphEmbeddings),
  graphEmbeddings: S.optionalKey(GraphEmbeddings),
  "document-embeddings": S.optionalKey(S.Unknown),
  documentEmbeddings: S.optionalKey(S.Unknown),
}, { description: "Knowledge service request payload." }) {}

export class KnowledgeResponse extends S.Class<KnowledgeResponse>("KnowledgeResponse")({
  error: S.optionalKey(WireErrorValue),
  ids: S.optionalKey(StringArray),
  eos: S.optionalKey(S.Boolean),
  triples: S.optionalKey(TripleArray),
  "graph-embeddings": S.optionalKey(GraphEmbeddings),
  graphEmbeddings: S.optionalKey(GraphEmbeddings),
  "document-embeddings": S.optionalKey(S.Unknown),
  documentEmbeddings: S.optionalKey(S.Unknown),
}, { description: "Knowledge service response payload." }) {}

export class FlowRequest extends S.Class<FlowRequest>("FlowRequest")({
  operation: S.String,
  "blueprint-name": S.optionalKey(S.String),
  "blueprint-definition": S.optionalKey(S.String),
  description: S.optionalKey(S.String),
  "flow-id": S.optionalKey(S.String),
  parameters: S.optionalKey(UnknownRecord),
  user: S.optionalKey(S.String),
}, { description: "Flow service request payload." }) {}

export class FlowResponse extends S.Class<FlowResponse>("FlowResponse")({
  "blueprint-names": S.optionalKey(StringArray),
  "flow-ids": S.optionalKey(StringArray),
  ids: S.optionalKey(StringArray),
  flow: S.optionalKey(S.String),
  "blueprint-definition": S.optionalKey(S.String),
  description: S.optionalKey(S.String),
  error: S.optionalKey(S.Union([OptionalMessageError, WireErrorValue])),
}, { description: "Flow service response payload." }) {}

export class PromptRequest extends S.Class<PromptRequest>("PromptRequest")({
  id: S.String,
  terms: UnknownRecord,
  streaming: S.optionalKey(S.Boolean),
}, { description: "Prompt rendering request payload." }) {}

export class PromptResponse extends S.Class<PromptResponse>("PromptResponse")({
  text: S.String,
  end_of_stream: S.optionalKey(S.Boolean),
  error: S.optionalKey(TypedMessageError),
  in_token: S.optionalKey(S.Finite),
  out_token: S.optionalKey(S.Finite),
  model: S.optionalKey(S.String),
}, { description: "Prompt rendering response payload." }) {}

export type ConfigRequest = object;
export type ConfigResponse = object;

export class ChunkedUploadDocumentMetadata extends S.Class<ChunkedUploadDocumentMetadata>("ChunkedUploadDocumentMetadata")({
  id: S.String,
  time: S.Finite,
  kind: S.String,
  title: S.String,
  comments: S.optionalKey(S.String),
  metadata: S.optionalKey(TripleArray),
  user: S.String,
  collection: S.optionalKey(S.String),
  tags: S.optionalKey(StringArray),
}, { description: "Document metadata used to begin a chunked upload." }) {}

export class BeginUploadRequest extends S.Class<BeginUploadRequest>("BeginUploadRequest")({
  operation: S.Literal("begin-upload"),
  "document-metadata": S.optionalKey(ChunkedUploadDocumentMetadata),
  documentMetadata: S.optionalKey(ChunkedUploadDocumentMetadata),
  "total-size": S.Finite,
  "chunk-size": S.optionalKey(S.Finite),
}, { description: "Chunked upload begin request payload." }) {}

export class BeginUploadResponse extends S.Class<BeginUploadResponse>("BeginUploadResponse")({
  "upload-id": S.String,
  "chunk-size": S.Finite,
  "total-chunks": S.Finite,
  error: S.optionalKey(ResponseError),
}, { description: "Chunked upload begin response payload." }) {}

export class UploadChunkRequest extends S.Class<UploadChunkRequest>("UploadChunkRequest")({
  operation: S.Literal("upload-chunk"),
  "upload-id": S.String,
  "chunk-index": S.Finite,
  content: S.String,
  user: S.String,
}, { description: "Chunked upload chunk request payload." }) {}

export class UploadChunkResponse extends S.Class<UploadChunkResponse>("UploadChunkResponse")({
  "upload-id": S.String,
  "chunk-index": S.Finite,
  "chunks-received": S.Finite,
  "total-chunks": S.Finite,
  "bytes-received": S.Finite,
  "total-bytes": S.Finite,
  error: S.optionalKey(ResponseError),
}, { description: "Chunked upload chunk response payload." }) {}

export class CompleteUploadRequest extends S.Class<CompleteUploadRequest>("CompleteUploadRequest")({
  operation: S.Literal("complete-upload"),
  "upload-id": S.String,
  user: S.String,
}, { description: "Chunked upload completion request payload." }) {}

export class CompleteUploadResponse extends S.Class<CompleteUploadResponse>("CompleteUploadResponse")({
  "document-id": S.String,
  "object-id": S.String,
  error: S.optionalKey(ResponseError),
}, { description: "Chunked upload completion response payload." }) {}

export class GetUploadStatusRequest extends S.Class<GetUploadStatusRequest>("GetUploadStatusRequest")({
  operation: S.Literal("get-upload-status"),
  "upload-id": S.String,
  user: S.String,
}, { description: "Chunked upload status request payload." }) {}

export class GetUploadStatusResponse extends S.Class<GetUploadStatusResponse>("GetUploadStatusResponse")({
  "upload-id": S.String,
  "upload-state": S.Literals(["in-progress", "completed", "expired"]),
  "chunks-received": S.Finite,
  "total-chunks": S.Finite,
  "received-chunks": S.Array(S.Finite).pipe(S.mutable),
  "missing-chunks": S.Array(S.Finite).pipe(S.mutable),
  "bytes-received": S.Finite,
  "total-bytes": S.Finite,
  error: S.optionalKey(ResponseError),
}, { description: "Chunked upload status response payload." }) {}

export class AbortUploadRequest extends S.Class<AbortUploadRequest>("AbortUploadRequest")({
  operation: S.Literal("abort-upload"),
  "upload-id": S.String,
  user: S.String,
}, { description: "Chunked upload abort request payload." }) {}

export class AbortUploadResponse extends S.Class<AbortUploadResponse>("AbortUploadResponse")({
  error: S.optionalKey(ResponseError),
}, { description: "Chunked upload abort response payload." }) {}

export class ListUploadsRequest extends S.Class<ListUploadsRequest>("ListUploadsRequest")({
  operation: S.Literal("list-uploads"),
  user: S.String,
}, { description: "Pending uploads list request payload." }) {}

export class UploadSession extends S.Class<UploadSession>("UploadSession")({
  "upload-id": S.String,
  "document-id": S.String,
  "document-metadata-json": S.String,
  "total-size": S.Finite,
  "chunk-size": S.Finite,
  "total-chunks": S.Finite,
  "chunks-received": S.Finite,
  "created-at": S.String,
}, { description: "Pending upload session payload." }) {}

export class ListUploadsResponse extends S.Class<ListUploadsResponse>("ListUploadsResponse")({
  "upload-sessions": S.Array(UploadSession).pipe(S.mutable),
  error: S.optionalKey(ResponseError),
}, { description: "Pending uploads list response payload." }) {}

export class StreamDocumentRequest extends S.Class<StreamDocumentRequest>("StreamDocumentRequest")({
  operation: S.Literal("stream-document"),
  "document-id": S.String,
  "chunk-size": S.optionalKey(S.Finite),
  user: S.String,
}, { description: "Document chunk stream request payload." }) {}

export class StreamDocumentResponse extends S.Class<StreamDocumentResponse>("StreamDocumentResponse")({
  content: S.String,
  "chunk-index": S.Finite,
  "total-chunks": S.Finite,
  error: S.optionalKey(ResponseError),
}, { description: "Document chunk stream response payload." }) {}
