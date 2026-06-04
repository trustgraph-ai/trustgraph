/**
 * Knowledge core service — manages stored knowledge graph cores.
 *
 * Python reference: trustgraph-flow/trustgraph/knowledge/service/service.py
 */

import {NodeRuntime} from "@effect/platform-node";
import {
  KnowledgeRequest as KnowledgeRequestSchema,
  KnowledgeResponse as KnowledgeResponseSchema,
  Term as TermSchema,
  Triple as TripleSchema,
  errorMessage,
  loadProcessorRuntimeConfig,
  makeAsyncProcessor,
  makeProcessorProgram,
  optionalStringConfig,
  topics,
  type AsyncProcessorRuntime,
  type BackendConsumer,
  type BackendProducer,
  type KnowledgeOperation,
  type KnowledgeRequest,
  type KnowledgeResponse,
  type Message,
  type ProcessorConfig,
} from "@trustgraph/base";
import {Duration, Effect, HashMap, Layer, ManagedRuntime, Match, SynchronizedRef} from "effect";
import * as O from "effect/Option";
import * as S from "effect/Schema";
import {ensureDirectory, joinPath, readTextFile, writeTextFile} from "../runtime/effect-files.js";

export interface KnowledgeCoreServiceConfig extends ProcessorConfig {
  readonly dataDir?: string;
}

const NumberArray = S.Array(S.Number).pipe(S.mutable);
const NumberArrays = S.Array(NumberArray).pipe(S.mutable);

const GraphEmbeddingSchema = S.Struct({
  entity: TermSchema,
  vectors: NumberArrays,
});
type GraphEmbedding = typeof GraphEmbeddingSchema.Type;

const DocumentEmbeddingsCoreSchema = S.StructWithRest(
  S.Struct({
    metadata: S.optionalKey(S.Record(S.String, S.Unknown)),
    chunks: S.optionalKey(S.Unknown.pipe(S.Array, S.mutable)),
  }),
  [S.Record(S.String, S.Unknown)],
);
type DocumentEmbeddingsCore = typeof DocumentEmbeddingsCoreSchema.Type;

const KnowledgeCoreSchema = S.Struct({
  triples: S.Array(TripleSchema).pipe(S.mutable),
  graphEmbeddings: S.Array(GraphEmbeddingSchema).pipe(S.mutable),
});
type KnowledgeCore = typeof KnowledgeCoreSchema.Type;

const PersistedKnowledgeSnapshotSchema = S.Struct({
  kg: S.Record(S.String, KnowledgeCoreSchema),
  de: S.optionalKey(S.Record(S.String, S.Array(DocumentEmbeddingsCoreSchema).pipe(S.mutable))),
});
const PersistedKnowledgeSnapshotJsonSchema = PersistedKnowledgeSnapshotSchema.pipe(S.fromJsonString);
const LegacyKnowledgeSnapshotJsonSchema = S.Record(S.String, KnowledgeCoreSchema).pipe(S.fromJsonString);
type PersistedKnowledgeSnapshot = typeof PersistedKnowledgeSnapshotSchema.Type;
type LegacyKnowledgeSnapshot = typeof LegacyKnowledgeSnapshotJsonSchema.Type;

export class KnowledgeCoreServiceError extends S.TaggedErrorClass<KnowledgeCoreServiceError>()(
  "KnowledgeCoreServiceError",
  {
    message: S.String,
    operation: S.String,
  },
) {}

const knowledgeCoreServiceError = (operation: string, cause: unknown): KnowledgeCoreServiceError =>
  KnowledgeCoreServiceError.make({
    operation,
    message: errorMessage(cause),
  });

type KnowledgeCoreStore = HashMap.HashMap<string, KnowledgeCore>;
type DocumentCoreStore = HashMap.HashMap<string, Array<DocumentEmbeddingsCore>>;

interface KnowledgeCoreServiceState {
  readonly kgCores: KnowledgeCoreStore;
  readonly deCores: DocumentCoreStore;
  readonly consumer: BackendConsumer<KnowledgeRequest> | null;
  readonly responseProducer: BackendProducer<KnowledgeResponse> | null;
}

