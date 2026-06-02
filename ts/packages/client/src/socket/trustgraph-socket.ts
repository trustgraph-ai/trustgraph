// Import core types and classes for the TrustGraph API
import type { Term, Triple } from "../models/Triple.js";
import {
  EffectRpcClient,
  type DispatchInput,
  type DispatchOptions,
  type RpcConnectionState,
  makeEffectRpcClient,
} from "./effect-rpc-client.js";
import { getDefaultSocketUrl, getRandomValues } from "./websocket-adapter.js";

// Import all message types for different services
import type {
  AgentRequest,
  AgentResponse,
  ConfigRequest,
  ConfigResponse,
  DocumentMetadata,
  DocumentRagRequest,
  DocumentRagResponse,
  EmbeddingsRequest,
  EmbeddingsResponse,
  EntityMatch,
  FlowRequest,
  FlowResponse,
  GraphEmbeddingsQueryRequest,
  GraphEmbeddingsQueryResponse,
  GraphRagRequest,
  GraphRagResponse,
  //  KnowledgeRequest,
  //  KnowledgeResponse,
  LibraryRequest,
  LibraryResponse,
  LoadDocumentRequest,
  LoadDocumentResponse,
  LoadTextRequest,
  LoadTextResponse,
  NlpQueryRequest,
  NlpQueryResponse,
  RowsQueryRequest,
  RowsQueryResponse,
  RowEmbeddingsQueryRequest,
  RowEmbeddingsQueryResponse,
  RowEmbeddingsMatch,
  PromptRequest,
  PromptResponse,
  //  ProcessingMetadata,
  ResponseError,
  StructuredQueryRequest,
  StructuredQueryResponse,
  TextCompletionRequest,
  TextCompletionResponse,
  TriplesQueryRequest,
  TriplesQueryResponse,
  // Chunked upload types
  ChunkedUploadDocumentMetadata,
  BeginUploadRequest,
  BeginUploadResponse,
  UploadChunkRequest,
  UploadChunkResponse,
  CompleteUploadRequest,
  CompleteUploadResponse,
  GetUploadStatusRequest,
  GetUploadStatusResponse,
  AbortUploadRequest,
  AbortUploadResponse,
  ListUploadsRequest,
  ListUploadsResponse,
  UploadSession,
  StreamDocumentRequest,
  StreamDocumentResponse,
  //  EntityEmbeddings,
  //  Error,
  //  GraphEmbedding,
  //  Metadata,
  //  Request,
  //  Response,
} from "../models/messages.js";

// GraphRAG options interface for configurable parameters
export interface GraphRagOptions {
  entityLimit?: number;
  tripleLimit?: number;
  maxSubgraphSize?: number;
  pathLength?: number;
}

// Metadata included in final streaming message
export interface StreamingMetadata {
  in_token?: number;
  out_token?: number;
  model?: string;
}

// Explainability event data
export interface ExplainEvent {
  explainId: string;
  explainGraph: string;  // Named graph where explain data is stored (e.g., urn:graph:retrieval)
  explainTriples?: Triple[];  // Inline subgraph triples (when available)
}

// Configuration constants
const SOCKET_URL = getDefaultSocketUrl(); // WebSocket endpoint path (isomorphic)

function isNonEmptyString(value: string | undefined): value is string {
  return value !== undefined && value.length > 0;
}

function withDefault(value: string | undefined, fallback: string): string {
  return isNonEmptyString(value) ? value : fallback;
}

function toErrorMessage(value: unknown, fallback: string): string {
  if (value instanceof Error) {
    return value.message;
  }
  if (typeof value === "string" && value.length > 0) {
    return value;
  }
  if (value !== null && typeof value === "object" && "message" in value) {
    const message = (value as { message?: unknown }).message;
    if (typeof message === "string" && message.length > 0) {
      return message;
    }
  }
  return fallback;
}

function dispatchOptions(
  timeoutMs: number | undefined,
  retries: number | undefined,
): DispatchOptions {
  const options: DispatchOptions = {};
  if (timeoutMs !== undefined) {
    return retries === undefined ? { timeoutMs } : { timeoutMs, retries };
  }
  if (retries !== undefined) return { retries };
  return options;
}

function streamingMetadataFrom(source: {
  in_token?: number;
  out_token?: number;
  model?: string;
}): StreamingMetadata | undefined {
  const metadata: StreamingMetadata = {};
  let hasMetadata = false;

  if (source.in_token !== undefined) {
    metadata.in_token = source.in_token;
    hasMetadata = true;
  }
  if (source.out_token !== undefined) {
    metadata.out_token = source.out_token;
    hasMetadata = true;
  }
  if (source.model !== undefined) {
    metadata.model = source.model;
    hasMetadata = true;
  }

  return hasMetadata ? metadata : undefined;
}

function throwIfResponseError(error: ResponseError | undefined): void {
  if (error !== undefined) {
    throw new Error(error.message);
  }
}

export interface ConfigValueEntry {
  workspace?: string;
  type?: string;
  key: string;
  value: unknown;
}

function asConfigValues(response: unknown): ConfigValueEntry[] {
  if (response === null || typeof response !== "object") return [];
  const values = (response as { values?: unknown }).values;
  if (!Array.isArray(values)) return [];
  return values.flatMap((value) => {
    if (value === null || typeof value !== "object") return [];
    const item = value as Record<string, unknown>;
    const key = item.key;
    if (typeof key !== "string") return [];
    const entry: ConfigValueEntry = { key, value: item.value };
    if (typeof item.workspace === "string") entry.workspace = item.workspace;
    if (typeof item.type === "string") entry.type = item.type;
    return [entry];
  });
}

function parseConfigJson(value: unknown): unknown {
  if (typeof value !== "string") return value;
  try {
    return JSON.parse(value);
  } catch {
    return value;
  }
}

/**
 * Socket interface defining all available operations for the TrustGraph API
 * This provides a unified interface for various AI/ML and knowledge graph
 * operations
 */
export interface Socket {
  close: () => void;

  // Text completion using AI models
  textCompletion: (system: string, text: string) => Promise<string>;

  // Graph-based Retrieval Augmented Generation
  graphRag: (text: string, options?: GraphRagOptions) => Promise<string>;

  // Agent interaction with streaming callbacks for different phases
  // BREAKING CHANGE: Callbacks now receive (chunk, complete, metadata?) instead of full messages
  agent: (
    question: string,
    think: (chunk: string, complete: boolean, metadata?: StreamingMetadata) => void,
    observe: (chunk: string, complete: boolean, metadata?: StreamingMetadata) => void,
    answer: (chunk: string, complete: boolean, metadata?: StreamingMetadata) => void,
    error: (e: string) => void,
    onExplain?: (event: ExplainEvent) => void,
    collection?: string,
  ) => void;

  // Streaming variants for RAG and completion services
  graphRagStreaming: (
    text: string,
    receiver: (chunk: string, complete: boolean, metadata?: StreamingMetadata) => void,
    onError: (error: string) => void,
    options?: GraphRagOptions,
    collection?: string,
  ) => void;

  documentRagStreaming: (
    text: string,
    receiver: (chunk: string, complete: boolean, metadata?: StreamingMetadata) => void,
    onError: (error: string) => void,
    docLimit?: number,
    collection?: string,
    onExplain?: (event: ExplainEvent) => void,
  ) => void;

  textCompletionStreaming: (
    system: string,
    text: string,
    receiver: (chunk: string, complete: boolean, metadata?: StreamingMetadata) => void,
    onError: (error: string) => void,
  ) => void;

  promptStreaming: (
    id: string,
    terms: Record<string, unknown>,
    receiver: (chunk: string, complete: boolean, metadata?: StreamingMetadata) => void,
    onError: (error: string) => void,
  ) => void;

