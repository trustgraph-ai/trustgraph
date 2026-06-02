/**
 * Librarian service — manages document storage, metadata, and processing records.
 *
 * An AsyncProcessor (NOT FlowProcessor) that:
 * 1. Listens on librarian-request and collection-management-request topics
 * 2. Handles CRUD operations for documents, child documents, processing records
 * 3. Handles collection management (list, update, delete)
 * 4. Stores document files on disk, metadata in-memory (persisted to JSON)
 *
 * Python reference: trustgraph-flow/trustgraph/librarian/service/service.py
 */

import {
  errorMessage,
  makeAsyncProcessor,
  makeProcessorProgram,
  type ProcessorConfig,
  type AsyncProcessorRuntime,
  type BackendConsumer,
  type BackendProducer,
  topics,
  type LibrarianRequest,
  type LibrarianResponse,
  type CollectionManagementRequest,
  type CollectionManagementResponse,
  DocumentMetadata as DocumentMetadataSchema,
  type DocumentMetadata,
  ProcessingMetadata as ProcessingMetadataSchema,
  type ProcessingMetadata,
  Triple as TripleSchema,
} from "@trustgraph/base";
import type { Message } from "@trustgraph/base";
import { NodeRuntime } from "@effect/platform-node";
import { Clock, Config, DateTime, Duration, Effect, Layer, ManagedRuntime, Option, Random, SynchronizedRef } from "effect";
import * as S from "effect/Schema";
import { makeCollectionManager, type CollectionManager } from "./collection-manager.js";
import {
  ensureDirectory,
  joinPath,
  readBinaryFile,
  readTextFile,
  removePath,
  writeBinaryFile,
  writeTextFile,
} from "../runtime/effect-files.js";

export interface LibrarianServiceConfig extends ProcessorConfig {
  dataDir?: string;
}

