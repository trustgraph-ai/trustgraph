// Import core types and classes for the TrustGraph API
import { Triple, Term } from "../models/Triple";
import { ServiceCallMulti } from "./service-call-multi";
import { ServiceCall } from "./service-call";

// Import all message types for different services
import {
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
  RequestMessage,
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
} from "../models/messages";

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
}

// Configuration constants
const SOCKET_RECONNECTION_TIMEOUT = 2000; // 2 seconds between reconnection
// attempts
const SOCKET_URL = "/api/socket"; // WebSocket endpoint path

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
  crypto.getRandomValues(array);

  const characters = "abcdefghijklmnopqrstuvwxyz1234567890";

  return array.reduce(
    (acc, current) => acc + characters[current % characters.length],
    "",
  );
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

export class BaseApi {
  ws?: WebSocket; // WebSocket connection instance
  tag: string; // Unique client identifier
  id: number; // Counter for generating unique message IDs
  token?: string; // Optional authentication token
  user: string; // User identifier for API requests
  socketUrl: string; // WebSocket URL
  inflight: { [key: string]: ServiceCall } = {}; // Track active requests by
  // message ID
  reconnectAttempts: number = 0; // Track reconnection attempts
  maxReconnectAttempts: number = 10; // Maximum reconnection attempts
  reconnectTimer?: number; // Timer for reconnection attempts
  reconnectionState: "idle" | "reconnecting" | "failed" = "idle"; // Connection state

  // Connection state tracking for UI
  private connectionStateListeners: ((state: ConnectionState) => void)[] = [];
  private lastError?: string;

  constructor(user: string, token?: string, socketUrl?: string) {
    this.tag = makeid(16); // Generate unique client tag
    this.id = 1; // Start message ID counter
    this.token = token; // Store authentication token
    this.user = user; // Store user identifier
    this.socketUrl = socketUrl || SOCKET_URL; // Use provided URL or default

    console.log(
      "SOCKET: opening socket...",
      token ? "with auth" : "without auth",
      "user:",
      user,
    );
    this.openSocket(); // Establish WebSocket connection
    console.log("SOCKET: socket opened");
  }

  /**
   * Subscribe to connection state changes for UI updates
   */
  onConnectionStateChange(listener: (state: ConnectionState) => void) {
    this.connectionStateListeners.push(listener);
    // Immediately send current state
    listener(this.getConnectionState());

    // Return unsubscribe function
    return () => {
      const index = this.connectionStateListeners.indexOf(listener);
      if (index > -1) {
        this.connectionStateListeners.splice(index, 1);
      }
    };
  }

  /**
   * Get current connection state
   */
  private getConnectionState(): ConnectionState {
    const hasApiKey = !!this.token;

    // Determine status based on WebSocket state and reconnection state
    let status: ConnectionState["status"];

    if (!this.ws || this.ws.readyState === WebSocket.CLOSED) {
      if (this.reconnectionState === "failed") {
        status = "failed";
      } else if (this.reconnectionState === "reconnecting") {
        status = "reconnecting";
      } else {
        status = "connecting";
      }
    } else if (this.ws.readyState === WebSocket.CONNECTING) {
      status = "connecting";
    } else if (this.ws.readyState === WebSocket.OPEN) {
      status = hasApiKey ? "authenticated" : "unauthenticated";
    } else {
      status = "connecting";
    }

    const state: ConnectionState = {
      status,
      hasApiKey,
      lastError: this.lastError,
    };

    // Add reconnection details if applicable
    if (status === "reconnecting") {
      state.reconnectAttempt = this.reconnectAttempts;
      state.maxAttempts = this.maxReconnectAttempts;
    }

    return state;
  }

  /**
   * Notify all listeners of connection state changes
   */
  private notifyStateChange() {
    const state = this.getConnectionState();
    this.connectionStateListeners.forEach((listener) => {
      try {
        listener(state);
      } catch (error) {
        console.error("Error in connection state listener:", error);
      }
    });
  }