  // Generate embeddings for texts (batch)
  embeddings: (texts: string[]) => Promise<number[][]>;

  // Query graph using embedding vector
  graphEmbeddingsQuery: (vec: number[], limit: number) => Promise<EntityMatch[]>;

  // Query knowledge graph triples (subject-predicate-object)
  triplesQuery: (
    s?: Term, // Subject (optional)
    p?: Term, // Predicate (optional)
    o?: Term, // Object (optional)
    limit?: number,
    collection?: string,
    graph?: string, // Named graph URI filter
  ) => Promise<Triple[]>;

  // Load a document into the system
  loadDocument: (
    document: string, // Base64-encoded document
    id?: string, // Optional document ID
    metadata?: Triple[], // Optional metadata as triples
  ) => Promise<void>;

  // Load plain text into the system
  loadText: (text: string, id?: string, metadata?: Triple[]) => Promise<void>;

  // Load a document into the library with full metadata
  loadLibraryDocument: (
    document: string,
    mimeType: string,
    id?: string,
    metadata?: Triple[],
  ) => Promise<void>;
}

/**
 * Generates a random message ID using cryptographically secure random values
 * @param length - Number of random characters to generate
 * @returns Random string of specified length
 */
function makeid(length: number) {
  const array = new Uint32Array(length);
  getRandomValues(array);

  const characters = "abcdefghijklmnopqrstuvwxyz1234567890";

  return array.reduce(
    (acc, current) => acc + characters[current % characters.length],
    "",
  );
}

type NewableFactory<Args extends readonly unknown[], A extends object> = {
  new (...args: Args): A;
  (...args: Args): A;
  readonly prototype: A;
};

function newableFactory<Args extends readonly unknown[], A extends object>(
  factory: (...args: Args) => A,
): NewableFactory<Args, A> {
  function Constructor(...args: Args): A {
    return factory(...args);
  }
  return Constructor as unknown as NewableFactory<Args, A>;
}

/**
 * BaseApi - Core WebSocket client for TrustGraph API
 * Manages connection lifecycle, message routing, and provides base request
 * functionality
 */
// Connection state interface for UI consumption
export interface ConnectionState {
  status:
    | "connecting"
    | "connected"
    | "reconnecting"
    | "failed"
    | "authenticated"
    | "unauthenticated";
  hasApiKey: boolean;
  reconnectAttempt?: number;
  maxAttempts?: number;
  nextRetryIn?: number;
  lastError?: string;
}

export function makeBaseApi(
  user: string,
  token?: string,
  socketUrl?: string,
  rpcFactory: (url: string) => EffectRpcClient = makeEffectRpcClient,
) {
  let rpc: EffectRpcClient;
  const connectionStateListeners: ((state: ConnectionState) => void)[] = [];
  let lastError: string | undefined = undefined;
  let rpcState: RpcConnectionState = { status: "connecting" };

  const api = {
    tag: makeid(16), // Unique client identifier
    id: 1, // Counter for generating unique message IDs
    token, // Optional authentication token
    user, // User identifier for API requests
    socketUrl: withDefault(socketUrl, SOCKET_URL), // Use provided URL or default

    /**
     * Subscribe to connection state changes for UI updates
     */
    onConnectionStateChange(listener: (state: ConnectionState) => void) {
      connectionStateListeners.push(listener);
      // Immediately send current state
      listener(getConnectionState());

      // Return unsubscribe function
      return () => {
        const index = connectionStateListeners.indexOf(listener);
        if (index > -1) {
          connectionStateListeners.splice(index, 1);
        }
      };
    },

    /**
     * Closes the WebSocket connection and cleans up
     */
    close() {
      rpc.close().catch((err) => {
        console.error("[socket close error]", err);
      });
    },

    /**
     * Generates the next unique message ID for requests
     * Format: {clientTag}-{incrementingNumber}
     */
    getNextId() {
      const mid = api.tag + "-" + api.id.toString();
      api.id++;
      return mid;
    },

    /**
     * Core method for making service requests over WebSocket
     * @param service - Name of the service to call
     * @param request - Request payload
     * @param timeout - Request timeout in milliseconds (default: 10000)
     * @param retries - Number of retry attempts (default: 3)
     * @param flow - Optional flow identifier
     * @returns Promise resolving to the service response
     */
    makeRequest<RequestType extends object, ResponseType>(
      service: string,
      request: RequestType,
      timeout?: number,
      retries?: number,
      flow?: string,
    ) {
      return rpc
        .dispatch(dispatchInput(service, request, flow), dispatchOptions(timeout, retries))
        .then((obj) => {
          return obj as ResponseType;
        });
    },

    /**
     * Makes a request that can receive multiple responses (streaming)
     * Used for operations that return data in chunks
     */
    makeRequestMulti<RequestType extends object, ResponseType>(
      service: string,
      request: RequestType,
      receiver: (resp: unknown) => boolean, // Callback to handle each response chunk
      timeout?: number,
      retries?: number,
      flow?: string,
    ) {
      return rpc
        .dispatchStream(
          dispatchInput(service, request, flow),
          (chunk) => {
            return receiver({ response: chunk.response, complete: chunk.complete });
          },
          dispatchOptions(timeout, retries),
        )
        .then((obj) => {
          return obj as ResponseType;
        });
    },

    /**
     * Convenience method for making flow-specific requests
     * Defaults to "default" flow if none specified
     */
    makeFlowRequest<RequestType extends object, ResponseType>(
      service: string,
      request: RequestType,
      timeout?: number,
      retries?: number,
      flow?: string,
    ) {
      const flowName = isNonEmptyString(flow) ? flow : "default";

      return api.makeRequest<RequestType, ResponseType>(
        service,
        request,
        timeout,
        retries,
        flowName,
      );
    },

    // Factory methods for creating specialized API instances
    librarian() {
      return new LibrarianApi(api);
    },

    flows() {
      return new FlowsApi(api);
    },

    flow(id: string) {
      return new FlowApi(api, id);
    },

    knowledge() {
      return new KnowledgeApi(api);
    },

    config() {
      return new ConfigApi(api);
    },

    collectionManagement() {
      return new CollectionManagementApi(api);
    },
  };

  /**
   * Get current connection state
   */
  const getConnectionState = (): ConnectionState => {
    const hasApiKey = isNonEmptyString(api.token);
    const status = connectionStatusFromRpc(hasApiKey);

    const state: ConnectionState = {
      status,
      hasApiKey,
    };
    if (lastError !== undefined) {
      state.lastError = lastError;
    }

    return state;
  };

  /**
   * Notify all listeners of connection state changes
   */
  const notifyStateChange = () => {
    const state = getConnectionState();
    connectionStateListeners.forEach((listener) => {
      try {
        listener(state);
      } catch (error) {
        console.error("Error in connection state listener:", error);
      }
    });
  };

  const connectionStatusFromRpc = (hasApiKey: boolean): ConnectionState["status"] => {
    switch (rpcState.status) {
      case "connected":
        return hasApiKey ? "authenticated" : "unauthenticated";
      case "failed":
        return "failed";
      case "closed":
        return "failed";
      case "connecting":
        return lastError === undefined ? "connecting" : "reconnecting";
    }
  };

  const dispatchInput = <RequestType extends object>(
    service: string,
    request: RequestType,
    flow?: string,
  ): DispatchInput => {
    if (isNonEmptyString(flow)) {
      return {
        scope: "flow",
        service,
        flow,
        request: request as Record<string, unknown>,
      };
    }
    return {
      scope: "global",
      service,
      request: request as Record<string, unknown>,
    };
  };

  const socketUrlWithToken = (): string => {
    if (!isNonEmptyString(api.token)) return api.socketUrl;
    const separator = api.socketUrl.includes("?") ? "&" : "?";
    return `${api.socketUrl}${separator}token=${encodeURIComponent(api.token)}`;
  };

  rpc = rpcFactory(socketUrlWithToken());
  rpc.subscribe((state) => {
    rpcState = state;
    lastError = state.lastError;
    notifyStateChange();
  });

  console.log(
    "SOCKET: opening socket...",
    isNonEmptyString(token) ? "with auth" : "without auth",
    "user:",
    user,
  );

  return api;
}

