/**
 * Knowledge core service — manages stored knowledge graph cores (triples + embeddings).
 *
 * An AsyncProcessor (NOT FlowProcessor) that:
 * 1. Listens on knowledge-request topic
 * 2. Handles CRUD operations for knowledge graph cores
 * 3. Each core stores triples and graph embeddings keyed by user:id
 * 4. Persists state to JSON
 *
 * Python reference: trustgraph-flow/trustgraph/knowledge/service/service.py
 */

import {
  AsyncProcessor,
  type ProcessorConfig,
  topics,
  type KnowledgeRequest,
  type KnowledgeResponse,
  type Triple,
  type Term,
} from "@trustgraph/base";
import { makeProcessorProgram } from "@trustgraph/base";
import type { BackendProducer, BackendConsumer, Message } from "@trustgraph/base";
import { joinPath, readTextFile, writeTextFile } from "../runtime/effect-files.js";

export interface KnowledgeCoreServiceConfig extends ProcessorConfig {
  dataDir?: string;
}

interface KnowledgeCore {
  triples: Triple[];
  graphEmbeddings: { entity: Term; vectors: number[][] }[];
}

export class KnowledgeCoreService extends AsyncProcessor {
  /** Keyed by `${user}:${id}` */
  private cores = new Map<string, KnowledgeCore>();
  private readonly persistPath: string;

  private consumer: BackendConsumer<KnowledgeRequest> | null = null;
  private responseProducer: BackendProducer<KnowledgeResponse> | null = null;

  constructor(config: KnowledgeCoreServiceConfig) {
    super(config);
    const dataDir = config.dataDir ?? process.env.KNOWLEDGE_DATA_DIR ?? "./data/knowledge";
    this.persistPath = joinPath(dataDir, "knowledge-state.json");
  }

  private coreKey(user: string, id: string): string {
    return `${user}:${id}`;
  }

  protected override async run(): Promise<void> {
    // Load persisted state
    await this.loadFromDisk();

    // Create producer
    this.responseProducer = await this.pubsub.createProducer<KnowledgeResponse>({
      topic: topics.knowledgeResponse,
    });

    // Create consumer
    this.consumer = await this.pubsub.createConsumer<KnowledgeRequest>({
      topic: topics.knowledgeRequest,
      subscription: `${this.config.id}-knowledge-request`,
    });

    console.log(`[KnowledgeCoreService] Listening on ${topics.knowledgeRequest}`);

    // Main consume loop
    while (this.running) {
      try {
        const msg = await this.consumer.receive(2000);
        if (msg === null) continue;

        await this.handleMessage(msg);
        await this.consumer.acknowledge(msg);
      } catch (err) {
        if (!this.running) break;
        console.error("[KnowledgeCoreService] Error in consume loop:", err);
        await sleep(1000);
      }
    }
  }

  private async handleMessage(msg: Message<KnowledgeRequest>): Promise<void> {
    const request = msg.value();
    const props = msg.properties();
    const requestId = props.id;

    if (requestId === undefined || requestId.length === 0) {
      console.warn("[KnowledgeCoreService] Received request without id, ignoring");
      return;
    }

    try {
      await this.handleOperation(request, requestId);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      await this.responseProducer!.send(
        { error: { type: "knowledge-error", message } },
        { id: requestId },
      );
    }
  }

  private async handleOperation(request: KnowledgeRequest, requestId: string): Promise<void> {
    switch (request.operation) {
      case "list-kg-cores":
        return this.listKgCores(request, requestId);
      case "get-kg-core":
        return this.getKgCore(request, requestId);
      case "delete-kg-core":
        return this.deleteKgCore(request, requestId);
      case "put-kg-core":
        return this.putKgCore(request, requestId);
      case "load-kg-core":
        return this.loadKgCore(request, requestId);
      default:
        throw new Error(`Unknown knowledge operation: ${request.operation as string}`);
    }
  }

  private async listKgCores(request: KnowledgeRequest, requestId: string): Promise<void> {
    const user = request.user ?? "";
    const prefix = user.length > 0 ? `${user}:` : "";

    const ids: string[] = [];
    for (const key of this.cores.keys()) {
      if (prefix.length === 0 || key.startsWith(prefix)) {
        // Extract the ID portion after the user prefix
        const id = key.slice(prefix.length);
        ids.push(id);
      }
    }

    await this.responseProducer!.send({ ids }, { id: requestId });
  }