  /**
   * Establishes WebSocket connection and sets up event handlers
   */
  openSocket() {
    // Don't create multiple connections
    if (
      this.ws &&
      (this.ws.readyState === WebSocket.CONNECTING ||
        this.ws.readyState === WebSocket.OPEN)
    ) {
      return;
    }

    // Clean up old socket if exists
    if (this.ws) {
      this.ws.removeEventListener("message", this.onMessage);
      this.ws.removeEventListener("close", this.onClose);
      this.ws.removeEventListener("open", this.onOpen);
      this.ws.removeEventListener("error", this.onError);
      this.ws = undefined;
    }

    try {
      // Build WebSocket URL with optional token parameter
      const wsUrl = this.token
        ? `${this.socketUrl}?token=${this.token}`
        : this.socketUrl;
      console.log(
        "SOCKET: connecting to",
        wsUrl.replace(/token=[^&]*/, "token=***"),
      );
      this.ws = new WebSocket(wsUrl);
    } catch (e) {
      console.error("[socket creation error]", e);
      this.scheduleReconnect();
      return;
    }

    // Bind event handlers to maintain proper 'this' context
    this.onMessage = this.onMessage.bind(this);
    this.onClose = this.onClose.bind(this);
    this.onOpen = this.onOpen.bind(this);
    this.onError = this.onError.bind(this);

    // Attach event listeners
    this.ws.addEventListener("message", this.onMessage);
    this.ws.addEventListener("close", this.onClose);
    this.ws.addEventListener("open", this.onOpen);
    this.ws.addEventListener("error", this.onError);
  }

  // Handle incoming messages from server
  onMessage(message: MessageEvent) {
    if (!message.data) return;

    try {
      const obj = JSON.parse(message.data);

      // Skip messages without ID (can't route them)
      if (!obj.id) return;

      // Route response to the corresponding inflight request
      if (this.inflight[obj.id]) {
        // Pass the whole message object so receiver can access 'complete' flag
        this.inflight[obj.id].onReceived(obj);
      }
    } catch (e) {
      console.error("[socket message parse error]", e);
    }
  }

  // Handle connection closure - automatically attempt reconnection
  onClose(event: CloseEvent) {
    console.log("[socket close]", event.code, event.reason);
    this.lastError = `Connection closed: ${event.reason || "Unknown reason"}`;
    this.ws = undefined;
    this.notifyStateChange();
    this.scheduleReconnect();
  }

  // Handle successful connection
  onOpen() {
    console.log("[socket open]");
    this.reconnectAttempts = 0; // Reset reconnection attempts on success
    this.reconnectionState = "idle"; // Reset connection state
    this.lastError = undefined; // Clear any previous errors

    // Clear any pending reconnect timer
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = undefined;
    }

    // Notify UI of successful connection
    this.notifyStateChange();