export type BaseApi = ReturnType<typeof makeBaseApi>;
export const BaseApi = newableFactory(makeBaseApi);

export function makeBaseApiWithRpc(
  user: string,
  token: string | undefined,
  socketUrl: string | undefined,
  rpc: EffectRpcClient,
): BaseApi {
  return makeBaseApi(user, token, socketUrl, () => rpc);
}

/**
 * LibrarianApi - Manages document storage and retrieval
 * Handles document lifecycle including upload, processing, and removal
 */
export function makeLibrarianApi(api: BaseApi) {
  return {
    api,



      /**
       * Retrieves list of all documents in the system
       */
      getDocuments() {
        return this.api
          .makeRequest<LibraryRequest, LibraryResponse>(
            "librarian",
            {
              operation: "list-documents",
              user: this.api.user,
            },
            60000, // 60 second timeout for potentially large lists
          )
          .then((r) => r["document-metadatas"] ?? r.documents ?? []);
      },



      /**
       * Retrieves list of documents currently being processed
       */
      getProcessing() {
        return this.api
          .makeRequest<LibraryRequest, LibraryResponse>(
            "librarian",
            {
              operation: "list-processing",
              user: this.api.user,
            },
            60000,
          )
          .then((r) => r["processing-metadatas"] ?? r.processing ?? r["processing-metadata"] ?? []);
      },



      /**
       * Retrieves metadata for a single document by ID
       * @param documentId - Document URI/ID to fetch
       * @returns Document metadata including title, comments, tags, and RDF metadata
       */
      getDocumentMetadata(documentId: string): Promise<DocumentMetadata | null> {
        return this.api
          .makeRequest<LibraryRequest, LibraryResponse>(
            "librarian",
            {
              operation: "get-document-metadata",
              "document-id": documentId,
              documentId,
              user: this.api.user,
            },
            30000,
          )
          .then((r) => r["document-metadata"] ?? r.documentMetadata ?? null);
      },



      /**
       * Uploads a document to the library with full metadata
       * @param document - Base64-encoded document content
       * @param id - Optional document identifier
       * @param metadata - Optional metadata as triples
       * @param mimeType - Document MIME type
       * @param title - Document title
       * @param comments - Additional comments
       * @param tags - Document tags for categorization
       */
      loadDocument(
        document: string, // base64-encoded doc
        mimeType: string,
        title: string,
        comments: string,
        tags: string[],
        id?: string,
        metadata?: Triple[],
      ) {
        const documentMetadata: DocumentMetadata = {
          time: Math.floor(Date.now() / 1000), // Unix timestamp
          kind: mimeType,
          title,
          comments,
          user: this.api.user,
          tags,
          "document-type": "source",
          documentType: "source",
        };
        if (id !== undefined) {
          documentMetadata.id = id;
        }
        if (metadata !== undefined) {
          documentMetadata.metadata = metadata;
        }

        return this.api.makeRequest<LibraryRequest, LibraryResponse>(
          "librarian",
          {
            operation: "add-document",
            "document-metadata": documentMetadata,
            documentMetadata,
            content: document,
          },
          30000, // 30 second timeout for document upload
        );
      },



      /**
       * Removes a document from the library
       */
      removeDocument(id: string, collection?: string) {
        return this.api.makeRequest<LibraryRequest, LibraryResponse>(
          "librarian",
          {
            operation: "remove-document",
            "document-id": id,
            documentId: id,
            user: this.api.user,
            collection: withDefault(collection, "default"),
          },
          30000,
        );
      },



      /**
       * Adds a document to the processing queue
       * @param id - Processing job identifier
       * @param doc_id - Document to process
       * @param flow - Processing flow to use
       * @param collection - Collection to add processed data to
       * @param tags - Tags for the processing job
       */
      addProcessing(
        id: string,
        doc_id: string,
        flow: string,
        collection?: string,
        tags?: string[],
      ) {
        return this.api.makeRequest<LibraryRequest, LibraryResponse>(
          "librarian",
          {
            operation: "add-processing",
            "processing-metadata": {
              id: id,
              "document-id": doc_id,
              documentId: doc_id,
              time: Math.floor(Date.now() / 1000),
              flow: flow,
              user: this.api.user,
              collection: withDefault(collection, "default"),
              tags: tags ?? [],
            },
          },
          30000,
        );
      },



      // ========== Chunked Upload API ==========

      /**
       * Initialize a chunked upload session for large documents (>2MB)
       * @param metadata - Document metadata including id, title, kind (MIME type), etc.
       * @param totalSize - Total size of the document in bytes
       * @param chunkSize - Optional chunk size (default: 5MB)
       * @returns Upload session info including upload-id and total-chunks
       */
      beginUpload(
        metadata: ChunkedUploadDocumentMetadata,
        totalSize: number,
        chunkSize?: number,
      ): Promise<BeginUploadResponse> {
        const request: BeginUploadRequest = {
          operation: "begin-upload",
          "document-metadata": metadata,
          documentMetadata: metadata,
          "total-size": totalSize,
        };
        if (chunkSize !== undefined) {
          request["chunk-size"] = chunkSize;
        }

        return this.api
          .makeRequest<BeginUploadRequest, BeginUploadResponse>(
            "librarian",
            request,
            30000,
          )
          .then((r) => {
            throwIfResponseError(r.error);
            return r;
          });
      },



      /**
       * Upload a single chunk of a document
       * Chunks can be uploaded in any order and in parallel
       * @param uploadId - Upload session ID from beginUpload
       * @param chunkIndex - Zero-based chunk index
       * @param content - Base64-encoded chunk content
       * @returns Progress info including chunks-received and bytes-received
       */
      uploadChunk(
        uploadId: string,
        chunkIndex: number,
        content: string,
      ): Promise<UploadChunkResponse> {
        return this.api
          .makeRequest<UploadChunkRequest, UploadChunkResponse>(
            "librarian",
            {
              operation: "upload-chunk",
              "upload-id": uploadId,
              "chunk-index": chunkIndex,
              content: content,
              user: this.api.user,
            },
            60000, // Longer timeout for chunk uploads
          )
          .then((r) => {
            throwIfResponseError(r.error);
            return r;
          });
      },



      /**
       * Finalize a chunked upload after all chunks are received
       * Triggers document processing
       * @param uploadId - Upload session ID from beginUpload
       * @returns Document ID and object ID
       */
      completeUpload(uploadId: string): Promise<CompleteUploadResponse> {
        return this.api
          .makeRequest<CompleteUploadRequest, CompleteUploadResponse>(
            "librarian",
            {
              operation: "complete-upload",
              "upload-id": uploadId,
              user: this.api.user,
            },
            30000,
          )
          .then((r) => {
            throwIfResponseError(r.error);
            return r;
          });
      },



      /**
       * Check upload progress (useful for resuming interrupted uploads)
       * @param uploadId - Upload session ID
       * @returns Status including received/missing chunks
       */
      getUploadStatus(uploadId: string): Promise<GetUploadStatusResponse> {
        return this.api
          .makeRequest<GetUploadStatusRequest, GetUploadStatusResponse>(
            "librarian",
            {
              operation: "get-upload-status",
              "upload-id": uploadId,
              user: this.api.user,
            },
            30000,
          )
          .then((r) => {
            throwIfResponseError(r.error);
            return r;
          });
      },



      /**
       * Cancel an in-progress upload and clean up
       * @param uploadId - Upload session ID to abort
       */
      abortUpload(uploadId: string): Promise<void> {
        return this.api
          .makeRequest<AbortUploadRequest, AbortUploadResponse>(
            "librarian",
            {
              operation: "abort-upload",
              "upload-id": uploadId,
              user: this.api.user,
            },
            30000,
          )
          .then((r) => {
            throwIfResponseError(r.error);
          });
      },



      /**
       * List pending upload sessions for the current user
       * @returns Array of upload sessions with metadata and progress
       */
      listUploads(): Promise<UploadSession[]> {
        return this.api
          .makeRequest<ListUploadsRequest, ListUploadsResponse>(
            "librarian",
            {
              operation: "list-uploads",
              user: this.api.user,
            },
            30000,
          )
          .then((r) => {
            throwIfResponseError(r.error);
            return r["upload-sessions"] ?? [];
          });
      },



      /**
       * Stream a document in chunks for retrieval (streaming response)
       * Sends one request, receives multiple chunk responses via callback
       * @param documentId - Document ID to retrieve
       * @param onChunk - Callback for each chunk: (content, chunkIndex, totalChunks, complete) => void
       * @param onError - Callback for errors
       * @param chunkSize - Optional chunk size (default: 1MB)
       */
      streamDocument(
        documentId: string,
        onChunk: (content: string, chunkIndex: number, totalChunks: number, complete: boolean) => void,
        onError: (error: string) => void,
        chunkSize?: number,
      ): void {
        const receiver = (message: unknown): boolean => {
          const msg = message as { response?: StreamDocumentResponse; complete?: boolean; error?: string };

          // Check for top-level error
          if (msg.error !== undefined) {
            onError(msg.error);
            return true;
          }

          const resp = msg.response;
          if (resp === undefined) {
            return msg.complete === true;
          }

          // Check for response-level error
          if (resp.error !== undefined) {
            onError(resp.error.message);
            return true;
          }

          const complete = msg.complete === true;
          onChunk(resp.content, resp["chunk-index"], resp["total-chunks"], complete);

          return complete;
        };

        const request: StreamDocumentRequest = {
          operation: "stream-document",
          "document-id": documentId,
          user: this.api.user,
        };
        if (chunkSize !== undefined) {
          request["chunk-size"] = chunkSize;
        }

        this.api.makeRequestMulti<StreamDocumentRequest, StreamDocumentResponse>(
          "librarian",
          request,
          receiver,
          300000, // 5 minute timeout for full document stream
        );
      },
  };
}

