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
  AsyncProcessor,
  type ProcessorConfig,
  topics,
  type LibrarianRequest,
  type LibrarianResponse,
  type CollectionManagementRequest,
  type CollectionManagementResponse,
  type DocumentMetadata,
  type ProcessingMetadata,
} from "@trustgraph/base";
import { makeProcessorProgram } from "@trustgraph/base";
import type { BackendProducer, BackendConsumer, Message } from "@trustgraph/base";
import { Effect } from "effect";
import { CollectionManager } from "./collection-manager.js";
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

export class LibrarianService extends AsyncProcessor {
  private documents = new Map<string, DocumentMetadata>();
  private processing = new Map<string, ProcessingMetadata>();
  private uploads = new Map<string, UploadSession>();
  private collectionManager = new CollectionManager();
  private readonly dataDir: string;
  private readonly persistPath: string;

  // Librarian topic consumers/producers
  private libConsumer: BackendConsumer<LibrarianRequest> | null = null;
  private libProducer: BackendProducer<LibrarianResponse> | null = null;

  // Collection management topic consumers/producers
  private colConsumer: BackendConsumer<CollectionManagementRequest> | null = null;
  private colProducer: BackendProducer<CollectionManagementResponse> | null = null;

  constructor(config: LibrarianServiceConfig) {
    super(config);
    this.dataDir = config.dataDir ?? process.env.LIBRARIAN_DATA_DIR ?? "./data/librarian";
    this.persistPath = joinPath(this.dataDir, "librarian-state.json");
  }

  protected override async run(): Promise<void> {
    // Ensure directories exist
    await ensureDirectory(joinPath(this.dataDir, "docs"));

    // Load persisted state
    await this.loadFromDisk();

    // Create producers
    this.libProducer = await this.pubsub.createProducer<LibrarianResponse>({
      topic: topics.librarianResponse,
    });
    this.colProducer = await this.pubsub.createProducer<CollectionManagementResponse>({
      topic: topics.collectionManagementResponse,
    });

    // Create consumers
    this.libConsumer = await this.pubsub.createConsumer<LibrarianRequest>({
      topic: topics.librarianRequest,
      subscription: `${this.config.id}-librarian-request`,
    });
    this.colConsumer = await this.pubsub.createConsumer<CollectionManagementRequest>({
      topic: topics.collectionManagementRequest,
      subscription: `${this.config.id}-collection-management-request`,
    });

    console.log(`[LibrarianService] Listening on ${topics.librarianRequest} and ${topics.collectionManagementRequest}`);

    // Main consume loop — poll both consumers
    while (this.running) {
      try {
        // Poll librarian requests
        const libMsg = await this.libConsumer.receive(2000);
        if (libMsg !== null) {
          await this.handleLibrarianMessage(libMsg);
          await this.libConsumer.acknowledge(libMsg);
        }

        // Poll collection management requests
        const colMsg = await this.colConsumer.receive(2000);
        if (colMsg !== null) {
          await this.handleCollectionMessage(colMsg);
          await this.colConsumer.acknowledge(colMsg);
        }
      } catch (err) {
        if (!this.running) break;
        console.error("[LibrarianService] Error in consume loop:", err);
        await sleep(1000);
      }
    }
  }

  // ---------- Librarian message handling ----------

  private requestRecord(request: LibrarianRequest): Record<string, unknown> {
    return request as Record<string, unknown>;
  }

  private documentId(request: LibrarianRequest): string | undefined {
    const req = this.requestRecord(request);
    return optionalString(req.documentId) ?? optionalString(req["document-id"]);
  }

  private processingId(request: LibrarianRequest): string | undefined {
    const req = this.requestRecord(request);
    return optionalString(req.processingId) ?? optionalString(req["processing-id"]);
  }

  private documentMetadata(request: LibrarianRequest): DocumentMetadata | undefined {
    const req = this.requestRecord(request);
    const value = req.documentMetadata ?? req["document-metadata"];
    return isRecord(value) ? this.normaliseDocumentMetadata(value) : undefined;
  }