export interface KnowledgeCoreService extends AsyncProcessorRuntime<KnowledgeCoreServiceError> {
  readonly state: SynchronizedRef.SynchronizedRef<KnowledgeCoreServiceState>;
  readonly dataDir: string;
  readonly persistPath: string;
  readonly coreKey: (user: string, id: string) => string;
  readonly graphEmbeddings: (request: KnowledgeRequest) => ReadonlyArray<GraphEmbedding>;
  readonly documentEmbeddings: (request: KnowledgeRequest) => DocumentEmbeddingsCore | undefined;
  readonly handleMessage: (msg: Message<KnowledgeRequest>) => Promise<void>;
  readonly handleMessageEffect: (msg: Message<KnowledgeRequest>) => Effect.Effect<void, KnowledgeCoreServiceError>;
  readonly handleOperation: (request: KnowledgeRequest, requestId: string) => Promise<void>;
  readonly handleOperationEffect: (request: KnowledgeRequest, requestId: string) => Effect.Effect<void, KnowledgeCoreServiceError>;
  readonly listKgCores: (request: KnowledgeRequest, requestId: string) => Promise<void>;
  readonly listKgCoresEffect: (request: KnowledgeRequest, requestId: string) => Effect.Effect<void, KnowledgeCoreServiceError>;
  readonly getKgCore: (request: KnowledgeRequest, requestId: string) => Promise<void>;
  readonly getKgCoreEffect: (request: KnowledgeRequest, requestId: string) => Effect.Effect<void, KnowledgeCoreServiceError>;
  readonly deleteKgCore: (request: KnowledgeRequest, requestId: string) => Promise<void>;
  readonly deleteKgCoreEffect: (request: KnowledgeRequest, requestId: string) => Effect.Effect<void, KnowledgeCoreServiceError>;
  readonly putKgCore: (request: KnowledgeRequest, requestId: string) => Promise<void>;
  readonly putKgCoreEffect: (request: KnowledgeRequest, requestId: string) => Effect.Effect<void, KnowledgeCoreServiceError>;
  readonly loadKgCore: (request: KnowledgeRequest, requestId: string) => Promise<void>;
  readonly loadKgCoreEffect: (request: KnowledgeRequest, requestId: string) => Effect.Effect<void, KnowledgeCoreServiceError>;
  readonly unloadKgCore: (request: KnowledgeRequest, requestId: string) => Promise<void>;
  readonly unloadKgCoreEffect: (request: KnowledgeRequest, requestId: string) => Effect.Effect<void, KnowledgeCoreServiceError>;
  readonly listDeCores: (request: KnowledgeRequest, requestId: string) => Promise<void>;
  readonly listDeCoresEffect: (request: KnowledgeRequest, requestId: string) => Effect.Effect<void, KnowledgeCoreServiceError>;
  readonly getDeCore: (request: KnowledgeRequest, requestId: string) => Promise<void>;
  readonly getDeCoreEffect: (request: KnowledgeRequest, requestId: string) => Effect.Effect<void, KnowledgeCoreServiceError>;
  readonly deleteDeCore: (request: KnowledgeRequest, requestId: string) => Promise<void>;
  readonly deleteDeCoreEffect: (request: KnowledgeRequest, requestId: string) => Effect.Effect<void, KnowledgeCoreServiceError>;
  readonly putDeCore: (request: KnowledgeRequest, requestId: string) => Promise<void>;
  readonly putDeCoreEffect: (request: KnowledgeRequest, requestId: string) => Effect.Effect<void, KnowledgeCoreServiceError>;
  readonly loadDeCore: (request: KnowledgeRequest, requestId: string) => Promise<void>;
  readonly loadDeCoreEffect: (request: KnowledgeRequest, requestId: string) => Effect.Effect<void, KnowledgeCoreServiceError>;
  readonly persist: () => Promise<void>;
  readonly persistEffect: Effect.Effect<void, never>;
  readonly loadFromDisk: () => Promise<void>;
  readonly loadFromDiskEffect: Effect.Effect<void, never>;
}

const initialState = (): KnowledgeCoreServiceState => ({
  kgCores: HashMap.empty<string, KnowledgeCore>(),
  deCores: HashMap.empty<string, Array<DocumentEmbeddingsCore>>(),
  consumer: null,
  responseProducer: null,
});

const getHashMapValue = <K, V>(store: HashMap.HashMap<K, V>, key: K): V | undefined =>
  O.getOrUndefined(HashMap.get(store, key));

const cloneKnowledgeCore = (core: KnowledgeCore): KnowledgeCore => ({
  triples: Array.from(core.triples),
  graphEmbeddings: core.graphEmbeddings.map((entry) => ({
    entity: entry.entity,
    vectors: entry.vectors.map((vector) => Array.from(vector)),
  })),
});