interface UploadSession {
  id: string;
  documentMetadata: DocumentMetadata;
  totalSize: number;
  chunkSize: number;
  totalChunks: number;
  createdAt: string;
  chunks: Map<number, string>;
  user: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function optionalString(value: unknown): string | undefined {
  return typeof value === "string" && value.length > 0 ? value : undefined;
}

export class LibrarianServiceError extends S.TaggedErrorClass<LibrarianServiceError>()(
  "LibrarianServiceError",
  {
    message: S.String,
    operation: S.String,
  },
) {}

const librarianServiceError = (operation: string, cause: unknown): LibrarianServiceError =>
  LibrarianServiceError.make({
    operation,
    message: errorMessage(cause),
  });

function resolveDataDir(config: LibrarianServiceConfig): string {
  return config.dataDir ?? Effect.runSync(
    Config.string("LIBRARIAN_DATA_DIR").pipe(Config.withDefault("./data/librarian")),
  );
}

const currentEpochSeconds: Effect.Effect<number> = Clock.currentTimeMillis.pipe(
  Effect.map((millis) => Math.floor(millis / 1000)),
);

const currentIsoString: Effect.Effect<string> = DateTime.now.pipe(Effect.map(DateTime.formatIso));

const encodeJsonString = (operation: string, value: unknown): Effect.Effect<string, LibrarianServiceError> =>
  S.encodeUnknownEffect(S.UnknownFromJsonString)(value).pipe(
    Effect.mapError((cause) => librarianServiceError(operation, cause)),
  );

const PersistedCollectionSchema = S.Struct({
  user: S.String,
  collection: S.String,
  name: S.String,
  description: S.String,
  tags: S.Array(S.String).pipe(S.mutable),
});

const PersistedLibrarianStateSchema = S.Struct({
  documents: S.optionalKey(S.Record(S.String, DocumentMetadataSchema)),
  processing: S.optionalKey(S.Record(S.String, ProcessingMetadataSchema)),
  collections: S.optionalKey(PersistedCollectionSchema.pipe(S.Array, S.mutable)),
});
const PersistedLibrarianStateJsonSchema = PersistedLibrarianStateSchema.pipe(S.fromJsonString);
type PersistedLibrarianState = typeof PersistedLibrarianStateSchema.Type;

const DocumentMetadataTriplesSchema = TripleSchema.pipe(S.Array, S.mutable);
const decodeDocumentMetadataTriples = S.decodeUnknownOption(DocumentMetadataTriplesSchema);

const decodePersistedLibrarianState = (
  raw: string,
): Effect.Effect<PersistedLibrarianState, LibrarianServiceError> =>
  S.decodeUnknownEffect(PersistedLibrarianStateJsonSchema)(raw).pipe(
    Effect.mapError((cause) => librarianServiceError("persist-decode", cause)),
  );

const randomUuid: Effect.Effect<string> = Effect.gen(function* () {
  const bytes: number[] = [];
  for (let index = 0; index < 16; index += 1) {
    bytes.push(yield* Random.nextIntBetween(0, 255));
  }

  bytes[6] = (bytes[6]! & 0x0f) | 0x40;
  bytes[8] = (bytes[8]! & 0x3f) | 0x80;

  const hex = bytes.map((byte) => byte.toString(16).padStart(2, "0"));
  return [
    hex.slice(0, 4).join(""),
    hex.slice(4, 6).join(""),
    hex.slice(6, 8).join(""),
    hex.slice(8, 10).join(""),
    hex.slice(10, 16).join(""),
  ].join("-");
});

export interface LibrarianService extends AsyncProcessorRuntime<LibrarianServiceError> {
  state: SynchronizedRef.SynchronizedRef<LibrarianServiceState>;
  dataDir: string;
  persistPath: string;
  requestRecord: (request: LibrarianRequest) => Record<string, unknown>;
  documentId: (request: LibrarianRequest) => string | undefined;
  processingId: (request: LibrarianRequest) => string | undefined;
  documentMetadata: (request: LibrarianRequest) => Promise<DocumentMetadata | undefined>;
  processingMetadata: (request: LibrarianRequest) => Promise<ProcessingMetadata | undefined>;
  normaliseDocumentMetadata: (value: Record<string, unknown>) => Promise<DocumentMetadata>;
  publicDocument: (doc: DocumentMetadata) => DocumentMetadata;
  publicProcessing: (proc: ProcessingMetadata) => ProcessingMetadata;
  documentResponse: (doc: DocumentMetadata) => LibrarianResponse;
  documentsResponse: (docs: DocumentMetadata[]) => LibrarianResponse;
  processingResponse: (records: ProcessingMetadata[]) => LibrarianResponse;
  handleLibrarianMessage: (msg: Message<LibrarianRequest>) => Promise<void>;
  handleLibrarianOperation: (request: LibrarianRequest) => Promise<LibrarianResponse>;
  addDocument: (request: LibrarianRequest) => Promise<LibrarianResponse>;
  removeDocument: (request: LibrarianRequest) => Promise<LibrarianResponse>;
  updateDocument: (request: LibrarianRequest) => Promise<LibrarianResponse>;
  listDocuments: (request: LibrarianRequest) => LibrarianResponse;
  getDocumentMetadata: (request: LibrarianRequest) => Promise<LibrarianResponse>;
  getDocumentContent: (request: LibrarianRequest) => Promise<LibrarianResponse>;
  addChildDocument: (request: LibrarianRequest) => Promise<LibrarianResponse>;
  listChildren: (request: LibrarianRequest) => Promise<LibrarianResponse>;
  addProcessing: (request: LibrarianRequest) => Promise<LibrarianResponse>;
  removeProcessing: (request: LibrarianRequest) => Promise<LibrarianResponse>;
  listProcessing: (request: LibrarianRequest) => LibrarianResponse;
  beginUpload: (request: LibrarianRequest) => Promise<LibrarianResponse>;
  uploadChunk: (request: LibrarianRequest) => Promise<LibrarianResponse>;
  completeUpload: (request: LibrarianRequest) => Promise<LibrarianResponse>;
  getUploadStatus: (request: LibrarianRequest) => Promise<LibrarianResponse>;
  abortUpload: (request: LibrarianRequest) => Promise<LibrarianResponse>;
  listUploads: (request: LibrarianRequest) => Promise<LibrarianResponse>;
  streamDocument: (request: LibrarianRequest) => Promise<LibrarianResponse[]>;
  handleCollectionMessage: (msg: Message<CollectionManagementRequest>) => Promise<void>;
  handleCollectionOperation: (request: CollectionManagementRequest) => Promise<CollectionManagementResponse>;
  persist: () => Promise<void>;
  loadFromDisk: () => Promise<void>;
}

interface LibrarianServiceState {
  readonly documents: Map<string, DocumentMetadata>;
  readonly processing: Map<string, ProcessingMetadata>;
  readonly uploads: Map<string, UploadSession>;
  readonly collectionManager: CollectionManager;
  readonly libConsumer: BackendConsumer<LibrarianRequest> | null;
  readonly libProducer: BackendProducer<LibrarianResponse> | null;
  readonly colConsumer: BackendConsumer<CollectionManagementRequest> | null;
  readonly colProducer: BackendProducer<CollectionManagementResponse> | null;
}

const cloneDocuments = (source: Map<string, DocumentMetadata>): Map<string, DocumentMetadata> =>
  new Map(source);

const cloneProcessing = (source: Map<string, ProcessingMetadata>): Map<string, ProcessingMetadata> =>
  new Map(source);

const cloneUploads = (source: Map<string, UploadSession>): Map<string, UploadSession> =>
  new Map(source);

const cloneUploadSession = (session: UploadSession): UploadSession => ({
  ...session,
  chunks: new Map(session.chunks),
});

const cloneCollectionManager = (source: CollectionManager): CollectionManager => {
  const manager = makeCollectionManager();
  manager.loadFromJSON(source.toJSON());
  return manager;
};

const initialState = (): LibrarianServiceState => ({
  documents: new Map<string, DocumentMetadata>(),
  processing: new Map<string, ProcessingMetadata>(),
  uploads: new Map<string, UploadSession>(),
  collectionManager: makeCollectionManager(),
  libConsumer: null,
  libProducer: null,
  colConsumer: null,
  colProducer: null,
});

const stateSnapshot = (stateRef: SynchronizedRef.SynchronizedRef<LibrarianServiceState>): LibrarianServiceState =>
  SynchronizedRef.getUnsafe(stateRef);

const updateHandles = (
  stateRef: SynchronizedRef.SynchronizedRef<LibrarianServiceState>,
  handles: {
    readonly libConsumer?: BackendConsumer<LibrarianRequest> | null;
    readonly libProducer?: BackendProducer<LibrarianResponse> | null;
    readonly colConsumer?: BackendConsumer<CollectionManagementRequest> | null;
    readonly colProducer?: BackendProducer<CollectionManagementResponse> | null;
  },
) =>
  SynchronizedRef.updateAndGet(stateRef, (state) => ({
    ...state,
    libConsumer: handles.libConsumer === undefined ? state.libConsumer : handles.libConsumer,
    libProducer: handles.libProducer === undefined ? state.libProducer : handles.libProducer,
    colConsumer: handles.colConsumer === undefined ? state.colConsumer : handles.colConsumer,
    colProducer: handles.colProducer === undefined ? state.colProducer : handles.colProducer,
  }));

const modifyResult = <Value>(
  value: Value,
  state: LibrarianServiceState,
): readonly [Value, LibrarianServiceState] => [value, state];

const uploadBytesReceived = (session: UploadSession): number =>
  [...session.chunks.values()].reduce((sum, chunk) => sum + chunk.length, 0);

const consumeOnceEffect = (
  service: LibrarianService,
): Effect.Effect<void, LibrarianServiceError> =>
  Effect.gen(function* () {
    const state = yield* SynchronizedRef.get(service.state);
    const libConsumer = state.libConsumer;
    if (libConsumer === null) {
      return yield* librarianServiceError("consume", "Librarian consumer not started");
    }
    const colConsumer = state.colConsumer;
    if (colConsumer === null) {
      return yield* librarianServiceError("consume", "Collection consumer not started");
    }

    const libMsg = yield* Effect.tryPromise({
      try: () => libConsumer.receive(2000),
      catch: (cause) => librarianServiceError("librarian-receive", cause),
    });
    if (libMsg !== null) {
      yield* Effect.tryPromise({
        try: () => service.handleLibrarianMessage(libMsg),
        catch: (cause) => librarianServiceError("librarian-handle", cause),
      });
      yield* Effect.tryPromise({
        try: () => libConsumer.acknowledge(libMsg),
        catch: (cause) => librarianServiceError("librarian-acknowledge", cause),
      });
    }

    const colMsg = yield* Effect.tryPromise({
      try: () => colConsumer.receive(2000),
      catch: (cause) => librarianServiceError("collection-receive", cause),
    });
    if (colMsg !== null) {
      yield* Effect.tryPromise({
        try: () => service.handleCollectionMessage(colMsg),
        catch: (cause) => librarianServiceError("collection-handle", cause),
      });
      yield* Effect.tryPromise({
        try: () => colConsumer.acknowledge(colMsg),
        catch: (cause) => librarianServiceError("collection-acknowledge", cause),
      });
    }
  });

const runLibrarianServiceEffect = (
  service: LibrarianService,
): Effect.Effect<void, LibrarianServiceError> =>
  Effect.gen(function* () {
    yield* Effect.tryPromise({
      try: () => ensureDirectory(joinPath(service.dataDir, "docs")),
      catch: (cause) => librarianServiceError("ensure-data-dir", cause),
    });

    yield* Effect.tryPromise({
      try: () => service.loadFromDisk(),
      catch: (cause) => librarianServiceError("load", cause),
    });

    const libProducer = yield* Effect.tryPromise({
      try: () => service.pubsub.createProducer<LibrarianResponse>({
        topic: topics.librarianResponse,
      }),
      catch: (cause) => librarianServiceError("librarian-producer", cause),
    });
    const colProducer = yield* Effect.tryPromise({
      try: () => service.pubsub.createProducer<CollectionManagementResponse>({
        topic: topics.collectionManagementResponse,
      }),
      catch: (cause) => librarianServiceError("collection-producer", cause),
    });
    yield* updateHandles(service.state, { libProducer, colProducer });

    const libConsumer = yield* Effect.tryPromise({
      try: () => service.pubsub.createConsumer<LibrarianRequest>({
        topic: topics.librarianRequest,
        subscription: `${service.config.id}-librarian-request`,
      }),
      catch: (cause) => librarianServiceError("librarian-consumer", cause),
    });
    const colConsumer = yield* Effect.tryPromise({
      try: () => service.pubsub.createConsumer<CollectionManagementRequest>({
        topic: topics.collectionManagementRequest,
        subscription: `${service.config.id}-collection-management-request`,
      }),
      catch: (cause) => librarianServiceError("collection-consumer", cause),
    });
    yield* updateHandles(service.state, { libConsumer, colConsumer });

    yield* Effect.log(`[LibrarianService] Listening on ${topics.librarianRequest} and ${topics.collectionManagementRequest}`);

    yield* Effect.whileLoop({
      while: () => service.running,
      body: () =>
        consumeOnceEffect(service).pipe(
          Effect.catch((err) => {
            if (!service.running) return Effect.void;
            return Effect.logError("[LibrarianService] Error in consume loop", { error: err.message }).pipe(
              Effect.flatMap(() => Effect.sleep(Duration.millis(1000))),
            );
          }),
        ),
      step: () => undefined,
    });
  });

export function makeLibrarianService(config: LibrarianServiceConfig): LibrarianService {
  const state = SynchronizedRef.makeUnsafe(initialState());
  let service: LibrarianService | undefined;

  const getService = Effect.sync(() => service).pipe(
    Effect.flatMap((current) =>
      current === undefined
        ? Effect.fail(librarianServiceError("service", "Librarian service not initialized"))
        : Effect.succeed(current)
    ),
  );

  const base = makeAsyncProcessor<LibrarianServiceError>(config, {
    runEffect: () => getService.pipe(Effect.flatMap(runLibrarianServiceEffect)),
  });
  const baseStop = base.stop;
  const dataDir = resolveDataDir(config);
  const persistPath = joinPath(dataDir, "librarian-state.json");

  const getDocumentMetadataEffect = (request: LibrarianRequest): Effect.Effect<LibrarianResponse, LibrarianServiceError> =>
    Effect.gen(function* () {
      const current = yield* getService;
      const id = current.documentId(request);
      if (id === undefined || id.length === 0) {
        return yield* librarianServiceError("get-document-metadata", "get-document-metadata requires documentId");
      }

      const doc = (yield* SynchronizedRef.get(current.state)).documents.get(id);
      if (doc === undefined) {
        return yield* librarianServiceError("get-document-metadata", `Document not found: ${id}`);
      }

      return current.documentResponse(doc);
    });

  const listChildrenEffect = (request: LibrarianRequest): Effect.Effect<LibrarianResponse, LibrarianServiceError> =>
    Effect.gen(function* () {
      const current = yield* getService;
      const parentId = current.documentId(request);
      if (parentId === undefined || parentId.length === 0) {
        return yield* librarianServiceError("list-children", "list-children requires documentId");
      }

      const children: DocumentMetadata[] = [];
      const currentState = yield* SynchronizedRef.get(current.state);
      for (const doc of currentState.documents.values()) {
        if (doc.parentId === parentId) {
          children.push(doc);
        }
      }

      return current.documentsResponse(children);
    });

  const uploadChunkEffect = (request: LibrarianRequest): Effect.Effect<LibrarianResponse, LibrarianServiceError> =>
    Effect.gen(function* () {
      const current = yield* getService;
      const req = current.requestRecord(request);
      const uploadId = optionalString(req["upload-id"]);
      if (uploadId === undefined) {
        return yield* librarianServiceError("upload-chunk", "upload-chunk requires upload-id");
      }
      const chunkIndex = typeof req["chunk-index"] === "number" ? req["chunk-index"] : -1;
      const content = optionalString(req.content);
      if (content === undefined) {
        return yield* librarianServiceError("upload-chunk", "upload-chunk requires content");
      }

      return yield* SynchronizedRef.modifyEffect(current.state, (serviceState) => {
        const currentSession = serviceState.uploads.get(uploadId);
        if (currentSession === undefined) {
          return Effect.fail(librarianServiceError("upload-chunk", `Upload not found: ${uploadId}`));
        }
        if (!Number.isInteger(chunkIndex) || chunkIndex < 0 || chunkIndex >= currentSession.totalChunks) {
          return Effect.fail(librarianServiceError("upload-chunk", "upload-chunk requires a valid chunk-index"));
        }

        const session = cloneUploadSession(currentSession);
        session.chunks.set(chunkIndex, content);
        const uploads = cloneUploads(serviceState.uploads);
        uploads.set(uploadId, session);

        return Effect.succeed(modifyResult({
          "upload-id": uploadId,
          "chunk-index": chunkIndex,
          "chunks-received": session.chunks.size,
          "total-chunks": session.totalChunks,
          "bytes-received": uploadBytesReceived(session),
          "total-bytes": session.totalSize,
        }, {
          ...serviceState,
          uploads,
        }));
      });
    });

  const getUploadStatusEffect = (request: LibrarianRequest): Effect.Effect<LibrarianResponse, LibrarianServiceError> =>
    Effect.gen(function* () {
      const current = yield* getService;
      const uploadId = optionalString(current.requestRecord(request)["upload-id"]);
      if (uploadId === undefined) {
        return yield* librarianServiceError("get-upload-status", "get-upload-status requires upload-id");
      }
      const session = (yield* SynchronizedRef.get(current.state)).uploads.get(uploadId);
      if (session === undefined) {
        return yield* librarianServiceError("get-upload-status", `Upload not found: ${uploadId}`);
      }
      const receivedChunks = [...session.chunks.keys()].sort((a, b) => a - b);
      const receivedSet = new Set(receivedChunks);
      const missingChunks = Array.from({ length: session.totalChunks }, (_, i) => i).filter((i) => !receivedSet.has(i));
      return {
        "upload-id": uploadId,
        "upload-state": "in-progress",
        "chunks-received": session.chunks.size,
        "total-chunks": session.totalChunks,
        "received-chunks": receivedChunks,
        "missing-chunks": missingChunks,
        "bytes-received": uploadBytesReceived(session),
        "total-bytes": session.totalSize,
      };
    });

  const abortUploadEffect = (request: LibrarianRequest): Effect.Effect<LibrarianResponse, LibrarianServiceError> =>
    Effect.gen(function* () {
      const current = yield* getService;
      const uploadId = optionalString(current.requestRecord(request)["upload-id"]);
      if (uploadId === undefined) {
        return yield* librarianServiceError("abort-upload", "abort-upload requires upload-id");
      }
      return yield* SynchronizedRef.modifyEffect(current.state, (serviceState) => {
        if (!serviceState.uploads.has(uploadId)) {
          return Effect.fail(librarianServiceError("abort-upload", `Upload not found: ${uploadId}`));
        }
        const uploads = cloneUploads(serviceState.uploads);
        uploads.delete(uploadId);
        return Effect.succeed(modifyResult({}, {
          ...serviceState,
          uploads,
        }));
      });
    });

  const librarianService: LibrarianService = Object.assign(base, {
      state,
      dataDir,
      persistPath,

      // ---------- Librarian message handling ----------

      requestRecord: function(this: LibrarianService, request: LibrarianRequest): Record<string, unknown> {
        return request;

        },



      documentId: function(this: LibrarianService, request: LibrarianRequest): string | undefined {
        const req = this.requestRecord(request);
        return optionalString(req.documentId) ?? optionalString(req["document-id"]);

        },



      processingId: function(this: LibrarianService, request: LibrarianRequest): string | undefined {
        const req = this.requestRecord(request);
        return optionalString(req.processingId) ?? optionalString(req["processing-id"]);

        },



      documentMetadata: function(this: LibrarianService, request: LibrarianRequest): Promise<DocumentMetadata | undefined> {
        const req = this.requestRecord(request);
        const value = req.documentMetadata ?? req["document-metadata"];
        if (!isRecord(value)) return Promise.resolve(undefined);
        return this.normaliseDocumentMetadata(value);

        },



      processingMetadata: function(this: LibrarianService, request: LibrarianRequest): Promise<ProcessingMetadata | undefined> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const req = service.requestRecord(request);
            const value = req.processingMetadata ?? req["processing-metadata"];
            if (!isRecord(value)) return undefined;
            const documentId = optionalString(value.documentId) ?? optionalString(value["document-id"]) ?? "";
            const id = optionalString(value.id) ?? (yield* randomUuid);
            const time = typeof value.time === "number" ? value.time : yield* currentEpochSeconds;
            return {
              id,
              documentId,
              "document-id": documentId,
              time,
              flow: optionalString(value.flow) ?? "default",
              user: optionalString(value.user) ?? optionalString(service.requestRecord(request).user) ?? "default",
              collection: optionalString(value.collection) ?? optionalString(service.requestRecord(request).collection) ?? "default",
              tags: Array.isArray(value.tags) ? value.tags.filter((tag): tag is string => typeof tag === "string") : [],
            };
          }),
        );

        },



      normaliseDocumentMetadata: function(this: LibrarianService, value: Record<string, unknown>): Promise<DocumentMetadata> {
        return Effect.runPromise(
          Effect.gen(function* () {
            const id = optionalString(value.id) ?? (yield* randomUuid);
            const parentId = optionalString(value.parentId) ?? optionalString(value["parent-id"]);
            const documentType = optionalString(value.documentType) ?? optionalString(value["document-type"]) ?? "source";
            const time = typeof value.time === "number" ? value.time : yield* currentEpochSeconds;
            const metadata = Array.isArray(value.metadata)
              ? Option.getOrUndefined(decodeDocumentMetadataTriples(value.metadata))
              : undefined;
            return {
              id,
              time,
              kind: optionalString(value.kind) ?? "application/octet-stream",
              title: optionalString(value.title) ?? "",
              comments: optionalString(value.comments) ?? "",
              user: optionalString(value.user) ?? "default",
              tags: Array.isArray(value.tags) ? value.tags.filter((tag): tag is string => typeof tag === "string") : [],
              ...(parentId !== undefined ? { parentId, "parent-id": parentId } : {}),
              documentType,
              "document-type": documentType,
              ...(metadata === undefined ? {} : { metadata }),
            };
          }),
        );

        },



      publicDocument: function(this: LibrarianService, doc: DocumentMetadata): DocumentMetadata {
        const parentId = doc.parentId ?? doc["parent-id"];
        const documentType = doc.documentType ?? doc["document-type"] ?? "source";
        return {
          ...doc,
          ...(parentId !== undefined ? { parentId, "parent-id": parentId } : {}),
          documentType,
          "document-type": documentType,
        };

        },



      publicProcessing: function(this: LibrarianService, proc: ProcessingMetadata): ProcessingMetadata {
        const documentId = proc.documentId ?? proc["document-id"] ?? "";
        return {
          ...proc,
          documentId,
          "document-id": documentId,
        };

        },



      documentResponse: function(this: LibrarianService, doc: DocumentMetadata): LibrarianResponse {
        const publicDoc = this.publicDocument(doc);
        return {
          documentMetadata: publicDoc,
          "document-metadata": publicDoc,
        };

        },



      documentsResponse: function(this: LibrarianService, docs: DocumentMetadata[]): LibrarianResponse {
        const publicDocs = docs.map((doc) => this.publicDocument(doc));
        return {
          documents: publicDocs,
          "document-metadatas": publicDocs,
        };

        },



      processingResponse: function(this: LibrarianService, records: ProcessingMetadata[]): LibrarianResponse {
        const publicRecords = records.map((proc) => this.publicProcessing(proc));
        return {
          processing: publicRecords,
          "processing-metadata": publicRecords,
          "processing-metadatas": publicRecords,
        };

        },



      handleLibrarianMessage: function(this: LibrarianService, msg: Message<LibrarianRequest>): Promise<void> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const request = msg.value();
            const props = msg.properties();
            const requestId = props.id;

            if (requestId === undefined || requestId.length === 0) {
              yield* Effect.logWarning("[LibrarianService] Received request without id, ignoring");
              return;
            }

            const sendResponse = (response: LibrarianResponse): Effect.Effect<void, LibrarianServiceError> =>
              Effect.gen(function* () {
                const producer = (yield* SynchronizedRef.get(service.state)).libProducer;
                if (producer === null) {
                  return yield* librarianServiceError("librarian-respond", "Librarian producer not started");
                }
                yield* Effect.tryPromise({
                  try: () => producer.send(response, { id: requestId }),
                  catch: (cause) => librarianServiceError("librarian-respond", cause),
                });
              });

            yield* Effect.gen(function* () {
              if (request.operation === "stream-document") {
                const responses = yield* Effect.tryPromise<LibrarianResponse[], LibrarianServiceError>({
                  try: () => service.streamDocument(request),
                  catch: (cause) => librarianServiceError("stream-document", cause),
                });
                for (const response of responses) {
                  yield* sendResponse(response);
                }
                return;
              }

              const response = yield* Effect.tryPromise<LibrarianResponse, LibrarianServiceError>({
                try: () => service.handleLibrarianOperation(request),
                catch: (cause) => librarianServiceError("librarian-operation", cause),
              });
              yield* sendResponse(response);
            }).pipe(
              Effect.catch((err) =>
                sendResponse({
                  error: { type: "librarian-error", message: err.message },
                }),
              ),
            );
          }),
        );

        },



      handleLibrarianOperation: function(this: LibrarianService, request: LibrarianRequest): Promise<LibrarianResponse> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            switch (request.operation) {
              case "add-document":
                return yield* Effect.tryPromise({
                  try: () => service.addDocument(request),
                  catch: (cause) => librarianServiceError("add-document", cause),
                });
              case "remove-document":
                return yield* Effect.tryPromise({
                  try: () => service.removeDocument(request),
                  catch: (cause) => librarianServiceError("remove-document", cause),
                });
              case "update-document":
                return yield* Effect.tryPromise({
                  try: () => service.updateDocument(request),
                  catch: (cause) => librarianServiceError("update-document", cause),
                });
              case "list-documents":
                return yield* Effect.try({
                  try: () => service.listDocuments(request),
                  catch: (cause) => librarianServiceError("list-documents", cause),
                });
              case "get-document-metadata":
                return yield* getDocumentMetadataEffect(request);
              case "get-document-content":
                return yield* Effect.tryPromise({
                  try: () => service.getDocumentContent(request),
                  catch: (cause) => librarianServiceError("get-document-content", cause),
                });
              case "add-child-document":
                return yield* Effect.tryPromise({
                  try: () => service.addChildDocument(request),
                  catch: (cause) => librarianServiceError("add-child-document", cause),
                });
              case "list-children":
                return yield* listChildrenEffect(request);
              case "add-processing":
                return yield* Effect.tryPromise({
                  try: () => service.addProcessing(request),
                  catch: (cause) => librarianServiceError("add-processing", cause),
                });
              case "remove-processing":
                return yield* Effect.tryPromise({
                  try: () => service.removeProcessing(request),
                  catch: (cause) => librarianServiceError("remove-processing", cause),
                });
              case "list-processing":
                return yield* Effect.try({
                  try: () => service.listProcessing(request),
                  catch: (cause) => librarianServiceError("list-processing", cause),
                });
              case "begin-upload":
                return yield* Effect.tryPromise({
                  try: () => service.beginUpload(request),
                  catch: (cause) => librarianServiceError("begin-upload", cause),
                });
              case "upload-chunk":
                return yield* uploadChunkEffect(request);
              case "complete-upload":
                return yield* Effect.tryPromise({
                  try: () => service.completeUpload(request),
                  catch: (cause) => librarianServiceError("complete-upload", cause),
                });
              case "get-upload-status":
                return yield* getUploadStatusEffect(request);
              case "abort-upload":
                return yield* abortUploadEffect(request);
              case "list-uploads":
                return yield* Effect.tryPromise({
                  try: () => service.listUploads(request),
                  catch: (cause) => librarianServiceError("list-uploads", cause),
                });
              case "stream-document":
                return yield* librarianServiceError("stream-document", "stream-document must be handled as a streaming operation");
              default:
                return yield* librarianServiceError("operation", `Unknown librarian operation: ${String(request.operation)}`);
            }
          }),
        );

        },



      addDocument: function(this: LibrarianService, request: LibrarianRequest): Promise<LibrarianResponse> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const meta = yield* Effect.tryPromise<DocumentMetadata | undefined, LibrarianServiceError>({
              try: () => service.documentMetadata(request),
              catch: (cause) => librarianServiceError("add-document-metadata", cause),
            });
            if (meta === undefined) return yield* librarianServiceError("add-document", "add-document requires documentMetadata");

            const id = meta.id;
            const now = yield* currentEpochSeconds;

            const doc: DocumentMetadata = {
              ...meta,
              id,
              time: now,
            };

            yield* SynchronizedRef.update(service.state, (serviceState) => {
              const documents = cloneDocuments(serviceState.documents);
              documents.set(id, doc);
              return {
                ...serviceState,
                documents,
              };
            });

            // Store file content if provided
            if (request.content !== undefined && request.content.length > 0) {
              const filePath = joinPath(service.dataDir, "docs", `${id}.bin`);
              const buf = Buffer.from(request.content, "base64");
              yield* Effect.tryPromise({
                try: () => writeBinaryFile(filePath, buf),
                catch: (cause) => librarianServiceError("add-document-write", cause),
              });
            }

            yield* Effect.tryPromise({
              try: () => service.persist(),
              catch: (cause) => librarianServiceError("add-document-persist", cause),
            });
            yield* Effect.log(`[LibrarianService] Added document ${id}: ${doc.title}`);

            return service.documentResponse(doc);
          }),
        );

        },



      removeDocument: function(this: LibrarianService, request: LibrarianRequest): Promise<LibrarianResponse> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const id = service.documentId(request);
            if (id === undefined || id.length === 0) {
              return yield* librarianServiceError("remove-document", "remove-document requires documentId");
            }

            const removal = yield* SynchronizedRef.modifyEffect(service.state, (serviceState) => {
              const childIds = [...serviceState.documents.entries()]
                .filter(([, doc]) => doc.parentId === id)
                .map(([childId]) => childId);
              const procIds = [...serviceState.processing.entries()]
                .filter(([, proc]) => proc.documentId === id)
                .map(([procId]) => procId);

              const documents = cloneDocuments(serviceState.documents);
              documents.delete(id);
              for (const childId of childIds) {
                documents.delete(childId);
              }

              const processing = cloneProcessing(serviceState.processing);
              for (const procId of procIds) {
                processing.delete(procId);
              }

              return Effect.succeed(modifyResult({ childIds, procIds }, {
                ...serviceState,
                documents,
                processing,
              }));
            });

            // Remove the file
            yield* Effect.tryPromise({
              try: () => removePath(joinPath(service.dataDir, "docs", `${id}.bin`)),
              catch: (cause) => librarianServiceError("remove-document-file", cause),
            }).pipe(Effect.orElseSucceed(() => undefined));

            // Cascade: remove children
            for (const childId of removal.childIds) {
              yield* Effect.tryPromise({
                try: () => removePath(joinPath(service.dataDir, "docs", `${childId}.bin`)),
                catch: (cause) => librarianServiceError("remove-child-file", cause),
              }).pipe(Effect.orElseSucceed(() => undefined));
            }

            yield* Effect.tryPromise({
              try: () => service.persist(),
              catch: (cause) => librarianServiceError("remove-document-persist", cause),
            });
            yield* Effect.log(`[LibrarianService] Removed document ${id} (cascade: ${removal.childIds.length} children, ${removal.procIds.length} processing)`);

            return {};
          }),
        );

        },



      updateDocument: function(this: LibrarianService, request: LibrarianRequest): Promise<LibrarianResponse> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const meta = yield* Effect.tryPromise<DocumentMetadata | undefined, LibrarianServiceError>({
              try: () => service.documentMetadata(request),
              catch: (cause) => librarianServiceError("update-document-metadata", cause),
            });
            const id = service.documentId(request) ?? meta?.id;
            if (id === undefined || id.length === 0) {
              return yield* librarianServiceError("update-document", "update-document requires documentId");
            }
            if (meta === undefined) return yield* librarianServiceError("update-document", "update-document requires documentMetadata");

            const doc = yield* SynchronizedRef.modifyEffect(service.state, (serviceState) => {
              const existing = serviceState.documents.get(id);
              if (existing === undefined) {
                return Effect.fail(librarianServiceError("update-document", `Document not found: ${id}`));
              }
              const next: DocumentMetadata = service.publicDocument({
                ...existing,
                ...meta,
                id,
                time: meta.time ?? existing.time,
              });
              const documents = cloneDocuments(serviceState.documents);
              documents.set(id, next);
              return Effect.succeed(modifyResult(next, {
                ...serviceState,
                documents,
              }));
            });
            yield* Effect.tryPromise({
              try: () => service.persist(),
              catch: (cause) => librarianServiceError("update-document-persist", cause),
            });
            return service.documentResponse(doc);
          }),
        );

        },



      listDocuments: function(this: LibrarianService, request: LibrarianRequest): LibrarianResponse {
        const user = request.user ?? "";
        const includeChildren = this.requestRecord(request)["include-children"] === true;
        const docs: DocumentMetadata[] = [];
        const serviceState = this.state.pipe(stateSnapshot);

        for (const doc of serviceState.documents.values()) {
          // Filter by user
          if (user.length > 0 && doc.user !== user) continue;
          // Exclude children (only top-level documents) unless explicitly requested
          if (!includeChildren && doc.parentId !== undefined && doc.parentId.length > 0) continue;
          docs.push(doc);
        }

        return this.documentsResponse(docs);

        },



      getDocumentMetadata: function(this: LibrarianService, request: LibrarianRequest): Promise<LibrarianResponse> {
        return Effect.runPromise(getDocumentMetadataEffect(request));

        },



      getDocumentContent: function(this: LibrarianService, request: LibrarianRequest): Promise<LibrarianResponse> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const id = service.documentId(request);
            if (id === undefined || id.length === 0) {
              return yield* librarianServiceError("get-document-content", "get-document-content requires documentId");
            }

            const doc = (yield* SynchronizedRef.get(service.state)).documents.get(id);
            if (doc === undefined) return yield* librarianServiceError("get-document-content", `Document not found: ${id}`);

            const filePath = joinPath(service.dataDir, "docs", `${id}.bin`);
            const buf = yield* Effect.tryPromise({
              try: () => readBinaryFile(filePath),
              catch: () => librarianServiceError("get-document-content", `Document content not found on disk: ${id}`),
            });
            const content = Buffer.from(buf).toString("base64");
            return { ...service.documentResponse(doc), content };
          }),
        );

        },



      addChildDocument: function(this: LibrarianService, request: LibrarianRequest): Promise<LibrarianResponse> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const meta = yield* Effect.tryPromise<DocumentMetadata | undefined, LibrarianServiceError>({
              try: () => service.documentMetadata(request),
              catch: (cause) => librarianServiceError("add-child-document-metadata", cause),
            });
            if (meta === undefined) {
              return yield* librarianServiceError("add-child-document", "add-child-document requires documentMetadata");
            }
            if (meta.parentId === undefined || meta.parentId.length === 0) {
              return yield* librarianServiceError("add-child-document", "add-child-document requires parentId in metadata");
            }
            const parentId = meta.parentId;

            const id = meta.id;
            const now = yield* currentEpochSeconds;

            const doc: DocumentMetadata = {
              ...meta,
              id,
              time: now,
            };

            yield* SynchronizedRef.modifyEffect(service.state, (serviceState) => {
              if (Boolean(serviceState.documents.has(parentId)) === false) {
                return Effect.fail(librarianServiceError("add-child-document", `Parent document not found: ${parentId}`));
              }
              const documents = cloneDocuments(serviceState.documents);
              documents.set(id, doc);
              return Effect.succeed(modifyResult(undefined, {
                ...serviceState,
                documents,
              }));
            });

            // Store file content if provided
            if (request.content !== undefined && request.content.length > 0) {
              const filePath = joinPath(service.dataDir, "docs", `${id}.bin`);
              const buf = Buffer.from(request.content, "base64");
              yield* Effect.tryPromise({
                try: () => writeBinaryFile(filePath, buf),
                catch: (cause) => librarianServiceError("add-child-document-write", cause),
              });
            }

            yield* Effect.tryPromise({
              try: () => service.persist(),
              catch: (cause) => librarianServiceError("add-child-document-persist", cause),
            });
            yield* Effect.log(`[LibrarianService] Added child document ${id} (parent: ${parentId})`);

            return service.documentResponse(doc);
          }),
        );

        },



      listChildren: function(this: LibrarianService, request: LibrarianRequest): Promise<LibrarianResponse> {
        return Effect.runPromise(listChildrenEffect(request));

        },



      addProcessing: function(this: LibrarianService, request: LibrarianRequest): Promise<LibrarianResponse> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const proc = yield* Effect.tryPromise<ProcessingMetadata | undefined, LibrarianServiceError>({
              try: () => service.processingMetadata(request),
              catch: (cause) => librarianServiceError("add-processing-metadata", cause),
            });
            if (proc === undefined) return yield* librarianServiceError("add-processing", "add-processing requires processingMetadata");

            const id = proc.id;
            const now = yield* currentEpochSeconds;

            const record: ProcessingMetadata = {
              ...proc,
              id,
              time: now,
            };

            yield* SynchronizedRef.update(service.state, (serviceState) => {
              const processing = cloneProcessing(serviceState.processing);
              processing.set(id, record);
              return {
                ...serviceState,
                processing,
              };
            });
            yield* Effect.tryPromise({
              try: () => service.persist(),
              catch: (cause) => librarianServiceError("add-processing-persist", cause),
            });

            yield* Effect.log(`[LibrarianService] Added processing ${id} for document ${proc.documentId}`);
            return service.processingResponse([record]);
          }),
        );

        },



      removeProcessing: function(this: LibrarianService, request: LibrarianRequest): Promise<LibrarianResponse> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const id = service.processingId(request);
            if (id === undefined || id.length === 0) {
              return yield* librarianServiceError("remove-processing", "remove-processing requires processingId");
            }

            yield* SynchronizedRef.update(service.state, (serviceState) => {
              const processing = cloneProcessing(serviceState.processing);
              processing.delete(id);
              return {
                ...serviceState,
                processing,
              };
            });
            yield* Effect.tryPromise({
              try: () => service.persist(),
              catch: (cause) => librarianServiceError("remove-processing-persist", cause),
            });

            return {};
          }),
        );

        },



      listProcessing: function(this: LibrarianService, request: LibrarianRequest): LibrarianResponse {
        const documentId = this.documentId(request);
        const records: ProcessingMetadata[] = [];
        const serviceState = this.state.pipe(stateSnapshot);

        for (const proc of serviceState.processing.values()) {
          const procDocumentId = proc.documentId ?? proc["document-id"];
          if (documentId !== undefined && documentId.length > 0 && procDocumentId !== documentId) {
            continue;
          }
          records.push(proc);
        }

        return this.processingResponse(records);

        },



      beginUpload: function(this: LibrarianService, request: LibrarianRequest): Promise<LibrarianResponse> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const meta = yield* Effect.tryPromise<DocumentMetadata | undefined, LibrarianServiceError>({
              try: () => service.documentMetadata(request),
              catch: (cause) => librarianServiceError("begin-upload-metadata", cause),
            });
            if (meta === undefined) return yield* librarianServiceError("begin-upload", "begin-upload requires documentMetadata");
            const req = service.requestRecord(request);
            const totalSize = typeof req["total-size"] === "number" ? req["total-size"] : 0;
            if (totalSize <= 0) return yield* librarianServiceError("begin-upload", "begin-upload requires total-size");
            const chunkSize = typeof req["chunk-size"] === "number" && req["chunk-size"] > 0
              ? req["chunk-size"]
              : 3 * 1024 * 1024;
            const totalChunks = Math.max(1, Math.ceil(totalSize / chunkSize));
            const uploadId = yield* randomUuid;
            const createdAt = yield* currentIsoString;

            const session: UploadSession = {
              id: uploadId,
              documentMetadata: meta,
              totalSize,
              chunkSize,
              totalChunks,
              createdAt,
              chunks: new Map<number, string>(),
              user: meta.user ?? optionalString(req.user) ?? "default",
            };

            yield* SynchronizedRef.update(service.state, (serviceState) => {
              const uploads = cloneUploads(serviceState.uploads);
              uploads.set(uploadId, session);
              return {
                ...serviceState,
                uploads,
              };
            });

            return {
              "upload-id": uploadId,
              "chunk-size": chunkSize,
              "total-chunks": totalChunks,
            };
          }),
        );

        },



      uploadChunk: function(this: LibrarianService, request: LibrarianRequest): Promise<LibrarianResponse> {
        return Effect.runPromise(uploadChunkEffect(request));

        },



      completeUpload: function(this: LibrarianService, request: LibrarianRequest): Promise<LibrarianResponse> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const uploadId = optionalString(service.requestRecord(request)["upload-id"]);
            if (uploadId === undefined) return yield* librarianServiceError("complete-upload", "complete-upload requires upload-id");
            const session = (yield* SynchronizedRef.get(service.state)).uploads.get(uploadId);
            if (session === undefined) return yield* librarianServiceError("complete-upload", `Upload not found: ${uploadId}`);
            if (session.chunks.size !== session.totalChunks) {
              return yield* librarianServiceError("complete-upload", `Upload incomplete: ${session.chunks.size}/${session.totalChunks} chunks received`);
            }

            const content = Array.from({ length: session.totalChunks }, (_, i) => session.chunks.get(i) ?? "").join("");
            const response = yield* Effect.tryPromise<LibrarianResponse, LibrarianServiceError>({
              try: () => service.addDocument({
                operation: "add-document",
                documentMetadata: session.documentMetadata,
                "document-metadata": session.documentMetadata,
                content,
                user: session.user,
              }),
              catch: (cause) => librarianServiceError("complete-upload-add-document", cause),
            });
            yield* SynchronizedRef.update(service.state, (serviceState) => {
              const uploads = cloneUploads(serviceState.uploads);
              uploads.delete(uploadId);
              return {
                ...serviceState,
                uploads,
              };
            });
            const documentId = response.documentMetadata?.id ?? response["document-metadata"]?.id ?? session.documentMetadata.id;
            return {
              ...response,
              "document-id": documentId,
              "object-id": documentId,
            };
          }),
        );

        },



      getUploadStatus: function(this: LibrarianService, request: LibrarianRequest): Promise<LibrarianResponse> {
        return Effect.runPromise(getUploadStatusEffect(request));

        },



      abortUpload: function(this: LibrarianService, request: LibrarianRequest): Promise<LibrarianResponse> {
        return Effect.runPromise(abortUploadEffect(request));

        },



      listUploads: function(this: LibrarianService, request: LibrarianRequest): Promise<LibrarianResponse> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const user = optionalString(service.requestRecord(request).user);
            const sessions = [];
            const serviceState = yield* SynchronizedRef.get(service.state);
            for (const session of serviceState.uploads.values()) {
              if (user !== undefined && session.user !== user) continue;
              const documentMetadataJson = yield* encodeJsonString(
                "list-uploads-document-metadata",
                service.publicDocument(session.documentMetadata),
              );
              sessions.push({
                "upload-id": session.id,
                "document-id": session.documentMetadata.id,
                "document-metadata-json": documentMetadataJson,
                "total-size": session.totalSize,
                "chunk-size": session.chunkSize,
                "total-chunks": session.totalChunks,
                "chunks-received": session.chunks.size,
                "created-at": session.createdAt,
              });
            }
            return { "upload-sessions": sessions };
          }),
        );

        },



      streamDocument: function(this: LibrarianService, request: LibrarianRequest): Promise<LibrarianResponse[]> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const id = service.documentId(request);
            if (id === undefined) return yield* librarianServiceError("stream-document", "stream-document requires documentId");
            const req = service.requestRecord(request);
            const chunkSize = typeof req["chunk-size"] === "number" && req["chunk-size"] > 0
              ? req["chunk-size"]
              : 1024 * 1024;
            const filePath = joinPath(service.dataDir, "docs", `${id}.bin`);
            const buf = yield* Effect.tryPromise({
              try: () => readBinaryFile(filePath),
              catch: (cause) => librarianServiceError("stream-document-read", cause),
            });
            const base64 = Buffer.from(buf).toString("base64");
            const totalChunks = Math.max(1, Math.ceil(base64.length / chunkSize));
            return Array.from({ length: totalChunks }, (_, index) => {
              const start = index * chunkSize;
              const content = base64.slice(start, start + chunkSize);
              return {
                content,
                "chunk-index": index,
                "total-chunks": totalChunks,
                eos: index === totalChunks - 1,
              };
            });
          }),
        );

        },



      // ---------- Collection management ----------

      handleCollectionMessage: function(this: LibrarianService, msg: Message<CollectionManagementRequest>): Promise<void> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const request = msg.value();
            const props = msg.properties();
            const requestId = props.id;

            if (requestId === undefined || requestId.length === 0) {
              yield* Effect.logWarning("[LibrarianService] Received collection request without id, ignoring");
              return;
            }

            const sendResponse = (response: CollectionManagementResponse): Effect.Effect<void, LibrarianServiceError> =>
              Effect.gen(function* () {
                const producer = (yield* SynchronizedRef.get(service.state)).colProducer;
                if (producer === null) {
                  return yield* librarianServiceError("collection-respond", "Collection producer not started");
                }
                yield* Effect.tryPromise({
                  try: () => producer.send(response, { id: requestId }),
                  catch: (cause) => librarianServiceError("collection-respond", cause),
                });
              });

            yield* Effect.gen(function* () {
              const response = yield* Effect.tryPromise<CollectionManagementResponse, LibrarianServiceError>({
                try: () => service.handleCollectionOperation(request),
                catch: (cause) => librarianServiceError("collection-operation", cause),
              });
              yield* sendResponse(response);
            }).pipe(
              Effect.catch((err) =>
                sendResponse({
                  error: { type: "collection-error", message: err.message },
                }),
              ),
            );
          }),
        );

        },



      handleCollectionOperation: function(this: LibrarianService, request: CollectionManagementRequest): Promise<CollectionManagementResponse> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            switch (request.operation) {
              case "list-collections": {
                const user = request.user ?? "";
                const collections = (yield* SynchronizedRef.get(service.state)).collectionManager.listCollections(user);
                return { collections };
              }

              case "update-collection": {
                const user = request.user ?? "";
                const collection = request.collection ?? "";
                const name = request.name ?? collection;
                const description = request.description ?? "";
                const tags = request.tags ?? [];

                const collections = yield* SynchronizedRef.modifyEffect(service.state, (serviceState) => {
                  const collectionManager = cloneCollectionManager(serviceState.collectionManager);
                  collectionManager.updateCollection(user, collection, name, description, tags);
                  return Effect.succeed(modifyResult(collectionManager.listCollections(user), {
                    ...serviceState,
                    collectionManager,
                  }));
                });
                yield* Effect.tryPromise({
                  try: () => service.persist(),
                  catch: (cause) => librarianServiceError("update-collection-persist", cause),
                });

                return { collections };
              }

              case "delete-collection": {
                const user = request.user ?? "";
                const collection = request.collection ?? "";

                yield* SynchronizedRef.update(service.state, (serviceState) => {
                  const collectionManager = cloneCollectionManager(serviceState.collectionManager);
                  collectionManager.deleteCollection(user, collection);
                  return {
                    ...serviceState,
                    collectionManager,
                  };
                });
                yield* Effect.tryPromise({
                  try: () => service.persist(),
                  catch: (cause) => librarianServiceError("delete-collection-persist", cause),
                });

                return {};
              }

              default:
                return yield* librarianServiceError("collection-operation", `Unknown collection operation: ${String(request.operation)}`);
            }
          }),
        );

        },



      // ---------- Persistence ----------

      persist: function(this: LibrarianService): Promise<void> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const serviceState = yield* SynchronizedRef.get(service.state);
            const data = {
              documents: Object.fromEntries(serviceState.documents),
              processing: Object.fromEntries(serviceState.processing),
              collections: serviceState.collectionManager.toJSON(),
            };

            const json = yield* encodeJsonString("persist-encode", data);
            yield* Effect.tryPromise({
              try: () => writeTextFile(service.persistPath, json),
              catch: (cause) => librarianServiceError("persist-write", cause),
            });
          }).pipe(
            Effect.catch((err) =>
              Effect.logError("[LibrarianService] Failed to persist state", { error: err.message }),
            ),
          ),
        );

        },



      loadFromDisk: function(this: LibrarianService): Promise<void> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const parsed = yield* Effect.gen(function* () {
              const raw = yield* Effect.tryPromise({
                try: () => readTextFile(service.persistPath),
                catch: (cause) => librarianServiceError("persist-read", cause),
              });
              return yield* decodePersistedLibrarianState(raw);
            }).pipe(
              Effect.catch(() =>
                Effect.log("[LibrarianService] No persisted state found, starting fresh").pipe(
                  Effect.flatMap(() => Effect.succeed<PersistedLibrarianState | null>(null)),
                ),
              ),
            );

            if (parsed === null) return;

            const documents = new Map<string, DocumentMetadata>();
            if (parsed.documents !== undefined) {
              for (const [id, doc] of Object.entries(parsed.documents)) {
                documents.set(id, service.publicDocument(doc));
              }
            }

            const processing = new Map<string, ProcessingMetadata>();
            if (parsed.processing !== undefined) {
              for (const [id, proc] of Object.entries(parsed.processing)) {
                processing.set(id, service.publicProcessing(proc));
              }
            }

            const collectionManager = makeCollectionManager();
            if (parsed.collections !== undefined) {
              collectionManager.loadFromJSON(parsed.collections);
            }

            yield* SynchronizedRef.update(service.state, (serviceState) => ({
              ...serviceState,
              documents,
              processing,
              collectionManager,
            }));

            yield* Effect.log(
              `[LibrarianService] Loaded persisted state (documents=${documents.size}, processing=${processing.size})`,
            );
          }),
        );

        },



      stop: function(this: LibrarianService): Promise<void> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const serviceState = yield* SynchronizedRef.get(service.state);
            const libConsumer = serviceState.libConsumer;
            if (libConsumer !== null) {
              yield* Effect.tryPromise({
                try: () => libConsumer.close(),
                catch: (cause) => librarianServiceError("close-librarian-consumer", cause),
              });
            }
            const libProducer = serviceState.libProducer;
            if (libProducer !== null) {
              yield* Effect.tryPromise({
                try: () => libProducer.close(),
                catch: (cause) => librarianServiceError("close-librarian-producer", cause),
              });
            }
            const colConsumer = serviceState.colConsumer;
            if (colConsumer !== null) {
              yield* Effect.tryPromise({
                try: () => colConsumer.close(),
                catch: (cause) => librarianServiceError("close-collection-consumer", cause),
              });
            }
            const colProducer = serviceState.colProducer;
            if (colProducer !== null) {
              yield* Effect.tryPromise({
                try: () => colProducer.close(),
                catch: (cause) => librarianServiceError("close-collection-producer", cause),
              });
            }
            yield* updateHandles(service.state, {
              libConsumer: null,
              libProducer: null,
              colConsumer: null,
              colProducer: null,
            });
            yield* Effect.tryPromise({
              try: () => baseStop(),
              catch: (cause) => librarianServiceError("stop", cause),
            });
          }),
        );

        }
  });
  service = librarianService;
  return librarianService;
}

export const LibrarianService = makeLibrarianService;

export const program = makeProcessorProgram({
  id: "librarian-svc",
  make: (config) => makeLibrarianService(config),
});

const librarianRuntime = ManagedRuntime.make(Layer.empty);

export function run(): Promise<void> {
  return librarianRuntime.runPromise(program);
}

export function runMain(): void {
  NodeRuntime.runMain(program);
}