  private processingMetadata(request: LibrarianRequest): ProcessingMetadata | undefined {
    const req = this.requestRecord(request);
    const value = req.processingMetadata ?? req["processing-metadata"];
    if (!isRecord(value)) return undefined;
    const documentId = optionalString(value.documentId) ?? optionalString(value["document-id"]) ?? "";
    return {
      id: optionalString(value.id) ?? crypto.randomUUID(),
      documentId,
      "document-id": documentId,
      time: typeof value.time === "number" ? value.time : Math.floor(Date.now() / 1000),
      flow: optionalString(value.flow) ?? "default",
      user: optionalString(value.user) ?? optionalString(this.requestRecord(request).user) ?? "default",
      collection: optionalString(value.collection) ?? optionalString(this.requestRecord(request).collection) ?? "default",
      tags: Array.isArray(value.tags) ? value.tags.filter((tag): tag is string => typeof tag === "string") : [],
    };
  }

  private normaliseDocumentMetadata(value: Record<string, unknown>): DocumentMetadata {
    const id = optionalString(value.id) ?? crypto.randomUUID();
    const parentId = optionalString(value.parentId) ?? optionalString(value["parent-id"]);
    const documentType = optionalString(value.documentType) ?? optionalString(value["document-type"]) ?? "source";
    return {
      id,
      time: typeof value.time === "number" ? value.time : Math.floor(Date.now() / 1000),
      kind: optionalString(value.kind) ?? "application/octet-stream",
      title: optionalString(value.title) ?? "",
      comments: optionalString(value.comments) ?? "",
      user: optionalString(value.user) ?? "default",
      tags: Array.isArray(value.tags) ? value.tags.filter((tag): tag is string => typeof tag === "string") : [],
      ...(parentId !== undefined ? { parentId, "parent-id": parentId } : {}),
      documentType,
      "document-type": documentType,
      ...(Array.isArray(value.metadata) ? { metadata: value.metadata as NonNullable<DocumentMetadata["metadata"]> } : {}),
    };
  }

  private publicDocument(doc: DocumentMetadata): DocumentMetadata {
    const parentId = doc.parentId ?? doc["parent-id"];
    const documentType = doc.documentType ?? doc["document-type"] ?? "source";
    return {
      ...doc,
      ...(parentId !== undefined ? { parentId, "parent-id": parentId } : {}),
      documentType,
      "document-type": documentType,
    };
  }

  private publicProcessing(proc: ProcessingMetadata): ProcessingMetadata {
    const documentId = proc.documentId ?? proc["document-id"] ?? "";
    return {
      ...proc,
      documentId,
      "document-id": documentId,
    };
  }

  private documentResponse(doc: DocumentMetadata): LibrarianResponse {
    const publicDoc = this.publicDocument(doc);
    return {
      documentMetadata: publicDoc,
      "document-metadata": publicDoc,
    };
  }

  private documentsResponse(docs: DocumentMetadata[]): LibrarianResponse {
    const publicDocs = docs.map((doc) => this.publicDocument(doc));
    return {
      documents: publicDocs,
      "document-metadatas": publicDocs,
    };
  }

  private processingResponse(records: ProcessingMetadata[]): LibrarianResponse {
    const publicRecords = records.map((proc) => this.publicProcessing(proc));
    return {
      processing: publicRecords,
      "processing-metadata": publicRecords,
      "processing-metadatas": publicRecords,
    };
  }

  private async handleLibrarianMessage(msg: Message<LibrarianRequest>): Promise<void> {
    const request = msg.value();
    const props = msg.properties();
    const requestId = props.id;

    if (requestId === undefined || requestId.length === 0) {
      console.warn("[LibrarianService] Received request without id, ignoring");
      return;
    }

    try {
      if (request.operation === "stream-document") {
        for (const response of await this.streamDocument(request)) {
          await this.libProducer!.send(response, { id: requestId });
        }
        return;
      }
      const response = await this.handleLibrarianOperation(request);
      await this.libProducer!.send(response, { id: requestId });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      await this.libProducer!.send(
        { error: { type: "librarian-error", message } },
        { id: requestId },
      );
    }
  }

  private async handleLibrarianOperation(request: LibrarianRequest): Promise<LibrarianResponse> {
    switch (request.operation) {
      case "add-document":
        return this.addDocument(request);
      case "remove-document":
        return this.removeDocument(request);
      case "update-document":
        return this.updateDocument(request);
      case "list-documents":
        return this.listDocuments(request);
      case "get-document-metadata":
        return this.getDocumentMetadata(request);
      case "get-document-content":
        return this.getDocumentContent(request);
      case "add-child-document":
        return this.addChildDocument(request);
      case "list-children":
        return this.listChildren(request);
      case "add-processing":
        return this.addProcessing(request);
      case "remove-processing":
        return this.removeProcessing(request);
      case "list-processing":
        return this.listProcessing(request);
      case "begin-upload":
        return this.beginUpload(request);
      case "upload-chunk":
        return this.uploadChunk(request);
      case "complete-upload":
        return this.completeUpload(request);
      case "get-upload-status":
        return this.getUploadStatus(request);
      case "abort-upload":
        return this.abortUpload(request);
      case "list-uploads":
        return this.listUploads(request);
      case "stream-document":
        throw new Error("stream-document must be handled as a streaming operation");
      default:
        throw new Error(`Unknown librarian operation: ${request.operation as string}`);
    }
  }

