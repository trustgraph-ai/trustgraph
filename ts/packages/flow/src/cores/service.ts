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
  makeAsyncProcessor,
  makeProcessorProgram,
  type ProcessorConfig,
  type AsyncProcessorRuntime,
  topics,
  type KnowledgeRequest,
  type KnowledgeResponse,
  type Triple,
  type Term,
  errorMessage,
} from "@trustgraph/base";
import type { Message } from "@trustgraph/base";
import { Config, Duration, Effect } from "effect";
import * as S from "effect/Schema";
import { ensureDirectory, joinPath, readTextFile, writeTextFile } from "../runtime/effect-files.js";

export interface KnowledgeCoreServiceConfig extends ProcessorConfig {
  dataDir?: string;
}

interface KnowledgeCore {
  triples: Triple[];
  graphEmbeddings: { entity: Term; vectors: number[][] }[];
}

interface DocumentEmbeddingsCore {
  metadata?: Record<string, unknown>;
  chunks?: unknown[];
  [key: string]: unknown;
}

export type KnowledgeCoreService = AsyncProcessorRuntime & Record<string, any>;

export class KnowledgeCoreServiceError extends S.TaggedErrorClass<KnowledgeCoreServiceError>()(
  "KnowledgeCoreServiceError",
  {
    message: S.String,
    operation: S.String,
  },
) {}

interface KnowledgeResponseProducer {
  send(response: KnowledgeResponse, properties: { id: string }): Promise<void>;
  close(): Promise<void>;
}

interface CloseableResource {
  close(): Promise<void>;
}

const knowledgeCoreServiceError = (operation: string, cause: unknown): KnowledgeCoreServiceError =>
  KnowledgeCoreServiceError.make({
    operation,
    message: errorMessage(cause),
  });

const tryPromise = <A>(
  operation: string,
  evaluate: () => Promise<A>,
): Effect.Effect<A, KnowledgeCoreServiceError> =>
  Effect.tryPromise({
    try: evaluate,
    catch: (cause) => knowledgeCoreServiceError(operation, cause),
  });

const trySync = <A>(
  operation: string,
  evaluate: () => A,
): Effect.Effect<A, KnowledgeCoreServiceError> =>
  Effect.try({
    try: evaluate,
    catch: (cause) => knowledgeCoreServiceError(operation, cause),
  });

const failPromise = (operation: string, cause: unknown): Promise<never> =>
  Effect.runPromise(Effect.fail(knowledgeCoreServiceError(operation, cause)));

const sendResponse = (
  service: KnowledgeCoreService,
  response: KnowledgeResponse,
  requestId: string,
  operation = "respond",
): Effect.Effect<void, KnowledgeCoreServiceError> =>
  Effect.gen(function* () {
    const responseProducer = service.responseProducer as KnowledgeResponseProducer | null | undefined;
    if (responseProducer === null || responseProducer === undefined) {
      return yield* knowledgeCoreServiceError(operation, "Knowledge response producer not started");
    }

    yield* tryPromise(operation, () => responseProducer.send(response, { id: requestId }));
  });

const closeResource = (
  resource: CloseableResource,
  operation: string,
): Effect.Effect<void> =>
  tryPromise(operation, () => resource.close()).pipe(
    Effect.catch((error) =>
      Effect.logError("[KnowledgeCoreService] Failed to close resource", {
        error: error.message,
        operation: error.operation,
      }),
    ),
  );