    // Immediately retry any pending requests that were waiting for connection
    for (const mid in this.inflight) {
      this.inflight[mid].retryNow();
    }
  }

  // Handle socket errors
  onError(event: Event) {
    console.error("[socket error]", event);
    this.lastError = "Connection error occurred";
    this.notifyStateChange();
  }

  /**
   * Schedules a reconnection attempt with exponential backoff
   */
  scheduleReconnect() {
    // Prevent concurrent reconnection attempts
    if (this.reconnectionState === "reconnecting") {
      console.log("[socket] Reconnection already in progress, skipping");
      return;
    }

    // Don't schedule if already scheduled
    if (this.reconnectTimer) return;

    this.reconnectionState = "reconnecting";
    this.reconnectAttempts++;
    this.notifyStateChange(); // Notify UI of reconnection attempt

    if (this.reconnectAttempts > this.maxReconnectAttempts) {
      console.error("[socket] Max reconnection attempts reached");
      this.reconnectionState = "failed";
      this.lastError = "Max reconnection attempts exceeded";
      this.notifyStateChange();
      // Notify all pending requests of the failure
      for (const mid in this.inflight) {
        this.inflight[mid].error(new Error("WebSocket connection failed"));
      }
      return;
    }

    // Calculate exponential backoff with jitter
    const backoffDelay = Math.min(
      SOCKET_RECONNECTION_TIMEOUT * Math.pow(2, this.reconnectAttempts - 1) +
        Math.random() * 1000,
      30000, // Max 30 seconds
    );

    console.log(
      `[socket] Reconnecting in ${backoffDelay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`,
    );

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = undefined;
      this.reopen();
    }, backoffDelay) as unknown as number;
  }

  /**
   * Reopens the WebSocket connection (used after connection failures)
   */
  reopen() {
    console.log("[socket reopen]");
    // Check if we're already connected or connecting
    if (
      this.ws &&
      (this.ws.readyState === WebSocket.OPEN ||
        this.ws.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }
    this.openSocket();
  }

  /**
   * Closes the WebSocket connection and cleans up
   */
  close() {
    // Clear reconnection timer
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = undefined;
    }

    // Clean up WebSocket
    if (this.ws) {
      // Remove event listeners to prevent memory leaks
      this.ws.removeEventListener("message", this.onMessage);
      this.ws.removeEventListener("close", this.onClose);
      this.ws.removeEventListener("open", this.onOpen);
      this.ws.removeEventListener("error", this.onError);

      this.ws.close();
      this.ws = undefined;
    }

    // Clear any remaining inflight requests
    for (const mid in this.inflight) {
      this.inflight[mid].error(new Error("Socket closed"));
    }
    this.inflight = {};
  }

  /**
   * Generates the next unique message ID for requests
   * Format: {clientTag}-{incrementingNumber}
   */
  getNextId() {
    const mid = this.tag + "-" + this.id.toString();
    this.id++;
    return mid;
  }

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
    const mid = this.getNextId();

    // Set default values
    if (timeout == undefined) timeout = 10000;
    if (retries == undefined) retries = 3;

    // Construct the request message
    const msg: RequestMessage = {
      id: mid,
      service: service,
      request: request,
    };

    // Add flow identifier if provided
    if (flow) msg.flow = flow;

    // Return a Promise that will be resolved/rejected by the ServiceCall
    return new Promise<ResponseType>((resolve, reject) => {
      const call = new ServiceCall(
        mid,
        msg,
        resolve as (resp: unknown) => void,
        reject as (err: object | string) => void,
        timeout,
        retries,
        this,
      );

      call.start();
      // Commented out debug logging: console.log("-->", msg);
    }).then((obj) => {
      // Commented out success logging: console.log("Success for", mid);
      return obj as ResponseType;
    });
  }

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
    const mid = this.getNextId();

    // Set defaults
    if (timeout == undefined) timeout = 10000;
    if (retries == undefined) retries = 3;

    // Construct request message
    const msg: RequestMessage = {
      id: mid,
      service: service,
      request: request,
    };

    if (flow) msg.flow = flow;

    return new Promise<ResponseType>((resolve, reject) => {
      const call = new ServiceCallMulti(
        mid,
        msg,
        resolve as (resp: unknown) => void,
        reject as (err: object | string) => void,
        timeout,
        retries,
        this as any, // eslint-disable-line @typescript-eslint/no-explicit-any
        receiver,
      );

      call.start();
    }).then((obj) => {
      return obj as ResponseType;
    });
  }

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
    if (!flow) flow = "default";

    return this.makeRequest<RequestType, ResponseType>(
      service,
      request,
      timeout,
      retries,
      flow,
    );
  }

  // Factory methods for creating specialized API instances
  librarian() {
    return new LibrarianApi(this);
  }

  flows() {
    return new FlowsApi(this);
  }

  flow(id: string) {
    return new FlowApi(this, id);
  }

  knowledge() {
    return new KnowledgeApi(this);
  }

  config() {
    return new ConfigApi(this);
  }

  collectionManagement() {
    return new CollectionManagementApi(this);
  }
}