  private async addDocument(request: LibrarianRequest): Promise<LibrarianResponse> {
    const meta = this.documentMetadata(request);
    if (meta === undefined) throw new Error("add-document requires documentMetadata");

    const id = meta.id;
    const now = Math.floor(Date.now() / 1000);

    const doc: DocumentMetadata = {
      ...meta,
      id,
      time: now,
    };

    this.documents.set(id, doc);

    // Store file content if provided
    if (request.content !== undefined && request.content.length > 0) {
      const filePath = joinPath(this.dataDir, "docs", `${id}.bin`);
      const buf = Buffer.from(request.content, "base64");
      await writeBinaryFile(filePath, buf);
    }

    await this.persist();
    console.log(`[LibrarianService] Added document ${id}: ${doc.title}`);

    return this.documentResponse(doc);
  }

  private async removeDocument(request: LibrarianRequest): Promise<LibrarianResponse> {
    const id = this.documentId(request);
    if (id === undefined || id.length === 0) {
      throw new Error("remove-document requires documentId");
    }

    // Remove the document itself
    this.documents.delete(id);

    // Remove the file
    try {
      await removePath(joinPath(this.dataDir, "docs", `${id}.bin`));
    } catch {
      // File may not exist — that's fine
    }

    // Cascade: remove children
    const childIds = [...this.documents.entries()]
      .filter(([, doc]) => doc.parentId === id)
      .map(([childId]) => childId);

    for (const childId of childIds) {
      this.documents.delete(childId);
      try {
        await removePath(joinPath(this.dataDir, "docs", `${childId}.bin`));
      } catch {
        // ignore
      }
    }

    // Remove associated processing records
    const procIds = [...this.processing.entries()]
      .filter(([, proc]) => proc.documentId === id)
      .map(([procId]) => procId);

    for (const procId of procIds) {
      this.processing.delete(procId);
    }

    await this.persist();
    console.log(`[LibrarianService] Removed document ${id} (cascade: ${childIds.length} children, ${procIds.length} processing)`);

    return {};
  }

  private async updateDocument(request: LibrarianRequest): Promise<LibrarianResponse> {
    const id = this.documentId(request) ?? this.documentMetadata(request)?.id;
    if (id === undefined || id.length === 0) {
      throw new Error("update-document requires documentId");
    }
    const existing = this.documents.get(id);
    if (existing === undefined) throw new Error(`Document not found: ${id}`);
    const meta = this.documentMetadata(request);
    if (meta === undefined) throw new Error("update-document requires documentMetadata");

    const doc: DocumentMetadata = this.publicDocument({
      ...existing,
      ...meta,
      id,
      time: meta.time ?? existing.time,
    });
    this.documents.set(id, doc);
    await this.persist();
    return this.documentResponse(doc);
  }

  private listDocuments(request: LibrarianRequest): LibrarianResponse {
    const user = request.user ?? "";
    const includeChildren = this.requestRecord(request)["include-children"] === true;
    const docs: DocumentMetadata[] = [];

    for (const doc of this.documents.values()) {
      // Filter by user
      if (user.length > 0 && doc.user !== user) continue;
      // Exclude children (only top-level documents) unless explicitly requested
      if (!includeChildren && doc.parentId !== undefined && doc.parentId.length > 0) continue;
      docs.push(doc);
    }

    return this.documentsResponse(docs);
  }

  private getDocumentMetadata(request: LibrarianRequest): LibrarianResponse {
    const id = this.documentId(request);
    if (id === undefined || id.length === 0) {
      throw new Error("get-document-metadata requires documentId");
    }

    const doc = this.documents.get(id);
    if (doc === undefined) throw new Error(`Document not found: ${id}`);

    return this.documentResponse(doc);
  }