  private async getKgCore(request: KnowledgeRequest, requestId: string): Promise<void> {
    const user = request.user ?? "";
    const coreId = request.id ?? "";
    const key = this.coreKey(user, coreId);

    const core = this.cores.get(key);
    if (core === undefined) {
      throw new Error(`Knowledge core not found: ${key}`);
    }

    // Send triples and embeddings in batches
    const BATCH_SIZE = 100;

    // Send triples in batches
    for (let i = 0; i < core.triples.length; i += BATCH_SIZE) {
      const batch = core.triples.slice(i, i + BATCH_SIZE);
      const isLast = i + BATCH_SIZE >= core.triples.length && core.graphEmbeddings.length === 0;

      await this.responseProducer!.send(
        { triples: batch, eos: isLast },
        { id: requestId },
      );
    }

    // Send graph embeddings in batches
    for (let i = 0; i < core.graphEmbeddings.length; i += BATCH_SIZE) {
      const batch = core.graphEmbeddings.slice(i, i + BATCH_SIZE);
      const isLast = i + BATCH_SIZE >= core.graphEmbeddings.length;

      await this.responseProducer!.send(
        { graphEmbeddings: batch, eos: isLast },
        { id: requestId },
      );
    }

    // If core was empty, send a final eos
    if (core.triples.length === 0 && core.graphEmbeddings.length === 0) {
      await this.responseProducer!.send({ eos: true }, { id: requestId });
    }
  }

  private async deleteKgCore(request: KnowledgeRequest, requestId: string): Promise<void> {
    const user = request.user ?? "";
    const coreId = request.id ?? "";
    const key = this.coreKey(user, coreId);

    this.cores.delete(key);
    await this.persist();

    console.log(`[KnowledgeCoreService] Deleted core: ${key}`);
    await this.responseProducer!.send({}, { id: requestId });
  }

  private async putKgCore(request: KnowledgeRequest, requestId: string): Promise<void> {
    const user = request.user ?? "";
    const coreId = request.id ?? "";
    const key = this.coreKey(user, coreId);

    let core = this.cores.get(key);
    if (core === undefined) {
      core = { triples: [], graphEmbeddings: [] };
      this.cores.set(key, core);
    }

    // Append triples if provided
    if (request.triples !== undefined && request.triples.length > 0) {
      core.triples.push(...request.triples);
    }

    // Append graph embeddings if provided
    if (request.graphEmbeddings !== undefined && request.graphEmbeddings.length > 0) {
      core.graphEmbeddings.push(...request.graphEmbeddings);
    }

    await this.persist();

    console.log(
      `[KnowledgeCoreService] Updated core ${key}: triples=${core.triples.length}, embeddings=${core.graphEmbeddings.length}`,
    );
    await this.responseProducer!.send({}, { id: requestId });
  }

  private async loadKgCore(request: KnowledgeRequest, requestId: string): Promise<void> {
    const user = request.user ?? "";
    const coreId = request.id ?? "";
    const key = this.coreKey(user, coreId);

    const core = this.cores.get(key);
    if (core === undefined) {
      throw new Error(`Knowledge core not found: ${key}`);
    }

    // MVP: just acknowledge. Full implementation would publish triples
    // to flow storage topics via the flow config.
    console.log(
      `[KnowledgeCoreService] Load requested for core ${key} (triples=${core.triples.length}, embeddings=${core.graphEmbeddings.length}) — returning success`,
    );
    await this.responseProducer!.send({}, { id: requestId });
  }

  // ---------- Persistence ----------

  private async persist(): Promise<void> {
    try {
      // Serialize Map to object
      const data: Record<string, KnowledgeCore> = {};
      for (const [key, core] of this.cores) {
        data[key] = core;
      }

      const json = JSON.stringify(data, null, 2);
      await writeTextFile(this.persistPath, json);
    } catch (err) {
      console.error("[KnowledgeCoreService] Failed to persist state:", err);
    }
  }

  private async loadFromDisk(): Promise<void> {
    try {
      const raw = await readTextFile(this.persistPath);
      const parsed = JSON.parse(raw) as Record<string, KnowledgeCore>;

      this.cores.clear();
      for (const [key, core] of Object.entries(parsed)) {
        this.cores.set(key, core);
      }

      console.log(`[KnowledgeCoreService] Loaded persisted state (cores=${this.cores.size})`);
    } catch {
      console.log("[KnowledgeCoreService] No persisted state found, starting fresh");
    }
  }

  override async stop(): Promise<void> {
    if (this.consumer !== null) {
      await this.consumer.close();
      this.consumer = null;
    }
    if (this.responseProducer !== null) {
      await this.responseProducer.close();
      this.responseProducer = null;
    }
    await super.stop();
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export const program = makeProcessorProgram({
  id: "knowledge-svc",
  make: (config) => new KnowledgeCoreService(config),
});

export async function run(): Promise<void> {
  await KnowledgeCoreService.launch("knowledge-svc");
}