/**
 * LibrarianApi - Manages document storage and retrieval
 * Handles document lifecycle including upload, processing, and removal
 */
export class LibrarianApi {
  api: BaseApi;

  constructor(api: BaseApi) {
    this.api = api;
  }

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
      .then((r) => r["document-metadatas"] || []);
  }

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
      .then((r) => r["processing-metadata"] || []);
  }

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
          user: this.api.user,
        },
        30000,
      )
      .then((r) => r["document-metadata"] || null);
  }

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
    return this.api.makeRequest<LibraryRequest, LibraryResponse>(
      "librarian",
      {
        operation: "add-document",
        "document-metadata": {
          id: id,
          time: Math.floor(Date.now() / 1000), // Unix timestamp
          kind: mimeType,
          title: title,
          comments: comments,
          metadata: metadata,
          user: this.api.user,
          tags: tags,
        },
        content: document,
      },
      30000, // 30 second timeout for document upload
    );
  }

  /**
   * Removes a document from the library
   */
  removeDocument(id: string, collection?: string) {
    return this.api.makeRequest<LibraryRequest, LibraryResponse>(
      "librarian",
      {
        operation: "remove-document",
        "document-id": id,
        user: this.api.user,
        collection: collection || "default",
      },
      30000,
    );
  }

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
          time: Math.floor(Date.now() / 1000),
          flow: flow,
          user: this.api.user,
          collection: collection ? collection : "default",
          tags: tags ? tags : [],
        },
      },
      30000,
    );
  }

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
    return this.api
      .makeRequest<BeginUploadRequest, BeginUploadResponse>(
        "librarian",
        {
          operation: "begin-upload",
          "document-metadata": metadata,
          "total-size": totalSize,
          "chunk-size": chunkSize,
        },
        30000,
      )
      .then((r) => {
        if (r.error) {
          throw new Error(r.error.message);
        }
        return r;
      });
  }

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
        if (r.error) {
          throw new Error(r.error.message);
        }
        return r;
      });
  }

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
        if (r.error) {
          throw new Error(r.error.message);
        }
        return r;
      });
  }

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
        if (r.error) {
          throw new Error(r.error.message);
        }
        return r;
      });
  }

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
        if (r.error) {
          throw new Error(r.error.message);
        }
      });
  }

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
        if (r.error) {
          throw new Error(r.error.message);
        }
        return r["upload-sessions"] || [];
      });
  }

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
      if (msg.error) {
        onError(msg.error);
        return true;
      }

      const resp = msg.response;
      if (!resp) {
        return !!msg.complete;
      }

      // Check for response-level error
      if (resp.error) {
        onError(resp.error.message);
        return true;
      }

      const complete = !!msg.complete;
      onChunk(resp.content, resp["chunk-index"], resp["total-chunks"], complete);

      return complete;
    };

    this.api.makeRequestMulti<StreamDocumentRequest, StreamDocumentResponse>(
      "librarian",
      {
        operation: "stream-document",
        "document-id": documentId,
        "chunk-size": chunkSize,
        user: this.api.user,
      },
      receiver,
      300000, // 5 minute timeout for full document stream
    );
  }
}

/**
 * FlowsApi - Manages processing flows and configuration
 * Flows define how documents and data are processed through the system
 */
export class FlowsApi {
  api: BaseApi;