  private async getDocumentContent(request: LibrarianRequest): Promise<LibrarianResponse> {
    const id = this.documentId(request);
    if (id === undefined || id.length === 0) {
      throw new Error("get-document-content requires documentId");
    }

    const doc = this.documents.get(id);
    if (doc === undefined) throw new Error(`Document not found: ${id}`);

    try {
      const filePath = joinPath(this.dataDir, "docs", `${id}.bin`);
      const buf = await readBinaryFile(filePath);
      const content = Buffer.from(buf).toString("base64");
      return { ...this.documentResponse(doc), content };
    } catch {
      throw new Error(`Document content not found on disk: ${id}`);
    }
  }

  private async addChildDocument(request: LibrarianRequest): Promise<LibrarianResponse> {
    const meta = this.documentMetadata(request);
    if (meta === undefined) {
      throw new Error("add-child-document requires documentMetadata");
    }
    if (meta.parentId === undefined || meta.parentId.length === 0) {
      throw new Error("add-child-document requires parentId in metadata");
    }

    // Verify parent exists
    if (!this.documents.has(meta.parentId)) {
      throw new Error(`Parent document not found: ${meta.parentId}`);
    }

    const id = meta.id;
    const now = Math.floor(Date.now() / 1000);

    const doc: DocumentMetadata = {
      ...meta,
      id,
      time: now,
    };

    this.documents.set(id, doc);

    // Store file content if provided
    if (request.content !== undefined && request.content.length > 0) {
      const filePath = joinPath(this.dataDir, "docs", `${id}.bin`);
      const buf = Buffer.from(request.content, "base64");
      await writeBinaryFile(filePath, buf);
    }

    await this.persist();
    console.log(`[LibrarianService] Added child document ${id} (parent: ${meta.parentId})`);

    return this.documentResponse(doc);
  }

  private listChildren(request: LibrarianRequest): LibrarianResponse {
    const parentId = this.documentId(request);
    if (parentId === undefined || parentId.length === 0) {
      throw new Error("list-children requires documentId");
    }

    const children: DocumentMetadata[] = [];
    for (const doc of this.documents.values()) {
      if (doc.parentId === parentId) {
        children.push(doc);
      }
    }

    return this.documentsResponse(children);
  }

  private async addProcessing(request: LibrarianRequest): Promise<LibrarianResponse> {
    const proc = this.processingMetadata(request);
    if (proc === undefined) throw new Error("add-processing requires processingMetadata");

    const id = proc.id;
    const now = Math.floor(Date.now() / 1000);

    const record: ProcessingMetadata = {
      ...proc,
      id,
      time: now,
    };

    this.processing.set(id, record);
    await this.persist();

    console.log(`[LibrarianService] Added processing ${id} for document ${proc.documentId}`);
    return this.processingResponse([record]);
  }

  private async removeProcessing(request: LibrarianRequest): Promise<LibrarianResponse> {
    const id = this.processingId(request);
    if (id === undefined || id.length === 0) {
      throw new Error("remove-processing requires processingId");
    }

    this.processing.delete(id);
    await this.persist();

    return {};
  }

  private listProcessing(request: LibrarianRequest): LibrarianResponse {
    const documentId = this.documentId(request);
    const records: ProcessingMetadata[] = [];

    for (const proc of this.processing.values()) {
      const procDocumentId = proc.documentId ?? proc["document-id"];
      if (documentId !== undefined && documentId.length > 0 && procDocumentId !== documentId) {
        continue;
      }
      records.push(proc);
    }

    return this.processingResponse(records);
  }

  private beginUpload(request: LibrarianRequest): LibrarianResponse {
    const meta = this.documentMetadata(request);
    if (meta === undefined) throw new Error("begin-upload requires documentMetadata");
    const req = this.requestRecord(request);
    const totalSize = typeof req["total-size"] === "number" ? req["total-size"] : 0;
    if (totalSize <= 0) throw new Error("begin-upload requires total-size");
    const chunkSize = typeof req["chunk-size"] === "number" && req["chunk-size"] > 0
      ? req["chunk-size"]
      : 3 * 1024 * 1024;
    const totalChunks = Math.max(1, Math.ceil(totalSize / chunkSize));
    const uploadId = crypto.randomUUID();

    this.uploads.set(uploadId, {
      id: uploadId,
      documentMetadata: meta,
      totalSize,
      chunkSize,
      totalChunks,
      createdAt: new Date().toISOString(),
      chunks: new Map<number, string>(),
      user: meta.user ?? optionalString(req.user) ?? "default",
    });

    return {
      "upload-id": uploadId,
      "chunk-size": chunkSize,
      "total-chunks": totalChunks,
    } as LibrarianResponse;
  }