export type LibrarianApi = ReturnType<typeof makeLibrarianApi>;
export const LibrarianApi = newableFactory(makeLibrarianApi);

/**
 * FlowsApi - Manages processing flows and configuration
 * Flows define how documents and data are processed through the system
 */
export function makeFlowsApi(api: BaseApi) {
  return {
    api,



      /**
       * Retrieves list of available flows
       */
      getFlows() {
        return this.api
          .makeRequest<FlowRequest, FlowResponse>(
            "flow",
            {
              operation: "list-flows",
            },
            60000,
          )
          .then((r) => r["flow-ids"] ?? []);
      },



      /**
       * Retrieves definition of a specific flow
       */
      getFlow(id: string) {
        return this.api
          .makeRequest<FlowRequest, FlowResponse>(
            "flow",
            {
              operation: "get-flow",
              "flow-id": id,
            },
            60000,
          )
          .then((r) => JSON.parse(r.flow ?? "{}")); // Parse JSON flow definition
      },



      // Configuration management methods

      /**
       * Retrieves all configuration settings
       */
      getConfigAll() {
        return this.api.makeRequest<ConfigRequest, ConfigResponse>(
          "config",
          {
            operation: "config",
          },
          60000,
        );
      },



      /**
       * Retrieves specific configuration values by key
       */
      getConfig(keys: { type: string; key: string }[]) {
        return this.api.makeRequest<ConfigRequest, ConfigResponse>(
          "config",
          {
            operation: "get",
            keys: keys,
          },
          60000,
        );
      },



      /**
       * Updates configuration values using the Python-compatible values array.
       */
      putConfig(items: { type: string; key: string; value: string }[]) {
        return this.api.makeRequest<ConfigRequest, ConfigResponse>(
          "config",
          {
            operation: "put",
            values: items,
          },
          60000,
        );
      },



      /**
       * Deletes a configuration entry
       */
      deleteConfig(target: { type: string; key: string }) {
        return this.api.makeRequest<ConfigRequest, ConfigResponse>(
            "config",
            {
              operation: "delete",
              keys: [target],
            },
            30000,
          );
      },



      // Prompt management - specialized config operations for AI prompts

      /**
       * Retrieves list of available prompt templates from config.prompt.
       * Each template is stored at `config.prompt.<name>` as an object
       * `{system, prompt}`. The reserved key `system` holds an optional
       * global system prompt and is excluded from the template list.
       */
      getPrompts() {
        return this.getConfigAll().then((r) => {
          const config = r as { config?: { prompt?: Record<string, unknown> } };
          const promptNs = config.config?.prompt ?? {};
          return Object.keys(promptNs)
            .filter((k) => k !== "system")
            .sort()
            .map((id) => ({ id, name: id }));
        });
      },



      /**
       * Retrieves a specific prompt template object: `{system, prompt}`.
       */
      getPrompt(id: string) {
        return this.getConfigAll().then((r) => {
          const config = r as { config?: { prompt?: Record<string, unknown> } };
          return config.config?.prompt?.[id] ?? null;
        });
      },



      /**
       * Retrieves the optional global system prompt at `config.prompt.system`.
       * Returns "" if not configured.
       */
      getSystemPrompt() {
        return this.getConfigAll().then((r) => {
          const config = r as { config?: { prompt?: { system?: unknown } } };
          const raw = config.config?.prompt?.system;
          if (raw == null) return "";
          return typeof raw === "string" ? raw : raw;
        });
      },



      // Flow blueprint management - templates for creating flows

      /**
       * Retrieves list of available flow blueprints (templates)
       */
      getFlowBlueprints() {
        return this.api
          .makeRequest<FlowRequest, FlowResponse>(
            "flow",
            {
              operation: "list-blueprints",
            },
            60000,
          )
          .then((r) => r["blueprint-names"]);
      },



      /**
       * Retrieves definition of a specific flow blueprint
       */
      getFlowBlueprint(name: string) {
        return this.api
          .makeRequest<FlowRequest, FlowResponse>(
            "flow",
            {
              operation: "get-blueprint",
              "blueprint-name": name,
            },
            60000,
          )
          .then((r) => JSON.parse(r["blueprint-definition"] ?? "{}"));
      },



      /**
       * Deletes a flow blueprint
       */
      deleteFlowBlueprint(name: string) {
        return this.api.makeRequest<FlowRequest, FlowResponse>(
          "flow",
          {
            operation: "delete-blueprint",
            "blueprint-name": name,
          },
          30000,
        );
      },



      // Flow lifecycle management

      /**
       * Starts a new flow instance
       */
      startFlow(
        id: string,
        blueprint_name: string,
        description: string,
        parameters?: Record<string, unknown>,
      ) {
        const request: FlowRequest = {
          operation: "start-flow",
          "flow-id": id,
          "blueprint-name": blueprint_name,
          description: description,
        };

        // Only include parameters if provided and not empty
        if (parameters !== undefined && Object.keys(parameters).length > 0) {
          request.parameters = parameters;
        }

        return this.api
          .makeRequest<FlowRequest, FlowResponse>("flow", request, 30000)
          .then((response) => {
            if (response.error !== undefined) {
              throw new Error(toErrorMessage(response.error, "Flow start failed"));
            }
            return response;
          });
      },



      /**
       * Stops a running flow instance
       */
      stopFlow(id: string) {
        return this.api.makeRequest<FlowRequest, FlowResponse>(
          "flow",
          {
            operation: "stop-flow",
            "flow-id": id,
          },
          30000,
        );
      },
  };
}