export function makeKnowledgeCoreService(config: KnowledgeCoreServiceConfig): KnowledgeCoreService {
  const service = makeAsyncProcessor(config, {
    run: () => service.run(),
  }) as KnowledgeCoreService;
  const baseStop = service.stop;
  service.cores = new Map<string, KnowledgeCore>();
  service.deCores = new Map<string, DocumentEmbeddingsCore[]>();
  service.consumer = null;
  service.responseProducer = null;
  const dataDir = config.dataDir ?? "./data/knowledge";
  service.dataDir = dataDir;
  service.persistPath = joinPath(dataDir, "knowledge-state.json");
  Object.assign(service, {


      coreKey: function(this: KnowledgeCoreService, user: string, id: string): string {
        return `${user}:${id}`;

        },



      run: function(this: KnowledgeCoreService): Promise<void> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            if (config.dataDir === undefined) {
              const configuredDataDir = yield* Config.string("KNOWLEDGE_DATA_DIR").pipe(
                Config.withDefault("./data/knowledge"),
              );
              service.dataDir = configuredDataDir;
              service.persistPath = joinPath(configuredDataDir, "knowledge-state.json");
            }

            yield* tryPromise("ensure-directory", () => ensureDirectory(service.dataDir));
            // Load persisted state
            yield* tryPromise("load", () => service.loadFromDisk());

            // Create producer
            service.responseProducer = yield* tryPromise("response-producer", () =>
              service.pubsub.createProducer<KnowledgeResponse>({
                topic: topics.knowledgeResponse,
              }),
            );

            // Create consumer
            service.consumer = yield* tryPromise("consumer", () =>
              service.pubsub.createConsumer<KnowledgeRequest>({
                topic: topics.knowledgeRequest,
                subscription: `${service.config.id}-knowledge-request`,
              }),
            );

            yield* Effect.log(`[KnowledgeCoreService] Listening on ${topics.knowledgeRequest}`);

            // Main consume loop
            while (service.running) {
              const shouldContinue = yield* Effect.gen(function* () {
                const consumer = service.consumer;
                if (consumer === null || consumer === undefined) {
                  return yield* knowledgeCoreServiceError("consume", "Knowledge request consumer not started");
                }

                const msg = yield* tryPromise("consume-receive", () => consumer.receive(2000));
                if (msg === null) return true;

                yield* tryPromise("consume-handle", () => service.handleMessage(msg));
                yield* tryPromise("consume-acknowledge", () => consumer.acknowledge(msg));

                return true;
              }).pipe(
                Effect.catch((error) => {
                  if (!service.running) return Effect.succeed(false);
                  return Effect.logError("[KnowledgeCoreService] Error in consume loop", {
                    error: error.message,
                  }).pipe(
                    Effect.flatMap(() => Effect.sleep(Duration.millis(1000))),
                    Effect.as(true),
                  );
                }),
              );

              if (!shouldContinue) break;
            }
          }),
        );

        },



      handleMessage: function(this: KnowledgeCoreService, msg: Message<KnowledgeRequest>): Promise<void> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const request = msg.value();
            const props = msg.properties();
            const requestId = props.id;

            if (requestId === undefined || requestId.length === 0) {
              yield* Effect.logWarning("[KnowledgeCoreService] Received request without id, ignoring");
              return;
            }

            yield* tryPromise("operation", () => service.handleOperation(request, requestId)).pipe(
              Effect.catch((error) =>
                sendResponse(
                  service,
                  { error: { type: "knowledge-error", message: error.message } },
                  requestId,
                  "respond-error",
                ),
              ),
            );
          }),
        );

        },



      handleOperation: function(this: KnowledgeCoreService, request: KnowledgeRequest, requestId: string): Promise<void> {
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
          case "unload-kg-core":
            return this.unloadKgCore(request, requestId);
          case "list-de-cores":
            return this.listDeCores(request, requestId);
          case "get-de-core":
            return this.getDeCore(request, requestId);
          case "delete-de-core":
            return this.deleteDeCore(request, requestId);
          case "put-de-core":
            return this.putDeCore(request, requestId);
          case "load-de-core":
            return this.loadDeCore(request, requestId);
          default:
            return failPromise("operation", `Unknown knowledge operation: ${request.operation as string}`);
        }

        },



      requestRecord: function(this: KnowledgeCoreService, request: KnowledgeRequest): Record<string, unknown> {
        return request as Record<string, unknown>;

        },



      graphEmbeddings: function(this: KnowledgeCoreService, request: KnowledgeRequest): { entity: Term; vectors: number[][] }[] {
        const req = this.requestRecord(request);
        const value = request.graphEmbeddings ?? req["graph-embeddings"];
        return Array.isArray(value) ? value as { entity: Term; vectors: number[][] }[] : [];

        },



      documentEmbeddings: function(this: KnowledgeCoreService, request: KnowledgeRequest): DocumentEmbeddingsCore | undefined {
        const req = this.requestRecord(request);
        const value = request.documentEmbeddings ?? req["document-embeddings"];
        if (typeof value !== "object" || value === null || Array.isArray(value)) return undefined;
        return value as DocumentEmbeddingsCore;

        },



      listKgCores: function(this: KnowledgeCoreService, request: KnowledgeRequest, requestId: string): Promise<void> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const user = request.user ?? "";
            const prefix = user.length > 0 ? `${user}:` : "";

            const ids: string[] = [];
            for (const key of (service.cores as Map<string, KnowledgeCore>).keys()) {
              if (prefix.length === 0 || key.startsWith(prefix)) {
                // Extract the ID portion after the user prefix
                const id = key.slice(prefix.length);
                ids.push(id);
              }
            }

            yield* sendResponse(service, { ids }, requestId);
          }),
        );

        },



      getKgCore: function(this: KnowledgeCoreService, request: KnowledgeRequest, requestId: string): Promise<void> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const user = request.user ?? "";
            const coreId = request.id ?? "";
            const key = service.coreKey(user, coreId);

            const core = service.cores.get(key);
            if (core === undefined) {
              return yield* knowledgeCoreServiceError("get-kg-core", `Knowledge core not found: ${key}`);
            }

            // Send triples and embeddings in batches
            const BATCH_SIZE = 100;

            // Send triples in batches
            for (let i = 0; i < core.triples.length; i += BATCH_SIZE) {
              const batch = core.triples.slice(i, i + BATCH_SIZE);
              const isLast = i + BATCH_SIZE >= core.triples.length && core.graphEmbeddings.length === 0;

              yield* sendResponse(
                service,
                { triples: batch, eos: isLast },
                requestId,
                "respond-kg-triples",
              );
            }

            // Send graph embeddings in batches
            for (let i = 0; i < core.graphEmbeddings.length; i += BATCH_SIZE) {
              const batch = core.graphEmbeddings.slice(i, i + BATCH_SIZE);
              const isLast = i + BATCH_SIZE >= core.graphEmbeddings.length;

              yield* sendResponse(
                service,
                { graphEmbeddings: batch, "graph-embeddings": batch, eos: isLast } as KnowledgeResponse,
                requestId,
                "respond-kg-embeddings",
              );
            }

            // If core was empty, send a final eos
            if (core.triples.length === 0 && core.graphEmbeddings.length === 0) {
              yield* sendResponse(service, { eos: true }, requestId, "respond-kg-empty");
            }
          }),
        );

        },



      deleteKgCore: function(this: KnowledgeCoreService, request: KnowledgeRequest, requestId: string): Promise<void> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const user = request.user ?? "";
            const coreId = request.id ?? "";
            const key = service.coreKey(user, coreId);

            service.cores.delete(key);
            yield* tryPromise("persist-delete-kg-core", () => service.persist());

            yield* Effect.log(`[KnowledgeCoreService] Deleted core: ${key}`);
            yield* sendResponse(service, {}, requestId);
          }),
        );

        },



      putKgCore: function(this: KnowledgeCoreService, request: KnowledgeRequest, requestId: string): Promise<void> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const user = request.user ?? "";
            const coreId = request.id ?? "";
            const key = service.coreKey(user, coreId);

            let core = service.cores.get(key);
            if (core === undefined) {
              core = { triples: [], graphEmbeddings: [] };
              service.cores.set(key, core);
            }

            // Append triples if provided
            if (request.triples !== undefined && request.triples.length > 0) {
              core.triples.push(...request.triples);
            }

            // Append graph embeddings if provided
            const graphEmbeddings = service.graphEmbeddings(request);
            if (graphEmbeddings.length > 0) {
              core.graphEmbeddings.push(...graphEmbeddings);
            }

            yield* tryPromise("persist-put-kg-core", () => service.persist());

            yield* Effect.log(
              `[KnowledgeCoreService] Updated core ${key}: triples=${core.triples.length}, embeddings=${core.graphEmbeddings.length}`,
            );
            yield* sendResponse(service, {}, requestId);
          }),
        );

        },



      loadKgCore: function(this: KnowledgeCoreService, request: KnowledgeRequest, requestId: string): Promise<void> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const user = request.user ?? "";
            const coreId = request.id ?? "";
            const key = service.coreKey(user, coreId);

            const core = service.cores.get(key);
            if (core === undefined) {
              return yield* knowledgeCoreServiceError("load-kg-core", `Knowledge core not found: ${key}`);
            }

            if (core.triples.length > 0) {
              yield* Effect.acquireUseRelease(
                tryPromise("triples-producer", () =>
                  service.pubsub.createProducer<unknown>({ topic: "tg.flow.triples" }),
                ),
                (producer) =>
                  tryPromise("send-triples", () =>
                    producer.send({
                      metadata: {
                        id: coreId,
                        root: coreId,
                        user,
                        collection: request.collection ?? "default",
                      },
                      triples: core.triples,
                    }),
                  ),
                (producer) => closeResource(producer, "close-triples-producer"),
              );
            }

            yield* Effect.log(
              `[KnowledgeCoreService] Loaded core ${key} (triples=${core.triples.length}, embeddings=${core.graphEmbeddings.length})`,
            );
            yield* sendResponse(service, {}, requestId);
          }),
        );

        },



      unloadKgCore: function(this: KnowledgeCoreService, _request: KnowledgeRequest, requestId: string): Promise<void> {
        return Effect.runPromise(sendResponse(this, {}, requestId));

        },



      listDeCores: function(this: KnowledgeCoreService, request: KnowledgeRequest, requestId: string): Promise<void> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const user = request.user ?? "";
            const prefix = user.length > 0 ? `${user}:` : "";
            const ids = [...service.deCores.keys()]
              .filter((key) => prefix.length === 0 || key.startsWith(prefix))
              .map((key) => key.slice(prefix.length));
            yield* sendResponse(service, { ids }, requestId);
          }),
        );

        },



      getDeCore: function(this: KnowledgeCoreService, request: KnowledgeRequest, requestId: string): Promise<void> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const user = request.user ?? "";
            const coreId = request.id ?? "";
            const key = service.coreKey(user, coreId);
            const core = service.deCores.get(key);
            if (core === undefined) {
              return yield* knowledgeCoreServiceError("get-de-core", `Document embeddings core not found: ${key}`);
            }

            for (let i = 0; i < core.length; i++) {
              const isLast = i === core.length - 1;
              yield* sendResponse(
                service,
                {
                  documentEmbeddings: core[i],
                  "document-embeddings": core[i],
                  eos: isLast,
                } as KnowledgeResponse,
                requestId,
                "respond-de-core",
              );
            }
            if (core.length === 0) {
              yield* sendResponse(service, { eos: true }, requestId, "respond-de-empty");
            }
          }),
        );

        },



      deleteDeCore: function(this: KnowledgeCoreService, request: KnowledgeRequest, requestId: string): Promise<void> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const user = request.user ?? "";
            const coreId = request.id ?? "";
            service.deCores.delete(service.coreKey(user, coreId));
            yield* tryPromise("persist-delete-de-core", () => service.persist());
            yield* sendResponse(service, {}, requestId);
          }),
        );

        },



      putDeCore: function(this: KnowledgeCoreService, request: KnowledgeRequest, requestId: string): Promise<void> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const user = request.user ?? "";
            const coreId = request.id ?? "";
            const key = service.coreKey(user, coreId);
            const item = service.documentEmbeddings(request);
            if (item === undefined) {
              return yield* knowledgeCoreServiceError("put-de-core", "put-de-core requires document-embeddings");
            }
            const core = service.deCores.get(key) ?? [];
            core.push(item);
            service.deCores.set(key, core);
            yield* tryPromise("persist-put-de-core", () => service.persist());
            yield* sendResponse(service, {}, requestId);
          }),
        );

        },



      loadDeCore: function(this: KnowledgeCoreService, request: KnowledgeRequest, requestId: string): Promise<void> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const user = request.user ?? "";
            const coreId = request.id ?? "";
            const key = service.coreKey(user, coreId);
            if (!(service.deCores as Map<string, DocumentEmbeddingsCore[]>).has(key)) {
              return yield* knowledgeCoreServiceError("load-de-core", `Document embeddings core not found: ${key}`);
            }
            yield* sendResponse(service, {}, requestId);
          }),
        );

        },



      // ---------- Persistence ----------

      persist: function(this: KnowledgeCoreService): Promise<void> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            // Serialize Map to object
            const data: {
              kg: Record<string, KnowledgeCore>;
              de: Record<string, DocumentEmbeddingsCore[]>;
            } = { kg: {}, de: {} };
            for (const [key, core] of service.cores) {
              data.kg[key] = core;
            }
            for (const [key, core] of service.deCores) {
              data.de[key] = core;
            }

            const json = yield* trySync("persist-serialize", () => JSON.stringify(data, null, 2));
            yield* tryPromise("persist-write", () => writeTextFile(service.persistPath, json));
          }).pipe(
            Effect.catch((error) =>
              Effect.logError("[KnowledgeCoreService] Failed to persist state", {
                error: error.message,
              }),
            ),
          ),
        );

        },



      loadFromDisk: function(this: KnowledgeCoreService): Promise<void> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const raw = yield* tryPromise("load-read", () => readTextFile(service.persistPath));
            const parsed = yield* trySync("load-parse", () =>
              JSON.parse(raw) as Record<string, KnowledgeCore> | {
                kg?: Record<string, KnowledgeCore>;
                de?: Record<string, DocumentEmbeddingsCore[]>;
              },
            );

            service.cores.clear();
            service.deCores.clear();
            const kg = "kg" in parsed && parsed.kg !== undefined ? parsed.kg : parsed as Record<string, KnowledgeCore>;
            for (const [key, core] of Object.entries(kg)) {
              service.cores.set(key, core);
            }
            if ("de" in parsed && parsed.de !== undefined) {
              for (const [key, core] of Object.entries(parsed.de)) {
                service.deCores.set(key, core);
              }
            }

            yield* Effect.log(`[KnowledgeCoreService] Loaded persisted state (kg=${service.cores.size}, de=${service.deCores.size})`);
          }).pipe(
            Effect.catch(() =>
              Effect.log("[KnowledgeCoreService] No persisted state found, starting fresh"),
            ),
          ),
        );

        },



      stop: function(this: KnowledgeCoreService): Promise<void> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            if (service.consumer !== null) {
              yield* tryPromise("close-consumer", () => service.consumer.close());
              service.consumer = null;
            }
            if (service.responseProducer !== null) {
              yield* tryPromise("close-response-producer", () => service.responseProducer.close());
              service.responseProducer = null;
            }
            yield* tryPromise("base-stop", () => baseStop());
          }),
        );

        }
  });
  return service;
}

export const KnowledgeCoreService = makeKnowledgeCoreService;

export const program = makeProcessorProgram({
  id: "knowledge-svc",
  make: (config) => makeKnowledgeCoreService(config),
});

export function run(): Promise<void> {
  return Effect.runPromise(program);
}