  private uploadChunk(request: LibrarianRequest): LibrarianResponse {
    const req = this.requestRecord(request);
    const uploadId = optionalString(req["upload-id"]);
    if (uploadId === undefined) throw new Error("upload-chunk requires upload-id");
    const session = this.uploads.get(uploadId);
    if (session === undefined) throw new Error(`Upload not found: ${uploadId}`);
    const chunkIndex = typeof req["chunk-index"] === "number" ? req["chunk-index"] : -1;
    if (!Number.isInteger(chunkIndex) || chunkIndex < 0 || chunkIndex >= session.totalChunks) {
      throw new Error("upload-chunk requires a valid chunk-index");
    }
    const content = optionalString(req.content);
    if (content === undefined) throw new Error("upload-chunk requires content");
    session.chunks.set(chunkIndex, content);

    const bytesReceived = [...session.chunks.values()].reduce((sum, chunk) => sum + chunk.length, 0);
    return {
      "upload-id": uploadId,
      "chunk-index": chunkIndex,
      "chunks-received": session.chunks.size,
      "total-chunks": session.totalChunks,
      "bytes-received": bytesReceived,
      "total-bytes": session.totalSize,
    } as LibrarianResponse;
  }

  private async completeUpload(request: LibrarianRequest): Promise<LibrarianResponse> {
    const uploadId = optionalString(this.requestRecord(request)["upload-id"]);
    if (uploadId === undefined) throw new Error("complete-upload requires upload-id");
    const session = this.uploads.get(uploadId);
    if (session === undefined) throw new Error(`Upload not found: ${uploadId}`);
    if (session.chunks.size !== session.totalChunks) {
      throw new Error(`Upload incomplete: ${session.chunks.size}/${session.totalChunks} chunks received`);
    }

    const content = Array.from({ length: session.totalChunks }, (_, i) => session.chunks.get(i) ?? "").join("");
    const response = await this.addDocument({
      operation: "add-document",
      documentMetadata: session.documentMetadata,
      "document-metadata": session.documentMetadata,
      content,
      user: session.user,
    } as LibrarianRequest);
    this.uploads.delete(uploadId);
    const documentId = response.documentMetadata?.id ?? response["document-metadata"]?.id ?? session.documentMetadata.id;
    return {
      ...response,
      "document-id": documentId,
      "object-id": documentId,
    } as LibrarianResponse;
  }

  private getUploadStatus(request: LibrarianRequest): LibrarianResponse {
    const uploadId = optionalString(this.requestRecord(request)["upload-id"]);
    if (uploadId === undefined) throw new Error("get-upload-status requires upload-id");
    const session = this.uploads.get(uploadId);
    if (session === undefined) throw new Error(`Upload not found: ${uploadId}`);
    const receivedChunks = [...session.chunks.keys()].sort((a, b) => a - b);
    const receivedSet = new Set(receivedChunks);
    const missingChunks = Array.from({ length: session.totalChunks }, (_, i) => i).filter((i) => !receivedSet.has(i));
    const bytesReceived = [...session.chunks.values()].reduce((sum, chunk) => sum + chunk.length, 0);
    return {
      "upload-id": uploadId,
      "upload-state": "in-progress",
      "chunks-received": session.chunks.size,
      "total-chunks": session.totalChunks,
      "received-chunks": receivedChunks,
      "missing-chunks": missingChunks,
      "bytes-received": bytesReceived,
      "total-bytes": session.totalSize,
    } as LibrarianResponse;
  }

  private abortUpload(request: LibrarianRequest): LibrarianResponse {
    const uploadId = optionalString(this.requestRecord(request)["upload-id"]);
    if (uploadId === undefined) throw new Error("abort-upload requires upload-id");
    this.uploads.delete(uploadId);
    return {};
  }

  private listUploads(request: LibrarianRequest): LibrarianResponse {
    const user = optionalString(this.requestRecord(request).user);
    const sessions = [...this.uploads.values()]
      .filter((session) => user === undefined || session.user === user)
      .map((session) => ({
        "upload-id": session.id,
        "document-id": session.documentMetadata.id,
        "document-metadata-json": JSON.stringify(this.publicDocument(session.documentMetadata)),
        "total-size": session.totalSize,
        "chunk-size": session.chunkSize,
        "total-chunks": session.totalChunks,
        "chunks-received": session.chunks.size,
        "created-at": session.createdAt,
      }));
    return { "upload-sessions": sessions } as LibrarianResponse;
  }