export type FlowsApi = ReturnType<typeof makeFlowsApi>;
export const FlowsApi = newableFactory(makeFlowsApi);

/**
 * FlowApi - Interface for interacting with a specific flow instance
 * Provides flow-specific versions of core AI/ML operations
 */
export function makeFlowApi(api: BaseApi, flowId: string) {
  return {
    api,

    flowId,



      /**
       * Performs text completion using AI models within this flow
       */
      textCompletion(system: string, text: string): Promise<string> {
        return this.api
          .makeRequest<TextCompletionRequest, TextCompletionResponse>(
            "text-completion",
            {
              system: system, // System prompt/instructions
              prompt: text, // User prompt
            },
            30000,
            undefined, // Use default retries
            this.flowId, // Route through this flow
          )
          .then((r) => r.response);
      },



      /**
       * Performs Graph RAG (Retrieval Augmented Generation) query
       */
      graphRag(text: string, options?: GraphRagOptions, collection?: string) {
        const request: GraphRagRequest = {
          query: text,
          user: this.api.user,
          collection: withDefault(collection, "default"),
        };
        if (options?.entityLimit !== undefined) {
          request["entity-limit"] = options.entityLimit;
        }
        if (options?.tripleLimit !== undefined) {
          request["triple-limit"] = options.tripleLimit;
        }
        if (options?.maxSubgraphSize !== undefined) {
          request["max-subgraph-size"] = options.maxSubgraphSize;
        }
        if (options?.pathLength !== undefined) {
          request["max-path-length"] = options.pathLength;
        }

        return this.api
          .makeRequest<GraphRagRequest, GraphRagResponse>(
            "graph-rag",
            request,
            60000, // Longer timeout for complex graph operations
            undefined,
            this.flowId,
          )
          .then((r) => r.response);
      },



      /**
       * Performs Document RAG (Retrieval Augmented Generation) query
       */
      documentRag(text: string, docLimit?: number, collection?: string) {
        return this.api
          .makeRequest<DocumentRagRequest, DocumentRagResponse>(
            "document-rag",
            {
              query: text,
              user: this.api.user,
              collection: withDefault(collection, "default"),
              "doc-limit": docLimit ?? 20,
            },
            60000, // Longer timeout for document operations
            undefined,
            this.flowId,
          )
          .then((r) => r.response);
      },



      /**
       * Interacts with an AI agent that provides streaming responses
       * BREAKING CHANGE: Callbacks now receive (chunk, complete, metadata?) instead of full messages
       */
      agent(
        question: string,
        think: (chunk: string, complete: boolean, metadata?: StreamingMetadata) => void,
        observe: (chunk: string, complete: boolean, metadata?: StreamingMetadata) => void,
        answer: (chunk: string, complete: boolean, metadata?: StreamingMetadata) => void,
        error: (s: string) => void,
        onExplain?: (event: ExplainEvent) => void,
        collection?: string,
      ) {
        const receiver = (message: unknown) => {
          const msg = message as { response?: AgentResponse; complete?: boolean; error?: string };

          // Check for top-level error
          if (msg.error !== undefined) {
            error(msg.error);
            return true;
          }

          const resp = msg.response ?? {};

          // Check for errors in response
          if (resp.chunk_type === "error" || resp.error !== undefined) {
            error(resp.error?.message ?? "Unknown agent error");
            return true; // End streaming on error
          }

          // Handle explainability events (agent uses chunk_type="explain")
          if (
            (resp.chunk_type === "explain" || resp.message_type === "explain") &&
            (resp.explain_id !== undefined || resp.explain_triples !== undefined)
          ) {
            const event: ExplainEvent = {
              explainId: resp.explain_id ?? "",
              explainGraph: resp.explain_graph ?? "",
            };
            if (resp.explain_triples !== undefined) {
              event.explainTriples = resp.explain_triples as Triple[];
            }
            onExplain?.(event);
            return false;
          }

          // Handle streaming chunks by chunk_type
          const content = resp.content ?? "";
          const messageComplete = resp.end_of_message === true;
          const dialogComplete = msg.complete === true || resp.end_of_dialog === true;

          // Extract metadata from final message
          const metadata = dialogComplete ? streamingMetadataFrom(resp) : undefined;

          switch (resp.chunk_type) {
            case "thought":
              think(content, messageComplete, metadata);
              break;
            case "observation":
              observe(content, messageComplete, metadata);
              break;
            case "answer":
            case "final-answer":
              answer(content, messageComplete, metadata);
              break;
            case "action":
              // Actions are typically not streamed incrementally, just logged
              console.log("Agent action:", content);
              break;
          }

          return dialogComplete; // End when backend signals complete
        };

        return this.api
          .makeRequestMulti<AgentRequest, AgentResponse>(
            "agent",
            {
              question: question,
              user: this.api.user,
            collection: withDefault(collection, "default"),
              streaming: true, // Always use streaming mode
            },
            receiver,
            120000,
            2,
            this.flowId,
          )
          .catch((err) => {
            const errorMessage = toErrorMessage(err, "Unknown error");
            error(`Agent request failed: ${errorMessage}`);
          });
      },



      /**
       * Performs Graph RAG query with streaming response
       * @param text - Query text
       * @param receiver - Called for each chunk with (chunk, complete) where complete=true on final chunk
       * @param onError - Called on error
       * @param options - Graph RAG options (including explainable flag)
       * @param collection - Collection name
       * @param onExplain - Optional callback for explainability events
       */
      graphRagStreaming(
        text: string,
        receiver: (chunk: string, complete: boolean, metadata?: StreamingMetadata) => void,
        onError: (error: string) => void,
        options?: GraphRagOptions,
        collection?: string,
        onExplain?: (event: ExplainEvent) => void,
      ): void {
        const recv = (message: unknown): boolean => {
          const msg = message as { response?: GraphRagResponse; complete?: boolean; error?: string };

          // Check for top-level error
          if (msg.error !== undefined) {
            onError(msg.error);
            return true;
          }

          const resp = (msg.response ?? {}) as GraphRagResponse;

          // Check for response-level error
          if (resp.error !== undefined) {
            onError(resp.error.message);
            return true;
          }

          // Extract explain data if present (may be embedded in the answer message)
          if (
            resp.message_type === "explain" &&
            (resp.explain_id !== undefined || resp.explain_triples !== undefined)
          ) {
            const event: ExplainEvent = {
              explainId: resp.explain_id ?? "",
              explainGraph: resp.explain_graph ?? "",
            };
            if (resp.explain_triples !== undefined) {
              event.explainTriples = resp.explain_triples as Triple[];
            }
            onExplain?.(event);
            // If this message also carries answer text, fall through to chunk handling.
            // If it's a standalone explain event (no answer text), stop here.
            if (resp.response === undefined && resp.endOfStream !== true && resp.end_of_session !== true) {
              return false;
            }
          }

          // Handle chunk messages (default behavior)
          const chunk = resp.response ?? resp.chunk ?? "";
          const complete = resp.end_of_session === true || resp.endOfStream === true || msg.complete === true;

          // Extract metadata from final message
          const metadata = complete ? streamingMetadataFrom(resp) : undefined;

          receiver(chunk, complete, metadata);

          return complete;
        };

        const request: GraphRagRequest = {
          query: text,
          user: this.api.user,
          collection: withDefault(collection, "default"),
          streaming: true,
        };
        if (options?.entityLimit !== undefined) {
          request["entity-limit"] = options.entityLimit;
        }
        if (options?.tripleLimit !== undefined) {
          request["triple-limit"] = options.tripleLimit;
        }
        if (options?.maxSubgraphSize !== undefined) {
          request["max-subgraph-size"] = options.maxSubgraphSize;
        }
        if (options?.pathLength !== undefined) {
          request["max-path-length"] = options.pathLength;
        }

        this.api.makeRequestMulti<GraphRagRequest, GraphRagResponse>(
          "graph-rag",
          request,
          recv,
          60000,
          undefined,
          this.flowId,
        ).catch((err) => {
          const errorMessage = toErrorMessage(err, "Unknown error");
          onError(`Graph RAG request failed: ${errorMessage}`);
        });
      },



      /**
       * Performs Document RAG query with streaming response
       * @param text - Query text
       * @param receiver - Called for each chunk with (chunk, complete) where complete=true on final chunk
       * @param onError - Called on error
       * @param docLimit - Maximum documents to retrieve
       * @param collection - Collection name
       */
      documentRagStreaming(
        text: string,
        receiver: (chunk: string, complete: boolean, metadata?: StreamingMetadata) => void,
        onError: (error: string) => void,
        docLimit?: number,
        collection?: string,
        onExplain?: (event: ExplainEvent) => void,
      ): void {
        const recv = (message: unknown): boolean => {
          const msg = message as { response?: DocumentRagResponse; complete?: boolean; error?: string };

          // Check for top-level error
          if (msg.error !== undefined) {
            onError(msg.error);
            return true;
          }

          const resp = (msg.response ?? {}) as DocumentRagResponse;

          // Check for response-level error
          if (resp.error !== undefined) {
            onError(resp.error.message);
            return true;
          }

          // Handle explainability events
          if (
            resp.message_type === "explain" &&
            resp.explain_id !== undefined &&
            resp.explain_graph !== undefined
          ) {
            onExplain?.({
              explainId: resp.explain_id,
              explainGraph: resp.explain_graph,
            });
            return false;
          }

          const chunk = resp.response ?? resp.chunk ?? "";
          const complete = resp.end_of_session === true || resp.endOfStream === true || msg.complete === true;

          // Extract metadata from final message
          const metadata = complete ? streamingMetadataFrom(resp) : undefined;

          receiver(chunk, complete, metadata);

          return complete;
        };

        const request: DocumentRagRequest = {
          query: text,
          user: this.api.user,
          collection: withDefault(collection, "default"),
          streaming: true,
        };
        if (docLimit !== undefined) {
          request["doc-limit"] = docLimit;
        }

        this.api.makeRequestMulti<DocumentRagRequest, DocumentRagResponse>(
          "document-rag",
          request,
          recv,
          60000,
          undefined,
          this.flowId,
        ).catch((err) => {
          const errorMessage = toErrorMessage(err, "Unknown error");
          onError(`Document RAG request failed: ${errorMessage}`);
        });
      },



      /**
       * Performs text completion with streaming response
       * @param system - System prompt
       * @param text - User prompt
       * @param receiver - Called for each chunk with (chunk, complete) where complete=true on final chunk
       * @param onError - Called on error
       */
      textCompletionStreaming(
        system: string,
        text: string,
        receiver: (chunk: string, complete: boolean, metadata?: StreamingMetadata) => void,
        onError: (error: string) => void,
      ): void {
        const recv = (message: unknown): boolean => {
          const msg = message as { response?: TextCompletionResponse; complete?: boolean; error?: string };

          // Check for top-level error
          if (msg.error !== undefined) {
            onError(msg.error);
            return true;
          }

          const resp = (msg.response ?? {}) as TextCompletionResponse;

          // Check for response-level error
          if (resp.error !== undefined) {
            onError(resp.error.message);
            return true;
          }

          // Text completion uses 'response' field for chunks
          const chunk = resp.response ?? "";
          const complete = msg.complete === true;

          // Extract metadata from final message
          const metadata = complete ? streamingMetadataFrom(resp) : undefined;

          receiver(chunk, complete, metadata);

          return complete;
        };

        this.api.makeRequestMulti<TextCompletionRequest, TextCompletionResponse>(
          "text-completion",
          {
            system: system,
            prompt: text,
            streaming: true,
          },
          recv,
          30000,
          undefined,
          this.flowId,
        );
      },



      /**
       * Executes a prompt template with streaming response
       * @param id - Prompt template ID
       * @param terms - Template variables
       * @param receiver - Called for each chunk with (chunk, complete) where complete=true on final chunk
       * @param onError - Called on error
       */
      promptStreaming(
        id: string,
        terms: Record<string, unknown>,
        receiver: (chunk: string, complete: boolean, metadata?: StreamingMetadata) => void,
        onError: (error: string) => void,
      ): void {
        const recv = (message: unknown): boolean => {
          const msg = message as { response?: PromptResponse; complete?: boolean; error?: string };

          // Check for top-level error
          if (msg.error !== undefined) {
            onError(msg.error);
            return true;
          }

          const resp = (msg.response ?? {}) as PromptResponse;

          // Check for response-level error
          if (resp.error !== undefined) {
            onError(resp.error.message);
            return true;
          }

          // Prompt service uses 'text' field for chunks
          const chunk = resp.text ?? "";
          const complete = msg.complete === true;

          // Extract metadata from final message
          const metadata = complete ? streamingMetadataFrom(resp) : undefined;

          receiver(chunk, complete, metadata);

          return complete;
        };

        this.api.makeRequestMulti<PromptRequest, PromptResponse>(
          "prompt",
          {
            id: id,
            terms: terms,
            streaming: true,
          },
          recv,
          30000,
          undefined,
          this.flowId,
        );
      },



      /**
       * Generates embeddings for multiple texts within this flow.
       * Returns vectors[text_index][dimension_index] - one vector per input text.
       */
      embeddings(texts: string[]) {
        return this.api
          .makeRequest<EmbeddingsRequest, EmbeddingsResponse>(
            "embeddings",
            {
              texts: texts,
            },
            30000,
            undefined,
            this.flowId,
          )
          .then((r) => r.vectors);
      },



      /**
       * Queries the knowledge graph using a single embedding vector
       */
      graphEmbeddingsQuery(
        vec: number[],
        limit: number | undefined,
        collection?: string,
      ) {
        return this.api
          .makeRequest<GraphEmbeddingsQueryRequest, GraphEmbeddingsQueryResponse>(
            "graph-embeddings",
            {
              vector: vec,
              limit: limit ?? 20, // Default to 20 results
              user: this.api.user,
              collection: withDefault(collection, "default"),
            },
            30000,
            undefined,
            this.flowId,
          )
          .then((r) => r.entities);
      },



      /**
       * Queries knowledge graph triples (subject-predicate-object relationships)
       * All parameters are optional - omitted parameters act as wildcards
       */
      triplesQuery(
        s?: Term,
        p?: Term,
        o?: Term,
        limit?: number,
        collection?: string,
        graph?: string,
      ) {
        const request: TriplesQueryRequest = {
          limit: limit ?? 20,
          user: this.api.user,
          collection: withDefault(collection, "default"),
        };
        if (s !== undefined) {
          request.s = s;
        }
        if (p !== undefined) {
          request.p = p;
        }
        if (o !== undefined) {
          request.o = o;
        }
        if (graph !== undefined) {
          request.g = graph;
        }

        return this.api
          .makeRequest<TriplesQueryRequest, TriplesQueryResponse>(
            "triples",
            request,
            30000,
            undefined,
            this.flowId,
          )
          .then((r) => r.triples ?? r.response ?? []);
      },



      /**
       * Loads a document into this flow for processing
       */
      loadDocument(
        document: string, // base64-encoded document
        id?: string,
        metadata?: Triple[],
      ) {
        const request: LoadDocumentRequest = {
          data: document,
        };
        if (id !== undefined) {
          request.id = id;
        }
        if (metadata !== undefined) {
          request.metadata = metadata;
        }

        return this.api.makeRequest<LoadDocumentRequest, LoadDocumentResponse>(
          "document-load",
          request,
          30000,
          undefined,
          this.flowId,
        );
      },



      /**
       * Loads plain text into this flow for processing
       */
      loadText(
        text: string, // Text content
        id?: string,
        metadata?: Triple[],
        charset?: string, // Character encoding
      ) {
        const request: LoadTextRequest = {
          text,
        };
        if (id !== undefined) {
          request.id = id;
        }
        if (metadata !== undefined) {
          request.metadata = metadata;
        }
        if (charset !== undefined) {
          request.charset = charset;
        }

        return this.api.makeRequest<LoadTextRequest, LoadTextResponse>(
          "text-load",
          request,
          30000,
          undefined,
          this.flowId,
        );
      },



      /**
       * Executes a GraphQL query against structured row data
       */
      rowsQuery(
        query: string,
        collection?: string,
        variables?: Record<string, unknown>,
        operationName?: string,
      ) {
        const request: RowsQueryRequest = {
          query,
          user: this.api.user,
          collection: withDefault(collection, "default"),
        };
        if (variables !== undefined) {
          request.variables = variables;
        }
        if (operationName !== undefined) {
          request.operation_name = operationName;
        }

        return this.api
          .makeRequest<RowsQueryRequest, RowsQueryResponse>(
            "rows",
            request,
            30000,
            undefined,
            this.flowId,
          )
          .then((r) => {
            // Return the GraphQL response structure directly
            const result: Record<string, unknown> = {};
            if (r.data !== undefined) result.data = r.data;
            if (r.errors !== undefined) result.errors = r.errors;
            if (r.extensions !== undefined) result.extensions = r.extensions;
            return result;
          });
      },



      /**
       * Converts a natural language question to a GraphQL query
       */
      nlpQuery(question: string, maxResults?: number) {
        return this.api
          .makeRequest<NlpQueryRequest, NlpQueryResponse>(
            "nlp-query",
            {
              question: question,
              max_results: maxResults ?? 100,
            },
            30000,
            undefined,
            this.flowId,
          )
          .then((r) => r);
      },



      /**
       * Executes a natural language question against structured data
       * Combines NLP query conversion and GraphQL execution
       */
      structuredQuery(question: string, collection?: string) {
        return this.api
          .makeRequest<StructuredQueryRequest, StructuredQueryResponse>(
            "structured-query",
            {
              question: question,
              user: this.api.user,
              collection: withDefault(collection, "default"),
            },
            30000,
            undefined,
            this.flowId,
          )
          .then((r) => {
            // Return the response structure directly
            const result: Record<string, unknown> = {};
            if (r.data !== undefined) result.data = r.data;
            if (r.errors !== undefined) result.errors = r.errors;
            return result;
          });
      },



      /**
       * Performs semantic search on structured data indexes using embedding vectors
       * @param vectors - Embedding vectors to search for
       * @param schemaName - Name of the schema to search
       * @param collection - Optional collection name
       * @param indexName - Optional index name to filter results
       * @param limit - Maximum number of results to return (default: 10)
       */
      rowEmbeddingsQuery(
        vector: number[],
        schemaName: string,
        collection?: string,
        indexName?: string,
        limit?: number,
      ): Promise<RowEmbeddingsMatch[]> {
        const request: RowEmbeddingsQueryRequest = {
          vector: vector,
          schema_name: schemaName,
          user: this.api.user,
          collection: withDefault(collection, "default"),
          limit: limit ?? 10,
        };

        if (indexName !== undefined) {
          request.index_name = indexName;
        }

        return this.api
          .makeRequest<RowEmbeddingsQueryRequest, RowEmbeddingsQueryResponse>(
            "row-embeddings",
            request,
            30000,
            undefined,
            this.flowId,
          )
          .then((r) => {
            if (r.error !== undefined) {
              throw new Error(r.error.message);
            }
            return r.matches ?? [];
          });
      },
  };
}