  constructor(api: BaseApi) {
    this.api = api;
  }

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
      .then((r) => r["flow-ids"] || []);
  }

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
      .then((r) => JSON.parse(r.flow || "{}")); // Parse JSON flow definition
  }

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
  }

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
  }

  /**
   * Updates configuration values
   */
  putConfig(values: { type: string; key: string; value: string }[]) {
    return this.api.makeRequest<ConfigRequest, ConfigResponse>(
      "config",
      {
        operation: "put",
        values: values,
      },
      60000,
    );
  }

  /**
   * Deletes configuration entries
   */
  deleteConfig(keys: { type: string; key: string }) {
    return this.api.makeRequest<ConfigRequest, ConfigResponse>(
      "config",
      {
        operation: "delete",
        keys: keys,
      },
      30000,
    );
  }

  // Prompt management - specialized config operations for AI prompts

  /**
   * Retrieves list of available prompt templates
   */
  getPrompts() {
    return this.getConfigAll().then((r) => {
      const config = r as Record<
        string,
        Record<string, Record<string, string>>
      >;
      return JSON.parse(config.config.prompt["template-index"]);
    });
  }

  /**
   * Retrieves a specific prompt template
   */
  getPrompt(id: string) {
    return this.getConfigAll().then((r) => {
      const config = r as Record<
        string,
        Record<string, Record<string, string>>
      >;
      return JSON.parse(config.config.prompt[`template.${id}`]);
    });
  }

  /**
   * Retrieves the system prompt configuration
   */
  getSystemPrompt() {
    return this.getConfigAll().then((r) => {
      const config = r as Record<
        string,
        Record<string, Record<string, string>>
      >;
      return JSON.parse(config.config.prompt.system);
    });
  }

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
  }

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
      .then((r) => JSON.parse(r["blueprint-definition"] || "{}"));
  }

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
  }

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
    if (parameters && Object.keys(parameters).length > 0) {
      request.parameters = parameters;
    }

    return this.api
      .makeRequest<FlowRequest, FlowResponse>("flow", request, 30000)
      .then((response) => {
        if (response.error) {
          let errorMessage = "Flow start failed";
          if (
            typeof response.error === "object" &&
            response.error &&
            "message" in response.error
          ) {
            errorMessage =
              (response.error as { message?: string }).message || errorMessage;
          } else if (typeof response.error === "string") {
            errorMessage = response.error;
          }
          throw new Error(errorMessage);
        }
        return response;
      });
  }

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
  }
}

/**
 * FlowApi - Interface for interacting with a specific flow instance
 * Provides flow-specific versions of core AI/ML operations
 */
export class FlowApi {
  api: BaseApi;
  flowId: string;