  private async streamDocument(request: LibrarianRequest): Promise<LibrarianResponse[]> {
    const id = this.documentId(request);
    if (id === undefined) throw new Error("stream-document requires documentId");
    const req = this.requestRecord(request);
    const chunkSize = typeof req["chunk-size"] === "number" && req["chunk-size"] > 0
      ? req["chunk-size"]
      : 1024 * 1024;
    const filePath = joinPath(this.dataDir, "docs", `${id}.bin`);
    const buf = await readBinaryFile(filePath);
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
      } as LibrarianResponse;
    });
  }

  // ---------- Collection management ----------

  private async handleCollectionMessage(msg: Message<CollectionManagementRequest>): Promise<void> {
    const request = msg.value();
    const props = msg.properties();
    const requestId = props.id;

    if (requestId === undefined || requestId.length === 0) {
      console.warn("[LibrarianService] Received collection request without id, ignoring");
      return;
    }

    try {
      const response = this.handleCollectionOperation(request);
      await this.colProducer!.send(response, { id: requestId });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      await this.colProducer!.send(
        { error: { type: "collection-error", message } },
        { id: requestId },
      );
    }
  }

  private handleCollectionOperation(request: CollectionManagementRequest): CollectionManagementResponse {
    switch (request.operation) {
      case "list-collections": {
        const user = request.user ?? "";
        const collections = this.collectionManager.listCollections(user);
        return { collections };
      }

      case "update-collection": {
        const user = request.user ?? "";
        const collection = request.collection ?? "";
        const name = request.name ?? collection;
        const description = request.description ?? "";
        const tags = request.tags ?? [];

        this.collectionManager.updateCollection(user, collection, name, description, tags);
        // Persist after mutation
        this.persist().catch((err) => console.error("[LibrarianService] Persist failed:", err));

        const collections = this.collectionManager.listCollections(user);
        return { collections };
      }

      case "delete-collection": {
        const user = request.user ?? "";
        const collection = request.collection ?? "";

        this.collectionManager.deleteCollection(user, collection);
        this.persist().catch((err) => console.error("[LibrarianService] Persist failed:", err));

        return {};
      }

      default:
        throw new Error(`Unknown collection operation: ${request.operation as string}`);
    }
  }

  // ---------- Persistence ----------

  private async persist(): Promise<void> {
    try {
      const data = {
        documents: Object.fromEntries(this.documents),
        processing: Object.fromEntries(this.processing),
        collections: this.collectionManager.toJSON(),
      };

      const json = JSON.stringify(data, null, 2);
      await writeTextFile(this.persistPath, json);
    } catch (err) {
      console.error("[LibrarianService] Failed to persist state:", err);
    }
  }

  private async loadFromDisk(): Promise<void> {
    try {
      const raw = await readTextFile(this.persistPath);
      const parsed = JSON.parse(raw) as {
        documents?: Record<string, DocumentMetadata>;
        processing?: Record<string, ProcessingMetadata>;
        collections?: Array<{ user: string; collection: string; name: string; description: string; tags: string[] }>;
      };

      this.documents.clear();
      if (parsed.documents !== undefined) {
        for (const [id, doc] of Object.entries(parsed.documents)) {
          this.documents.set(id, this.publicDocument(doc));
        }
      }

      this.processing.clear();
      if (parsed.processing !== undefined) {
        for (const [id, proc] of Object.entries(parsed.processing)) {
          this.processing.set(id, this.publicProcessing(proc));
        }
      }

      if (parsed.collections !== undefined) {
        this.collectionManager.loadFromJSON(parsed.collections);
      }

      console.log(
        `[LibrarianService] Loaded persisted state (documents=${this.documents.size}, processing=${this.processing.size})`,
      );
    } catch {
      console.log("[LibrarianService] No persisted state found, starting fresh");
    }
  }

  override async stop(): Promise<void> {
    if (this.libConsumer !== null) {
      await this.libConsumer.close();
      this.libConsumer = null;
    }
    if (this.libProducer !== null) {
      await this.libProducer.close();
      this.libProducer = null;
    }
    if (this.colConsumer !== null) {
      await this.colConsumer.close();
      this.colConsumer = null;
    }
    if (this.colProducer !== null) {
      await this.colProducer.close();
      this.colProducer = null;
    }
    await super.stop();
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export const program = makeProcessorProgram({
  id: "librarian-svc",
  make: (config) => new LibrarianService(config),
});

export async function run(): Promise<void> {
  await Effect.runPromise(program);
}