export type FlowApi = ReturnType<typeof makeFlowApi>;
export const FlowApi = newableFactory(makeFlowApi);

/**
 * ConfigApi - Dedicated configuration management interface
 * Handles system configuration, prompts, and token cost tracking
 */
export function makeConfigApi(api: BaseApi) {
  return {
    api,



      /**
       * Retrieves complete configuration
       */
      getConfigAll() {
        return this.api.makeRequest<ConfigRequest, ConfigResponse>(
          "config",
          {
            operation: "config",
          },
          60000,
        );
      },



      /**
       * Retrieves specific configuration entries
       */
      getConfig(keys: { type: string; key: string }[]) {
        return this.api.makeRequest<ConfigRequest, ConfigResponse>(
          "config",
          {
            operation: "get",
            keys: keys,
          },
          60000,
        );
      },



      /**
       * Updates configuration values using the Python-compatible values array.
       */
      putConfig(items: { type: string; key: string; value: string }[]) {
        return this.api.makeRequest<ConfigRequest, ConfigResponse>(
          "config",
          {
            operation: "put",
            values: items,
          },
          60000,
        );
      },



      /**
       * Deletes a configuration entry
       */
      deleteConfig(target: { type: string; key: string }) {
        return this.api.makeRequest<ConfigRequest, ConfigResponse>(
            "config",
            {
              operation: "delete",
              keys: [target],
            },
            30000,
          );
      },



      // Specialized prompt management methods

      /**
       * Retrieves list of available prompt templates from config.prompt.
       * Each template is stored at `config.prompt.<name>` as an object
       * `{system, prompt}`. The reserved key `system` holds an optional
       * global system prompt and is excluded from the template list.
       */
      getPrompts() {
        return this.getConfigAll().then((r) => {
          const config = r as { config?: { prompt?: Record<string, unknown> } };
          const promptNs = config.config?.prompt ?? {};
          return Object.keys(promptNs)
            .filter((k) => k !== "system")
            .sort()
            .map((id) => ({ id, name: id }));
        });
      },



      /**
       * Retrieves a specific prompt template object: `{system, prompt}`.
       */
      getPrompt(id: string) {
        return this.getConfigAll().then((r) => {
          const config = r as { config?: { prompt?: Record<string, unknown> } };
          return config.config?.prompt?.[id] ?? null;
        });
      },



      /**
       * Retrieves the optional global system prompt at `config.prompt.system`.
       * Returns "" if not configured.
       */
      getSystemPrompt() {
        return this.getConfigAll().then((r) => {
          const config = r as { config?: { prompt?: { system?: unknown } } };
          const raw = config.config?.prompt?.system;
          if (raw == null) return "";
          return typeof raw === "string" ? raw : raw;
        });
      },



      /**
       * Lists available configuration types
       */
      list(type: string) {
        return this.api
          .makeRequest<ConfigRequest, ConfigResponse>(
            "config",
            {
              operation: "list",
              type: type,
            },
            60000,
          )
          .then((r) => r);
      },



      /**
       * Retrieves all key/values for a specific type
       */
      getValues(type: string) {
        return this.api
          .makeRequest<ConfigRequest, ConfigResponse>(
            "config",
            {
              operation: "getvalues",
              type: type,
            },
            60000,
          )
          .then((r) => asConfigValues(r));
      },



      /**
       * Retrieves token cost information for different AI models
       * Useful for cost tracking and optimization
       */
      getTokenCosts() {
        return this.api
          .makeRequest<ConfigRequest, ConfigResponse>(
            "config",
            {
              operation: "getvalues",
              type: "token-cost",
            },
            60000,
          )
          .then((r) => {
            return asConfigValues(r).map((item) => ({
              key: item.key,
              value: parseConfigJson(item.value),
            }));
          })
          .then((r) =>
            // Transform to more usable format
            r.map((x: unknown) => {
              const item = x as Record<string, unknown>;
              const value = item.value as Record<string, number>;
              return {
                model: item.key,
                input_price: value.input_price, // Cost per input token
                output_price: value.output_price, // Cost per output token
              };
            }),
          );
      },
  };
}