const sortedEntries = <A>(store: HashMap.HashMap<string, A>): ReadonlyArray<readonly [string, A]> =>
  HashMap.toEntries(store).sort(([left], [right]) => left.localeCompare(right));

const toPersistedSnapshot = (state: KnowledgeCoreServiceState): PersistedKnowledgeSnapshot => {
  const kg: Record<string, KnowledgeCore> = {};
  const de: Record<string, Array<DocumentEmbeddingsCore>> = {};

  for (const [key, core] of sortedEntries(state.kgCores)) {
    kg[key] = cloneKnowledgeCore(core);
  }
  for (const [key, core] of sortedEntries(state.deCores)) {
    de[key] = Array.from(core);
  }

  return {kg, de};
};

const kgStoreFromRecord = (record: LegacyKnowledgeSnapshot): KnowledgeCoreStore => {
  let store = HashMap.empty<string, KnowledgeCore>();
  for (const [key, core] of Object.entries(record)) {
    store = HashMap.set(store, key, cloneKnowledgeCore(core));
  }
  return store;
};

const deStoreFromRecord = (
  record: Record<string, Array<DocumentEmbeddingsCore>> | undefined,
): DocumentCoreStore => {
  let store = HashMap.empty<string, Array<DocumentEmbeddingsCore>>();
  for (const [key, core] of Object.entries(record ?? {})) {
    store = HashMap.set(store, key, Array.from(core));
  }
  return store;
};

const coreKey = (user: string, id: string): string => `${user}:${id}`;

const graphEmbeddingsFor = (request: KnowledgeRequest): ReadonlyArray<GraphEmbedding> =>
  request.graphEmbeddings ?? request["graph-embeddings"] ?? [];

const documentEmbeddingsFor = (request: KnowledgeRequest): DocumentEmbeddingsCore | undefined =>
  request.documentEmbeddings ?? request["document-embeddings"];

const updateHandles = (
  stateRef: SynchronizedRef.SynchronizedRef<KnowledgeCoreServiceState>,
  handles: {
    readonly consumer?: BackendConsumer<KnowledgeRequest> | null;
    readonly responseProducer?: BackendProducer<KnowledgeResponse> | null;
  },
) =>
  SynchronizedRef.updateAndGet(stateRef, (state) => ({
    ...state,
    consumer: handles.consumer === undefined ? state.consumer : handles.consumer,
    responseProducer: handles.responseProducer === undefined ? state.responseProducer : handles.responseProducer,
  }));

const tryPromise = <A>(
  operation: string,
  evaluate: () => Promise<A>,
): Effect.Effect<A, KnowledgeCoreServiceError> =>
  Effect.tryPromise({
    try: evaluate,
    catch: (cause) => knowledgeCoreServiceError(operation, cause),
  });