  constructor(api: BaseApi, flowId: string) {
    this.api = api;
    this.flowId = flowId; // All requests will be routed through this flow
  }

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
  }

  /**
   * Performs Graph RAG (Retrieval Augmented Generation) query
   */
  graphRag(text: string, options?: GraphRagOptions, collection?: string) {
    return this.api
      .makeRequest<GraphRagRequest, GraphRagResponse>(
        "graph-rag",
        {
          query: text,
          user: this.api.user,
          collection: collection || "default",
          "entity-limit": options?.entityLimit,
          "triple-limit": options?.tripleLimit,
          "max-subgraph-size": options?.maxSubgraphSize,
          "max-path-length": options?.pathLength,
        },
        60000, // Longer timeout for complex graph operations
        undefined,
        this.flowId,
      )
      .then((r) => r.response);
  }

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
          collection: collection || "default",
          "doc-limit": docLimit || 20,
        },
        60000, // Longer timeout for document operations
        undefined,
        this.flowId,
      )
      .then((r) => r.response);
  }

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
  ) {
    const receiver = (message: unknown) => {
      const msg = message as { response?: AgentResponse; complete?: boolean; error?: string };

      // Check for top-level error
      if (msg.error) {
        error(msg.error);
        return true;
      }

      const resp = msg.response || {};

      // Check for errors in response
      if (resp.chunk_type === "error" || resp.error) {
        error(resp.error?.message || "Unknown agent error");
        return true; // End streaming on error
      }

      // Handle explainability events (agent uses chunk_type="explain")
      if ((resp.chunk_type === "explain" || resp.message_type === "explain") && resp.explain_id && resp.explain_graph) {
        onExplain?.({
          explainId: resp.explain_id,
          explainGraph: resp.explain_graph,
        });
        return false;
      }

      // Handle streaming chunks by chunk_type
      const content = resp.content || "";
      const messageComplete = !!resp.end_of_message;
      const dialogComplete = !!msg.complete;

      // Extract metadata from final message
      const metadata: StreamingMetadata | undefined = dialogComplete && (resp.in_token || resp.out_token || resp.model)
        ? { in_token: resp.in_token, out_token: resp.out_token, model: resp.model }
        : undefined;

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
          streaming: true, // Always use streaming mode
        },
        receiver,
        120000,
        2,
        this.flowId,
      )
      .catch((err) => {
        const errorMessage =
          err instanceof Error ? err.message : err?.toString() || "Unknown error";
        error(`Agent request failed: ${errorMessage}`);
      });
  }

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
      if (msg.error) {
        onError(msg.error);
        return true;
      }

      const resp = (msg.response || {}) as GraphRagResponse;

      // Check for response-level error
      if (resp.error) {
        onError(resp.error.message);
        return true;
      }

      // Handle explainability events
      if (resp.message_type === "explain" && resp.explain_id && resp.explain_graph) {
        onExplain?.({
          explainId: resp.explain_id,
          explainGraph: resp.explain_graph,
        });
        // Don't return true - more messages may follow
        return false;
      }

      // Handle chunk messages (default behavior)
      const chunk = resp.response || resp.chunk || "";
      const complete = !!resp.end_of_session || !!msg.complete;

      // Extract metadata from final message
      const metadata: StreamingMetadata | undefined = complete && (resp.in_token || resp.out_token || resp.model)
        ? { in_token: resp.in_token, out_token: resp.out_token, model: resp.model }
        : undefined;

      receiver(chunk, complete, metadata);

      return complete;
    };

    this.api.makeRequestMulti<GraphRagRequest, GraphRagResponse>(
      "graph-rag",
      {
        query: text,
        user: this.api.user,
        collection: collection || "default",
        "entity-limit": options?.entityLimit,
        "triple-limit": options?.tripleLimit,
        "max-subgraph-size": options?.maxSubgraphSize,
        "max-path-length": options?.pathLength,
        streaming: true,
      },
      recv,
      60000,
      undefined,
      this.flowId,
    );
  }

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
      if (msg.error) {
        onError(msg.error);
        return true;
      }

      const resp = (msg.response || {}) as DocumentRagResponse;

      // Check for response-level error
      if (resp.error) {
        onError(resp.error.message);
        return true;
      }

      // Handle explainability events
      if (resp.message_type === "explain" && resp.explain_id && resp.explain_graph) {
        onExplain?.({
          explainId: resp.explain_id,
          explainGraph: resp.explain_graph,
        });
        return false;
      }

      const chunk = resp.response || resp.chunk || "";
      const complete = !!resp.end_of_session || !!msg.complete;

      // Extract metadata from final message
      const metadata: StreamingMetadata | undefined = complete && (resp.in_token || resp.out_token || resp.model)
        ? { in_token: resp.in_token, out_token: resp.out_token, model: resp.model }
        : undefined;

      receiver(chunk, complete, metadata);

      return complete;
    };

    this.api.makeRequestMulti<DocumentRagRequest, DocumentRagResponse>(
      "document-rag",
      {
        query: text,
        user: this.api.user,
        collection: collection || "default",
        "doc-limit": docLimit,
        streaming: true,
      },
      recv,
      60000,
      undefined,
      this.flowId,
    );
  }

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
      if (msg.error) {
        onError(msg.error);
        return true;
      }

      const resp = (msg.response || {}) as TextCompletionResponse;

      // Check for response-level error
      if (resp.error) {
        onError(resp.error.message);
        return true;
      }

      // Text completion uses 'response' field for chunks
      const chunk = resp.response || "";
      const complete = !!msg.complete;

      // Extract metadata from final message
      const metadata: StreamingMetadata | undefined = complete && (resp.in_token || resp.out_token || resp.model)
        ? { in_token: resp.in_token, out_token: resp.out_token, model: resp.model }
        : undefined;

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
  }

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
      if (msg.error) {
        onError(msg.error);
        return true;
      }

      const resp = (msg.response || {}) as PromptResponse;

      // Check for response-level error
      if (resp.error) {
        onError(resp.error.message);
        return true;
      }

      // Prompt service uses 'text' field for chunks
      const chunk = resp.text || "";
      const complete = !!msg.complete;

      // Extract metadata from final message
      const metadata: StreamingMetadata | undefined = complete && (resp.in_token || resp.out_token || resp.model)
        ? { in_token: resp.in_token, out_token: resp.out_token, model: resp.model }
        : undefined;

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
  }

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
  }

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
          limit: limit ? limit : 20, // Default to 20 results
          user: this.api.user,
          collection: collection || "default",
        },
        30000,
        undefined,
        this.flowId,
      )
      .then((r) => r.entities);
  }

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
    return this.api
      .makeRequest<TriplesQueryRequest, TriplesQueryResponse>(
        "triples",
        {
          s: s, // Subject
          p: p, // Predicate
          o: o, // Object
          g: graph, // Named graph URI filter
          limit: limit ? limit : 20,
          user: this.api.user,
          collection: collection || "default",
        },
        30000,
        undefined,
        this.flowId,
      )
      .then((r) => r.response);
  }

  /**
   * Loads a document into this flow for processing
   */
  loadDocument(
    document: string, // base64-encoded document
    id?: string,
    metadata?: Triple[],
  ) {
    return this.api.makeRequest<LoadDocumentRequest, LoadDocumentResponse>(
      "document-load",
      {
        id: id,
        metadata: metadata,
        data: document,
      },
      30000,
      undefined,
      this.flowId,
    );
  }

  /**
   * Loads plain text into this flow for processing
   */
  loadText(
    text: string, // Text content
    id?: string,
    metadata?: Triple[],
    charset?: string, // Character encoding
  ) {
    return this.api.makeRequest<LoadTextRequest, LoadTextResponse>(
      "text-load",
      {
        id: id,
        metadata: metadata,
        text: text,
        charset: charset,
      },
      30000,
      undefined,
      this.flowId,
    );
  }

  /**
   * Executes a GraphQL query against structured row data
   */
  rowsQuery(
    query: string,
    collection?: string,
    variables?: Record<string, unknown>,
    operationName?: string,
  ) {
    return this.api
      .makeRequest<RowsQueryRequest, RowsQueryResponse>(
        "rows",
        {
          query: query,
          user: this.api.user,
          collection: collection || "default",
          variables: variables,
          operation_name: operationName,
        },
        30000,
        undefined,
        this.flowId,
      )
      .then((r) => {
        // Return the GraphQL response structure directly
        const result: Record<string, unknown> = {};
        if (r.data !== undefined) result.data = r.data;
        if (r.errors) result.errors = r.errors;
        if (r.extensions) result.extensions = r.extensions;
        return result;
      });
  }

  /**
   * Converts a natural language question to a GraphQL query
   */
  nlpQuery(question: string, maxResults?: number) {
    return this.api
      .makeRequest<NlpQueryRequest, NlpQueryResponse>(
        "nlp-query",
        {
          question: question,
          max_results: maxResults || 100,
        },
        30000,
        undefined,
        this.flowId,
      )
      .then((r) => r);
  }

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
          collection: collection || "default",
        },
        30000,
        undefined,
        this.flowId,
      )
      .then((r) => {
        // Return the response structure directly
        const result: Record<string, unknown> = {};
        if (r.data !== undefined) result.data = r.data;
        if (r.errors) result.errors = r.errors;
        return result;
      });
  }

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
      collection: collection || "default",
      limit: limit || 10,
    };

    if (indexName) {
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
        if (r.error) {
          throw new Error(r.error.message);
        }
        return r.matches || [];
      });
  }
}

