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

import { randomUUID } from "node:crypto";
import { readFile, writeFile, mkdir, unlink } from "node:fs/promises";
import { dirname, join } from "node:path";
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
import type { BackendProducer, BackendConsumer, Message } from "@trustgraph/base";
import { CollectionManager } from "./collection-manager.js";

export interface LibrarianServiceConfig extends ProcessorConfig {
  dataDir?: string;
}

export class LibrarianService extends AsyncProcessor {
  private documents = new Map<string, DocumentMetadata>();
  private processing = new Map<string, ProcessingMetadata>();
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
    this.persistPath = join(this.dataDir, "librarian-state.json");
  }

  protected override async run(): Promise<void> {
    // Ensure directories exist
    await mkdir(join(this.dataDir, "docs"), { recursive: true });

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
        if (libMsg) {
          await this.handleLibrarianMessage(libMsg);
          await this.libConsumer.acknowledge(libMsg);
        }

        // Poll collection management requests
        const colMsg = await this.colConsumer.receive(2000);
        if (colMsg) {
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

  private async handleLibrarianMessage(msg: Message<LibrarianRequest>): Promise<void> {
    const request = msg.value();
    const props = msg.properties();
    const requestId = props.id;

    if (!requestId) {
      console.warn("[LibrarianService] Received request without id, ignoring");
      return;
    }

    try {
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
      default:
        throw new Error(`Unknown librarian operation: ${request.operation as string}`);
    }
  }

  private async addDocument(request: LibrarianRequest): Promise<LibrarianResponse> {
    const meta = request.documentMetadata;
    if (!meta) throw new Error("add-document requires documentMetadata");

    const id = randomUUID();
    const now = Date.now();

    const doc: DocumentMetadata = {
      ...meta,
      id,
      time: now,
    };

    this.documents.set(id, doc);

    // Store file content if provided
    if (request.content) {
      const filePath = join(this.dataDir, "docs", `${id}.bin`);
      const buf = Buffer.from(request.content, "base64");
      await writeFile(filePath, buf);
    }

    await this.persist();
    console.log(`[LibrarianService] Added document ${id}: ${doc.title}`);

    return { documentMetadata: doc };
  }

  private async removeDocument(request: LibrarianRequest): Promise<LibrarianResponse> {
    const id = request.documentId;
    if (!id) throw new Error("remove-document requires documentId");

    // Remove the document itself
    this.documents.delete(id);

    // Remove the file
    try {
      await unlink(join(this.dataDir, "docs", `${id}.bin`));
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
        await unlink(join(this.dataDir, "docs", `${childId}.bin`));
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

  private listDocuments(request: LibrarianRequest): LibrarianResponse {
    const user = request.user ?? "";
    const docs: DocumentMetadata[] = [];

    for (const doc of this.documents.values()) {
      // Filter by user
      if (user && doc.user !== user) continue;
      // Exclude children (only top-level documents) unless explicitly requested
      if (doc.parentId) continue;
      docs.push(doc);
    }

    return { documents: docs };
  }

  private getDocumentMetadata(request: LibrarianRequest): LibrarianResponse {
    const id = request.documentId;
    if (!id) throw new Error("get-document-metadata requires documentId");

    const doc = this.documents.get(id);
    if (!doc) throw new Error(`Document not found: ${id}`);

    return { documentMetadata: doc };
  }

  private async getDocumentContent(request: LibrarianRequest): Promise<LibrarianResponse> {
    const id = request.documentId;
    if (!id) throw new Error("get-document-content requires documentId");

    const doc = this.documents.get(id);
    if (!doc) throw new Error(`Document not found: ${id}`);

    try {
      const filePath = join(this.dataDir, "docs", `${id}.bin`);
      const buf = await readFile(filePath);
      const content = buf.toString("base64");
      return { documentMetadata: doc, content };
    } catch {
      throw new Error(`Document content not found on disk: ${id}`);
    }
  }

  private async addChildDocument(request: LibrarianRequest): Promise<LibrarianResponse> {
    const meta = request.documentMetadata;
    if (!meta) throw new Error("add-child-document requires documentMetadata");
    if (!meta.parentId) throw new Error("add-child-document requires parentId in metadata");

    // Verify parent exists
    if (!this.documents.has(meta.parentId)) {
      throw new Error(`Parent document not found: ${meta.parentId}`);
    }

    const id = randomUUID();
    const now = Date.now();

    const doc: DocumentMetadata = {
      ...meta,
      id,
      time: now,
    };

    this.documents.set(id, doc);

    // Store file content if provided
    if (request.content) {
      const filePath = join(this.dataDir, "docs", `${id}.bin`);
      const buf = Buffer.from(request.content, "base64");
      await writeFile(filePath, buf);
    }

    await this.persist();
    console.log(`[LibrarianService] Added child document ${id} (parent: ${meta.parentId})`);

    return { documentMetadata: doc };
  }

  private listChildren(request: LibrarianRequest): LibrarianResponse {
    const parentId = request.documentId;
    if (!parentId) throw new Error("list-children requires documentId");

    const children: DocumentMetadata[] = [];
    for (const doc of this.documents.values()) {
      if (doc.parentId === parentId) {
        children.push(doc);
      }
    }

    return { documents: children };
  }

  private async addProcessing(request: LibrarianRequest): Promise<LibrarianResponse> {
    const proc = request.processingMetadata;
    if (!proc) throw new Error("add-processing requires processingMetadata");

    const id = randomUUID();
    const now = Date.now();

    const record: ProcessingMetadata = {
      ...proc,
      id,
      time: now,
    };

    this.processing.set(id, record);
    await this.persist();

    console.log(`[LibrarianService] Added processing ${id} for document ${proc.documentId}`);
    return { processing: [record] };
  }

  private async removeProcessing(request: LibrarianRequest): Promise<LibrarianResponse> {
    const id = request.processingId;
    if (!id) throw new Error("remove-processing requires processingId");

    this.processing.delete(id);
    await this.persist();

    return {};
  }

  private listProcessing(request: LibrarianRequest): LibrarianResponse {
    const documentId = request.documentId;
    const records: ProcessingMetadata[] = [];

    for (const proc of this.processing.values()) {
      if (documentId && proc.documentId !== documentId) continue;
      records.push(proc);
    }

    return { processing: records };
  }

  // ---------- Collection management ----------

  private async handleCollectionMessage(msg: Message<CollectionManagementRequest>): Promise<void> {
    const request = msg.value();
    const props = msg.properties();
    const requestId = props.id;

    if (!requestId) {
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
      await mkdir(dirname(this.persistPath), { recursive: true });
      await writeFile(this.persistPath, json, "utf-8");
    } catch (err) {
      console.error("[LibrarianService] Failed to persist state:", err);
    }
  }

  private async loadFromDisk(): Promise<void> {
    try {
      const raw = await readFile(this.persistPath, "utf-8");
      const parsed = JSON.parse(raw) as {
        documents?: Record<string, DocumentMetadata>;
        processing?: Record<string, ProcessingMetadata>;
        collections?: Array<{ user: string; collection: string; name: string; description: string; tags: string[] }>;
      };

      this.documents.clear();
      if (parsed.documents) {
        for (const [id, doc] of Object.entries(parsed.documents)) {
          this.documents.set(id, doc);
        }
      }

      this.processing.clear();
      if (parsed.processing) {
        for (const [id, proc] of Object.entries(parsed.processing)) {
          this.processing.set(id, proc);
        }
      }

      if (parsed.collections) {
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
    if (this.libConsumer) {
      await this.libConsumer.close();
      this.libConsumer = null;
    }
    if (this.libProducer) {
      await this.libProducer.close();
      this.libProducer = null;
    }
    if (this.colConsumer) {
      await this.colConsumer.close();
      this.colConsumer = null;
    }
    if (this.colProducer) {
      await this.colProducer.close();
      this.colProducer = null;
    }
    await super.stop();
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function run(): Promise<void> {
  await LibrarianService.launch("librarian-svc");
}