const closeResource = (
  resource: {readonly close: () => Promise<void>},
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

const sendResponse = Effect.fnUntraced(function* (
  stateRef: SynchronizedRef.SynchronizedRef<KnowledgeCoreServiceState>,
  response: KnowledgeResponse,
  requestId: string,
  operation = "respond",
) {
  const responseProducer = (yield* SynchronizedRef.get(stateRef)).responseProducer;
  if (responseProducer === null) {
    return yield* knowledgeCoreServiceError(operation, "Knowledge response producer not started");
  }

  yield* tryPromise(operation, () => responseProducer.send(response, {id: requestId}));
});

const readPersistedKnowledgeEffect = Effect.fn("KnowledgeCoreService.readPersistedKnowledge")(
  function* (persistPath: string) {
    const raw = yield* tryPromise("load-read", () => readTextFile(persistPath));
    const current = S.decodeUnknownOption(PersistedKnowledgeSnapshotJsonSchema)(raw);
    if (O.isSome(current)) {
      return {
        kgCores: kgStoreFromRecord(current.value.kg),
        deCores: deStoreFromRecord(current.value.de),
      };
    }

    const legacy = S.decodeUnknownOption(LegacyKnowledgeSnapshotJsonSchema)(raw);
    if (O.isSome(legacy)) {
      return {
        kgCores: kgStoreFromRecord(legacy.value),
        deCores: HashMap.empty<string, Array<DocumentEmbeddingsCore>>(),
      };
    }

    return yield* knowledgeCoreServiceError("load-decode", "Persisted knowledge state did not match any known shape");
  },
  (effect) =>
    effect.pipe(
      Effect.catch(() =>
        Effect.log("[KnowledgeCoreService] No persisted state found, starting fresh").pipe(
          Effect.flatMap(() =>
            Effect.succeed<{
              readonly kgCores: KnowledgeCoreStore;
              readonly deCores: DocumentCoreStore;
            } | null>(null)
          ),
        )
      ),
    ),
  );

const persistStateEffect = Effect.fn("KnowledgeCoreService.persistState")(
  function* (persistPath: string, state: KnowledgeCoreServiceState) {
    const snapshot = toPersistedSnapshot(state);
    const json = yield* S.encodeUnknownEffect(S.UnknownFromJsonString)(snapshot).pipe(
      Effect.mapError((cause) => knowledgeCoreServiceError("persist-encode", cause)),
    );
    yield* tryPromise("persist-write", () => writeTextFile(persistPath, json));
  },
  (effect) =>
    effect.pipe(
      Effect.catch((error) =>
        Effect.logError("[KnowledgeCoreService] Failed to persist state", {
          error: error.message,
        }),
      ),
    ),
);

const listIds = <A>(
  store: HashMap.HashMap<string, A>,
  user: string,
): Array<string> => {
  const prefix = user.length > 0 ? `${user}:` : "";
  const ids: Array<string> = [];

  for (const [key] of sortedEntries(store)) {
    if (prefix.length === 0 || key.startsWith(prefix)) {
      ids.push(key.slice(prefix.length));
    }
  }

  return ids;
};

const closeKnowledgeResourcesEffect = Effect.fn("KnowledgeCoreService.closeResources")(function* (
  stateRef: SynchronizedRef.SynchronizedRef<KnowledgeCoreServiceState>,
) {
  const state = yield* SynchronizedRef.get(stateRef);

  const consumer = state.consumer;
  if (consumer !== null) {
    yield* tryPromise("close-consumer", () => consumer.close());
  }

  const responseProducer = state.responseProducer;
  if (responseProducer !== null) {
    yield* tryPromise("close-response-producer", () => responseProducer.close());
  }

  yield* updateHandles(stateRef, {
    consumer: null,
    responseProducer: null,
  });
});

const consumeOnceEffect = Effect.fnUntraced(function* (
  service: KnowledgeCoreService,
) {
  const consumer = (yield* SynchronizedRef.get(service.state)).consumer;
  if (consumer === null) {
    return yield* knowledgeCoreServiceError("consume", "Knowledge request consumer not started");
  }

  const msg = yield* tryPromise("consume-receive", () => consumer.receive(2000));
  if (msg === null) return;

  yield* service.handleMessageEffect(msg);
  yield* tryPromise("consume-acknowledge", () => consumer.acknowledge(msg));
});

const runKnowledgeCoreServiceEffect = Effect.fn("KnowledgeCoreService.run")(function* (
  service: KnowledgeCoreService,
) {
  yield* tryPromise("ensure-directory", () => ensureDirectory(service.dataDir));
  yield* service.loadFromDiskEffect;

  const responseProducer = yield* tryPromise("response-producer", () =>
    service.pubsub.createProducer<KnowledgeResponse>({
      topic: topics.knowledgeResponse,
      schema: KnowledgeResponseSchema,
    }),
  );
  yield* updateHandles(service.state, {responseProducer});

  const consumer = yield* tryPromise("consumer", () =>
    service.pubsub.createConsumer<KnowledgeRequest>({
      topic: topics.knowledgeRequest,
      subscription: `${service.config.id}-knowledge-request`,
      schema: KnowledgeRequestSchema,
    }),
  );
  yield* updateHandles(service.state, {consumer});

  yield* Effect.log(`[KnowledgeCoreService] Listening on ${topics.knowledgeRequest}`);

  yield* Effect.whileLoop({
    while: () => service.running,
    body: () =>
      consumeOnceEffect(service).pipe(
        Effect.catch((error) => {
          if (!service.running) return Effect.void;
          return Effect.logError("[KnowledgeCoreService] Error in consume loop", {
            error: error.message,
          }).pipe(
            Effect.flatMap(() => Effect.sleep(Duration.millis(1000))),
          );
        }),
      ),
    step: () => undefined,
  });
});

const listKgCoresEffect = (
  stateRef: SynchronizedRef.SynchronizedRef<KnowledgeCoreServiceState>,
  request: KnowledgeRequest,
  requestId: string,
) =>
  SynchronizedRef.get(stateRef).pipe(
    Effect.flatMap((state) => sendResponse(stateRef, {ids: listIds(state.kgCores, request.user ?? "")}, requestId)),
  );

const getKgCoreEffect = Effect.fn("getKgCoreEffect")(function* (
  stateRef: SynchronizedRef.SynchronizedRef<KnowledgeCoreServiceState>,
  request: KnowledgeRequest,
  requestId: string,
) {
    const key = coreKey(request.user ?? "", request.id ?? "");
    const core = getHashMapValue((yield* SynchronizedRef.get(stateRef)).kgCores, key);
    if (core === undefined) {
      return yield* knowledgeCoreServiceError("get-kg-core", `Knowledge core not found: ${key}`);
    }

    const batchSize = 100;
    for (let i = 0; i < core.triples.length; i += batchSize) {
      const batch = core.triples.slice(i, i + batchSize);
      const isLast = i + batchSize >= core.triples.length && core.graphEmbeddings.length === 0;
      yield* sendResponse(stateRef, {triples: batch, eos: isLast}, requestId, "respond-kg-triples");
    }

    for (let i = 0; i < core.graphEmbeddings.length; i += batchSize) {
      const batch = core.graphEmbeddings.slice(i, i + batchSize);
      const isLast = i + batchSize >= core.graphEmbeddings.length;
      yield* sendResponse(
        stateRef,
        {
          graphEmbeddings: batch,
          "graph-embeddings": batch,
          eos: isLast,
        },
        requestId,
        "respond-kg-embeddings",
      );
    }

    if (core.triples.length === 0 && core.graphEmbeddings.length === 0) {
      yield* sendResponse(stateRef, {eos: true}, requestId, "respond-kg-empty");
    }
});

const deleteKgCoreEffect = Effect.fn("deleteKgCoreEffect")(function* (
  stateRef: SynchronizedRef.SynchronizedRef<KnowledgeCoreServiceState>,
  persistPath: string,
  request: KnowledgeRequest,
  requestId: string,
) {
    const key = coreKey(request.user ?? "", request.id ?? "");
    const next = yield* SynchronizedRef.updateAndGet(stateRef, (state) => ({
      ...state,
      kgCores: HashMap.remove(state.kgCores, key),
    }));

    yield* persistStateEffect(persistPath, next);
    yield* Effect.log(`[KnowledgeCoreService] Deleted core: ${key}`);
    yield* sendResponse(stateRef, {}, requestId);
});

const putKgCoreEffect = Effect.fn("putKgCoreEffect")(function* (
  stateRef: SynchronizedRef.SynchronizedRef<KnowledgeCoreServiceState>,
  persistPath: string,
  request: KnowledgeRequest,
  requestId: string,
) {
    const key = coreKey(request.user ?? "", request.id ?? "");
    const next = yield* SynchronizedRef.updateAndGet(stateRef, (state) => {
      const existing = getHashMapValue(state.kgCores, key) ?? {triples: [], graphEmbeddings: []};
      const core: KnowledgeCore = {
        triples: [
          ...existing.triples,
          ...Array.from(request.triples ?? []),
        ],
        graphEmbeddings: [
          ...existing.graphEmbeddings,
          ...graphEmbeddingsFor(request).map((entry) => ({
            entity: entry.entity,
            vectors: entry.vectors.map((vector) => Array.from(vector)),
          })),
        ],
      };
      return {
        ...state,
        kgCores: HashMap.set(state.kgCores, key, core),
      };
    });

    const core = getHashMapValue(next.kgCores, key);
    yield* persistStateEffect(persistPath, next);
    yield* Effect.log(
      `[KnowledgeCoreService] Updated core ${key}: triples=${core?.triples.length ?? 0}, embeddings=${core?.graphEmbeddings.length ?? 0}`,
    );
    yield* sendResponse(stateRef, {}, requestId);
});

const loadKgCoreEffect = Effect.fn("loadKgCoreEffect")(function* (
  stateRef: SynchronizedRef.SynchronizedRef<KnowledgeCoreServiceState>,
  service: KnowledgeCoreService,
  request: KnowledgeRequest,
  requestId: string,
) {
    const user = request.user ?? "";
    const coreId = request.id ?? "";
    const key = coreKey(user, coreId);
    const core = getHashMapValue((yield* SynchronizedRef.get(stateRef)).kgCores, key);
    if (core === undefined) {
      return yield* knowledgeCoreServiceError("load-kg-core", `Knowledge core not found: ${key}`);
    }

    if (core.triples.length > 0) {
      yield* Effect.acquireUseRelease(
        tryPromise("triples-producer", () =>
          service.pubsub.createProducer<unknown>({topic: "tg.flow.triples"}),
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
    yield* sendResponse(stateRef, {}, requestId);
});

const listDeCoresEffect = (
  stateRef: SynchronizedRef.SynchronizedRef<KnowledgeCoreServiceState>,
  request: KnowledgeRequest,
  requestId: string,
) =>
  SynchronizedRef.get(stateRef).pipe(
    Effect.flatMap((state) => sendResponse(stateRef, {ids: listIds(state.deCores, request.user ?? "")}, requestId)),
  );

const getDeCoreEffect = Effect.fn("getDeCoreEffect")(function* (
  stateRef: SynchronizedRef.SynchronizedRef<KnowledgeCoreServiceState>,
  request: KnowledgeRequest,
  requestId: string,
) {
    const key = coreKey(request.user ?? "", request.id ?? "");
    const core = getHashMapValue((yield* SynchronizedRef.get(stateRef)).deCores, key);
    if (core === undefined) {
      return yield* knowledgeCoreServiceError("get-de-core", `Document embeddings core not found: ${key}`);
    }

    for (const [index, item] of core.entries()) {
      yield* sendResponse(
        stateRef,
        {
          documentEmbeddings: item,
          "document-embeddings": item,
          eos: index === core.length - 1,
        },
        requestId,
        "respond-de-core",
      );
    }

    if (core.length === 0) {
      yield* sendResponse(stateRef, {eos: true}, requestId, "respond-de-empty");
    }
});

const deleteDeCoreEffect = Effect.fn("deleteDeCoreEffect")(function* (
  stateRef: SynchronizedRef.SynchronizedRef<KnowledgeCoreServiceState>,
  persistPath: string,
  request: KnowledgeRequest,
  requestId: string,
) {
    const key = coreKey(request.user ?? "", request.id ?? "");
    const next = yield* SynchronizedRef.updateAndGet(stateRef, (state) => ({
      ...state,
      deCores: HashMap.remove(state.deCores, key),
    }));

    yield* persistStateEffect(persistPath, next);
    yield* sendResponse(stateRef, {}, requestId);
});

const putDeCoreEffect = Effect.fn("putDeCoreEffect")(function* (
  stateRef: SynchronizedRef.SynchronizedRef<KnowledgeCoreServiceState>,
  persistPath: string,
  request: KnowledgeRequest,
  requestId: string,
) {
    const item = documentEmbeddingsFor(request);
    if (item === undefined) {
      return yield* knowledgeCoreServiceError("put-de-core", "put-de-core requires document-embeddings");
    }

    const key = coreKey(request.user ?? "", request.id ?? "");
    const next = yield* SynchronizedRef.updateAndGet(stateRef, (state) => ({
      ...state,
      deCores: HashMap.set(state.deCores, key, [
        ...(getHashMapValue(state.deCores, key) ?? []),
        item,
      ]),
    }));

    yield* persistStateEffect(persistPath, next);
    yield* sendResponse(stateRef, {}, requestId);
});

const loadDeCoreEffect = Effect.fn("loadDeCoreEffect")(function* (
  stateRef: SynchronizedRef.SynchronizedRef<KnowledgeCoreServiceState>,
  request: KnowledgeRequest,
  requestId: string,
) {
    const key = coreKey(request.user ?? "", request.id ?? "");
    const exists = HashMap.has((yield* SynchronizedRef.get(stateRef)).deCores, key);
    if (!exists) {
      return yield* knowledgeCoreServiceError("load-de-core", `Document embeddings core not found: ${key}`);
    }
    yield* sendResponse(stateRef, {}, requestId);
});

export function makeKnowledgeCoreService(config: KnowledgeCoreServiceConfig): KnowledgeCoreService {
  const dataDir = config.dataDir ?? "./data/knowledge";
  const persistPath = joinPath(dataDir, "knowledge-state.json");
  const state = SynchronizedRef.makeUnsafe(initialState());
  let service: KnowledgeCoreService | undefined;

  const getService = Effect.sync(() => service).pipe(
    Effect.flatMap((current) =>
      current === undefined
        ? Effect.fail(knowledgeCoreServiceError("service", "Knowledge core service not initialized"))
        : Effect.succeed(current)
    ),
  );

  const base = makeAsyncProcessor<KnowledgeCoreServiceError>(config, {
    runEffect: () => getService.pipe(Effect.flatMap(runKnowledgeCoreServiceEffect)),
  });
  const baseStop = base.stop;

  const handleOperationEffect = Effect.fn("KnowledgeCoreService.handleOperation")(function* (
    request: KnowledgeRequest,
    requestId: string,
  ) {
    const operation: KnowledgeOperation = request.operation;

    return yield* Match.value(operation).pipe(
      Match.when("list-kg-cores", () => listKgCoresEffect(state, request, requestId)),
      Match.when("get-kg-core", () => getKgCoreEffect(state, request, requestId)),
      Match.when("delete-kg-core", () => deleteKgCoreEffect(state, persistPath, request, requestId)),
      Match.when("put-kg-core", () => putKgCoreEffect(state, persistPath, request, requestId)),
      Match.when("load-kg-core", () =>
        getService.pipe(Effect.flatMap((current) => loadKgCoreEffect(state, current, request, requestId)))
      ),
      Match.when("unload-kg-core", () => sendResponse(state, {}, requestId)),
      Match.when("list-de-cores", () => listDeCoresEffect(state, request, requestId)),
      Match.when("get-de-core", () => getDeCoreEffect(state, request, requestId)),
      Match.when("delete-de-core", () => deleteDeCoreEffect(state, persistPath, request, requestId)),
      Match.when("put-de-core", () => putDeCoreEffect(state, persistPath, request, requestId)),
      Match.when("load-de-core", () => loadDeCoreEffect(state, request, requestId)),
      Match.exhaustive,
    );
  });

  const handleMessageEffect = Effect.fn("KnowledgeCoreService.handleMessage")(function* (msg: Message<KnowledgeRequest>) {
    const request = yield* S.decodeUnknownEffect(KnowledgeRequestSchema)(msg.value()).pipe(
      Effect.mapError((cause) => knowledgeCoreServiceError("decode", cause)),
    );
    const requestId = msg.properties().id;

    if (requestId === undefined || requestId.length === 0) {
      yield* Effect.logWarning("[KnowledgeCoreService] Received request without id, ignoring");
      return;
    }

    yield* handleOperationEffect(request, requestId).pipe(
      Effect.catch((error) =>
        sendResponse(
          state,
          {error: {type: "knowledge-error", message: error.message}},
          requestId,
          "respond-error",
        )
      ),
    );
  });

  const loadFromDiskEffect = Effect.fn("KnowledgeCoreService.loadFromDisk")(function* () {
    const loaded = yield* readPersistedKnowledgeEffect(persistPath);
    if (loaded === null) return;

    const next = yield* SynchronizedRef.updateAndGet(state, (current) => ({
      ...current,
      kgCores: loaded.kgCores,
      deCores: loaded.deCores,
    }));

    yield* Effect.log(`[KnowledgeCoreService] Loaded persisted state (kg=${HashMap.size(next.kgCores)}, de=${HashMap.size(next.deCores)})`);
  });

  service = Object.assign(base, {
    state,
    dataDir,
    persistPath,
    coreKey,
    graphEmbeddings: graphEmbeddingsFor,
    documentEmbeddings: documentEmbeddingsFor,
    handleMessage: (msg: Message<KnowledgeRequest>) => Effect.runPromise(handleMessageEffect(msg)),
    handleMessageEffect,
    handleOperation: (request: KnowledgeRequest, requestId: string) => Effect.runPromise(handleOperationEffect(request, requestId)),
    handleOperationEffect,
    listKgCores: (request: KnowledgeRequest, requestId: string) => Effect.runPromise(listKgCoresEffect(state, request, requestId)),
    listKgCoresEffect: (request: KnowledgeRequest, requestId: string) => listKgCoresEffect(state, request, requestId),
    getKgCore: (request: KnowledgeRequest, requestId: string) => Effect.runPromise(getKgCoreEffect(state, request, requestId)),
    getKgCoreEffect: (request: KnowledgeRequest, requestId: string) => getKgCoreEffect(state, request, requestId),
    deleteKgCore: (request: KnowledgeRequest, requestId: string) => Effect.runPromise(deleteKgCoreEffect(state, persistPath, request, requestId)),
    deleteKgCoreEffect: (request: KnowledgeRequest, requestId: string) => deleteKgCoreEffect(state, persistPath, request, requestId),
    putKgCore: (request: KnowledgeRequest, requestId: string) => Effect.runPromise(putKgCoreEffect(state, persistPath, request, requestId)),
    putKgCoreEffect: (request: KnowledgeRequest, requestId: string) => putKgCoreEffect(state, persistPath, request, requestId),
    loadKgCore: (request: KnowledgeRequest, requestId: string) =>
      Effect.runPromise(getService.pipe(Effect.flatMap((current) => loadKgCoreEffect(state, current, request, requestId)))),
    loadKgCoreEffect: (request: KnowledgeRequest, requestId: string) =>
      getService.pipe(Effect.flatMap((current) => loadKgCoreEffect(state, current, request, requestId))),
    unloadKgCore: (_request: KnowledgeRequest, requestId: string) => Effect.runPromise(sendResponse(state, {}, requestId)),
    unloadKgCoreEffect: (_request: KnowledgeRequest, requestId: string) => sendResponse(state, {}, requestId),
    listDeCores: (request: KnowledgeRequest, requestId: string) => Effect.runPromise(listDeCoresEffect(state, request, requestId)),
    listDeCoresEffect: (request: KnowledgeRequest, requestId: string) => listDeCoresEffect(state, request, requestId),
    getDeCore: (request: KnowledgeRequest, requestId: string) => Effect.runPromise(getDeCoreEffect(state, request, requestId)),
    getDeCoreEffect: (request: KnowledgeRequest, requestId: string) => getDeCoreEffect(state, request, requestId),
    deleteDeCore: (request: KnowledgeRequest, requestId: string) => Effect.runPromise(deleteDeCoreEffect(state, persistPath, request, requestId)),
    deleteDeCoreEffect: (request: KnowledgeRequest, requestId: string) => deleteDeCoreEffect(state, persistPath, request, requestId),
    putDeCore: (request: KnowledgeRequest, requestId: string) => Effect.runPromise(putDeCoreEffect(state, persistPath, request, requestId)),
    putDeCoreEffect: (request: KnowledgeRequest, requestId: string) => putDeCoreEffect(state, persistPath, request, requestId),
    loadDeCore: (request: KnowledgeRequest, requestId: string) => Effect.runPromise(loadDeCoreEffect(state, request, requestId)),
    loadDeCoreEffect: (request: KnowledgeRequest, requestId: string) => loadDeCoreEffect(state, request, requestId),
    persist: () => Effect.runPromise(SynchronizedRef.get(state).pipe(Effect.flatMap((current) => persistStateEffect(persistPath, current)))),
    persistEffect: SynchronizedRef.get(state).pipe(Effect.flatMap((current) => persistStateEffect(persistPath, current))),
    loadFromDisk: () => Effect.runPromise(loadFromDiskEffect()),
    loadFromDiskEffect: loadFromDiskEffect(),
    stop: () =>
      Effect.runPromise(
        closeKnowledgeResourcesEffect(state).pipe(
          Effect.flatMap(() =>
            tryPromise("base-stop", () => baseStop())
          ),
        ),
      ),
  });

  return service;
}

export const KnowledgeCoreService = makeKnowledgeCoreService;

export const loadKnowledgeCoreServiceRuntimeConfig = Effect.fn("loadKnowledgeCoreServiceRuntimeConfig")(function* () {
  const processorConfig = yield* loadProcessorRuntimeConfig("knowledge-svc", {
    manageProcessSignals: false,
  });
  const dataDir = yield* optionalStringConfig("KNOWLEDGE_DATA_DIR");
  return {
    ...processorConfig,
    ...(dataDir !== undefined ? {dataDir} : {}),
  } satisfies KnowledgeCoreServiceConfig;
});

export const program = makeProcessorProgram({
  id: "knowledge-svc",
  loadConfig: loadKnowledgeCoreServiceRuntimeConfig(),
  make: (config) => makeKnowledgeCoreService(config),
});

const knowledgeCoreRuntime = ManagedRuntime.make(Layer.empty);

export function run(): Promise<void> {
  return knowledgeCoreRuntime.runPromise(program);
}

export function runMain(): void {
  NodeRuntime.runMain(program);
}