export type ConfigApi = ReturnType<typeof makeConfigApi>;
export const ConfigApi = newableFactory(makeConfigApi);

/**
 * KnowledgeApi - Manages knowledge graph cores and data
 * Knowledge cores appear to be collections of processed knowledge graph data
 */
export function makeKnowledgeApi(api: BaseApi) {
  return {
    api,



      /**
       * Retrieves list of available knowledge graph cores
       */
      getKnowledgeCores() {
        return this.api
          .makeRequest<FlowRequest, FlowResponse>(
            "knowledge",
            {
              operation: "list-kg-cores",
              user: this.api.user,
            },
            60000,
          )
          .then((r) => r.ids ?? []);
      },



      getDocumentEmbeddingCores() {
        return this.api
          .makeRequest<FlowRequest, FlowResponse>(
            "knowledge",
            {
              operation: "list-de-cores",
              user: this.api.user,
            },
            60000,
          )
          .then((r) => r.ids ?? []);
      },



      /**
       * Deletes a knowledge graph core
       */
      deleteKgCore(id: string, collection?: string) {
        return this.api.makeRequest<LibraryRequest, LibraryResponse>(
          "knowledge",
          {
            operation: "delete-kg-core",
            id: id,
            user: this.api.user,
            collection: withDefault(collection, "default"),
          },
          30000,
        );
      },



      /**
       * Deletes a knowledge graph core
       */
      loadKgCore(id: string, flow: string, collection?: string) {
        return this.api.makeRequest<LibraryRequest, LibraryResponse>(
          "knowledge",
          {
            operation: "load-kg-core",
            id: id,
            flow: flow,
            user: this.api.user,
            collection: withDefault(collection, "default"),
          },
          30000,
        );
      },



      unloadKgCore(id: string, flow: string) {
        return this.api.makeRequest<LibraryRequest, LibraryResponse>(
          "knowledge",
          {
            operation: "unload-kg-core",
            id,
            flow,
            user: this.api.user,
          },
          30000,
        );
      },



      deleteDeCore(id: string) {
        return this.api.makeRequest<LibraryRequest, LibraryResponse>(
          "knowledge",
          {
            operation: "delete-de-core",
            id,
            user: this.api.user,
          },
          30000,
        );
      },



      loadDeCore(id: string, flow: string, collection?: string) {
        return this.api.makeRequest<LibraryRequest, LibraryResponse>(
          "knowledge",
          {
            operation: "load-de-core",
            id,
            flow,
            user: this.api.user,
            collection: withDefault(collection, "default"),
          },
          30000,
        );
      },



      /**
       * Retrieves a knowledge graph core with streaming data
       * Uses multi-request pattern for large datasets
       * @param receiver - Callback function to handle streaming data chunks
       */
      getKgCore(
        id: string,
        collection: string | undefined,
        receiver: (msg: unknown, eos: boolean) => void,
      ) {
        // Wrapper to handle end-of-stream detection
        const recv = (msg: unknown) => {
          const response = msg as Record<string, unknown>;
          if (response.eos === true) {
            // End of stream - notify receiver and signal completion
            receiver(msg, true);
            return true;
          } else {
            // Regular message - continue streaming
            receiver(msg, false);
            return false;
          }
        };

        return this.api.makeRequestMulti<LibraryRequest, LibraryResponse>(
          "knowledge",
          {
            operation: "get-kg-core",
            id: id,
            user: this.api.user,
            collection: withDefault(collection, "default"),
          },
          recv, // Stream handler
          30000,
        );
      },
  };
}