/**
 * ConfigApi - Dedicated configuration management interface
 * Handles system configuration, prompts, and token cost tracking
 */
export class ConfigApi {
  api: BaseApi;

  constructor(api: BaseApi) {
    this.api = api;
  }

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
  }

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
  }

  /**
   * Updates configuration values
   */
  putConfig(values: { type: string; key: string; value: string }[]) {
    return this.api.makeRequest<ConfigRequest, ConfigResponse>(
      "config",
      {
        operation: "put",
        values: values,
      },
      60000,
    );
  }

  /**
   * Deletes configuration entries
   */
  deleteConfig(keys: { type: string; key: string }) {
    return this.api.makeRequest<ConfigRequest, ConfigResponse>(
      "config",
      {
        operation: "delete",
        keys: keys,
      },
      30000,
    );
  }

  // Specialized prompt management methods

  /**
   * Retrieves available prompt templates
   */
  getPrompts() {
    return this.getConfigAll().then((r) => {
      const config = r as Record<
        string,
        Record<string, Record<string, string>>
      >;
      return JSON.parse(config.config.prompt["template-index"]);
    });
  }

  /**
   * Retrieves a specific prompt template
   */
  getPrompt(id: string) {
    return this.getConfigAll().then((r) => {
      const config = r as Record<
        string,
        Record<string, Record<string, string>>
      >;
      return JSON.parse(config.config.prompt[`template.${id}`]);
    });
  }

  /**
   * Retrieves system prompt configuration
   */
  getSystemPrompt() {
    return this.getConfigAll().then((r) => {
      const config = r as Record<
        string,
        Record<string, Record<string, string>>
      >;
      return JSON.parse(config.config.prompt.system);
    });
  }

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
  }

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
      .then((r) => (r as RowsQueryResponse).values);
  }

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
        // Parse JSON values and restructure data
        const response = r as RowsQueryResponse;
        return (response.values || []).map((x: unknown) => {
          const item = x as Record<string, string>;
          return { key: item.key, value: JSON.parse(item.value) };
        });
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
  }
}