export type KnowledgeApi = ReturnType<typeof makeKnowledgeApi>;
export const KnowledgeApi = newableFactory(makeKnowledgeApi);

/**
 * CollectionManagementApi - Manages collections for organizing documents
 * Provides operations for listing, creating, updating, and deleting collections
 */
export function makeCollectionManagementApi(api: BaseApi) {
  return {
    api,



      /**
       * Lists all collections for the current user with optional tag filtering
       * @param tagFilter - Optional array of tags to filter collections
       * @returns Promise resolving to array of collection metadata
       */
      listCollections(tagFilter?: string[]) {
        const request: Record<string, unknown> = {
          operation: "list-collections",
          user: this.api.user,
        };

        if (tagFilter !== undefined && tagFilter.length > 0) {
          request.tag_filter = tagFilter;
        }

        return this.api
          .makeRequest<
            Record<string, unknown>,
            Record<string, unknown>
          >("collection-management", request, 30000)
          .then((r) => r.collections ?? []);
      },



      /**
       * Creates or updates a collection for the current user
       * @param collection - Collection ID (unique identifier)
       * @param name - Display name for the collection
       * @param description - Description of the collection
       * @param tags - Array of tags for categorization
       * @returns Promise resolving to updated collection metadata
       */
      updateCollection(
        collection: string,
        name?: string,
        description?: string,
        tags?: string[],
      ) {
        const request: Record<string, unknown> = {
          operation: "update-collection",
          user: this.api.user,
          collection,
        };

        if (name !== undefined) {
          request.name = name;
        }
        if (description !== undefined) {
          request.description = description;
        }
        if (tags !== undefined) {
          request.tags = tags;
        }

        return this.api
          .makeRequest<
            Record<string, unknown>,
            Record<string, unknown>
          >("collection-management", request, 30000)
          .then((r) => {
            if (
              r.collections !== undefined &&
              Array.isArray(r.collections) &&
              r.collections.length > 0
            ) {
              return r.collections[0];
            }
            throw new Error("Failed to update collection");
          });
      },



      /**
       * Deletes a collection and all its data for the current user
       * @param collection - Collection ID to delete
       * @returns Promise resolving when deletion is complete
       */
      deleteCollection(collection: string) {
        return this.api.makeRequest<
          Record<string, unknown>,
          Record<string, unknown>
        >(
          "collection-management",
          {
            operation: "delete-collection",
            user: this.api.user,
            collection,
          },
          30000,
        );
      },
  };
}

export type CollectionManagementApi = ReturnType<typeof makeCollectionManagementApi>;
export const CollectionManagementApi = newableFactory(makeCollectionManagementApi);

/**
 * Factory function to create a new TrustGraph WebSocket connection
 * This is the main entry point for using the TrustGraph API
 * @param user - User identifier for API requests
 * @param token - Optional authentication token for secure connections
 * @param socketUrl - Optional WebSocket URL (defaults to /api/v1/rpc for browser, provide full URL for Node.js)
 */
export const createTrustGraphSocket = (
  user: string,
  token?: string,
  socketUrl?: string,
): BaseApi => {
  return new BaseApi(user, token, socketUrl);
};