/**
 * KnowledgeApi - Manages knowledge graph cores and data
 * Knowledge cores appear to be collections of processed knowledge graph data
 */
export class KnowledgeApi {
  api: BaseApi;

  constructor(api: BaseApi) {
    this.api = api;
  }

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
      .then((r) => r.ids || []);
  }

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
        collection: collection || "default",
      },
      30000,
    );
  }

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
        collection: collection || "default",
      },
      30000,
    );
  }

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
      if (response.eos) {
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
        collection: collection || "default",
      },
      recv, // Stream handler
      30000,
    );
  }
}

/**
 * CollectionManagementApi - Manages collections for organizing documents
 * Provides operations for listing, creating, updating, and deleting collections
 */
export class CollectionManagementApi {
  api: BaseApi;

  constructor(api: BaseApi) {
    this.api = api;
  }

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

    if (tagFilter && tagFilter.length > 0) {
      request.tag_filter = tagFilter;
    }

    return this.api
      .makeRequest<
        Record<string, unknown>,
        Record<string, unknown>
      >("collection-management", request, 30000)
      .then((r) => r.collections || []);
  }

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
          r.collections &&
          Array.isArray(r.collections) &&
          r.collections.length > 0
        ) {
          return r.collections[0];
        }
        throw new Error("Failed to update collection");
      });
  }

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
  }
}

/**
 * Factory function to create a new TrustGraph WebSocket connection
 * This is the main entry point for using the TrustGraph API
 * @param user - User identifier for API requests
 * @param token - Optional authentication token for secure connections
 * @param socketUrl - Optional WebSocket URL (defaults to /api/socket for browser, provide full URL for Node.js)
 */
export const createTrustGraphSocket = (
  user: string,
  token?: string,
  socketUrl?: string,
): BaseApi => {
  return new BaseApi(user, token, socketUrl);
};
