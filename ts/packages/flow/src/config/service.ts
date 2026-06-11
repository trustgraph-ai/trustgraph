/**
 * Config service — manages system global configuration state.
 *
 * Python reference: trustgraph-flow/trustgraph/config/service/service.py
 */

import {NodeRuntime} from "@effect/platform-node";
import {Array as A, Duration, Effect, HashMap, Match, Option, Order, SynchronizedRef} from "effect";
import * as Predicate from "effect/Predicate";
import * as S from "effect/Schema";
import type {
  AsyncProcessorRuntime,
  BackendConsumer,
  BackendProducer,
  ConfigOperation,
  ConfigRequest,
  ConfigResponse,
  Message,
  ProcessorConfig,
} from "@trustgraph/base";
import {
  ConfigRequest as ConfigRequestSchema,
  ConfigResponse as ConfigResponseSchema,
  errorMessage,
  loadProcessorRuntimeConfig,
  makeAsyncProcessor,
  makeProcessorProgram,
  optionalStringConfig,
  processorLifecycleError,
  topics,
} from "@trustgraph/base";
import {readTextFileEffect, writeTextFileEffect} from "../runtime/effect-files.js";

export interface ConfigServiceConfig extends ProcessorConfig {
  readonly persistPath?: string;
}

interface ConfigPush {
  readonly version: number;
  readonly config: Record<string, unknown>;
}

const ConfigPushSchema = S.Struct({
  version: S.Finite,
  config: S.Record(S.String, S.Unknown),
});

export class ConfigServiceError extends S.TaggedErrorClass<ConfigServiceError>()(
  "ConfigServiceError",
  {
    message: S.String,
    operation: S.String,
  },
) {}

const configServiceError = (operation: string, cause: unknown): ConfigServiceError =>
  ConfigServiceError.make({
    operation,
    message: errorMessage(cause),
  });

const DEFAULT_WORKSPACE = "default";

interface ConfigKeyLike {
  readonly type: string;
  readonly key?: string;
}

interface ConfigValueLike {
  readonly workspace?: string;
  readonly type: string;
  readonly key: string;
  readonly value: unknown;
}

type NamespaceStore = HashMap.HashMap<string, unknown>;
type WorkspaceStore = HashMap.HashMap<string, NamespaceStore>;
type ConfigStore = HashMap.HashMap<string, WorkspaceStore>;
type WorkspaceSnapshot = Record<string, Record<string, Record<string, unknown>>>;

interface ConfigServiceState {
  readonly version: number;
  readonly store: ConfigStore;
  readonly consumer: BackendConsumer<ConfigRequest> | null;
  readonly responseProducer: BackendProducer<ConfigResponse> | null;
  readonly pushProducer: BackendProducer<ConfigPush> | null;
}

const PersistedConfigSchema = S.Struct({
  version: S.optionalKey(S.Finite),
  data: S.optionalKey(S.Record(S.String, S.Record(S.String, S.Unknown))),
  workspaces: S.optionalKey(S.Record(S.String, S.Record(S.String, S.Record(S.String, S.Unknown)))),
});
const PersistedConfigJsonSchema = PersistedConfigSchema.pipe(S.fromJsonString);
type PersistedConfig = typeof PersistedConfigSchema.Type;

export interface ConfigService extends AsyncProcessorRuntime<ConfigServiceError> {
  readonly state: SynchronizedRef.SynchronizedRef<ConfigServiceState>;
  readonly persistPath: string | null;
  readonly handleMessageEffect: (msg: Message<ConfigRequest>) => Effect.Effect<void, ConfigServiceError>;
  readonly handleOperationEffect: (request: ConfigRequest) => Effect.Effect<ConfigResponse, ConfigServiceError>;
  readonly handleGet: (request: ConfigRequest) => ConfigResponse;
  readonly handlePutEffect: (request: ConfigRequest) => Effect.Effect<ConfigResponse, ConfigServiceError>;
  readonly handleDeleteEffect: (request: ConfigRequest) => Effect.Effect<ConfigResponse, ConfigServiceError>;
  readonly handleList: (request: ConfigRequest) => ConfigResponse;
  readonly handleGetValues: (request: ConfigRequest) => ConfigResponse;
  readonly handleGetValuesAllWorkspaces: (request: ConfigRequest) => ConfigResponse;
  readonly handleConfigDump: (request: ConfigRequest) => ConfigResponse;
  readonly pushConfigEffect: Effect.Effect<void, ConfigServiceError>;
  readonly persistEffect: Effect.Effect<void>;
  readonly loadFromDiskEffect: Effect.Effect<void>;
}

const initialState = (): ConfigServiceState => ({
  version: 0,
  store: HashMap.empty<string, WorkspaceStore>(),
  consumer: null,
  responseProducer: null,
  pushProducer: null,
});

const getHashMapValue = <K, V>(store: HashMap.HashMap<K, V>, key: K): V | undefined =>
  Option.getOrUndefined(HashMap.get(store, key));

const workspaceOrder = Order.make<string>((left, right) =>
  left === right
    ? 0
    : left === DEFAULT_WORKSPACE
      ? -1
      : right === DEFAULT_WORKSPACE
        ? 1
        : Order.String(left, right)
);

const orderByKey = <A>(order: Order.Order<string>): Order.Order<readonly [string, A]> =>
  Order.mapInput(order, ([key]) => key);

const workspaceEntries = (store: ConfigStore): ReadonlyArray<readonly [string, WorkspaceStore]> =>
  A.sort(HashMap.toEntries(store), orderByKey<WorkspaceStore>(workspaceOrder));

const namespaceEntries = (store: WorkspaceStore): ReadonlyArray<readonly [string, NamespaceStore]> =>
  A.sort(HashMap.toEntries(store), orderByKey<NamespaceStore>(Order.String));

const valueEntries = (store: NamespaceStore): ReadonlyArray<readonly [string, unknown]> =>
  A.sort(HashMap.toEntries(store), orderByKey<unknown>(Order.String));

const toPersistedWorkspaces = (
  store: ConfigStore,
): WorkspaceSnapshot => {
  const workspaces: WorkspaceSnapshot = {};

  for (const [workspace, ws] of workspaceEntries(store)) {
    const workspaceData: Record<string, Record<string, unknown>> = {};
    for (const [namespace, subMap] of namespaceEntries(ws)) {
      const obj: Record<string, unknown> = {};
      for (const [key, value] of valueEntries(subMap)) {
        obj[key] = value;
      }
      workspaceData[namespace] = obj;
    }
    workspaces[workspace] = workspaceData;
  }

  return workspaces;
};

const workspaceStoreFromPersistedNamespaces = (
  namespaces: Record<string, Record<string, unknown>>,
): WorkspaceStore => {
  let workspaceStore = HashMap.empty<string, NamespaceStore>();

  for (const [namespace, obj] of Object.entries(namespaces)) {
    let namespaceStore = HashMap.empty<string, unknown>();
    for (const [key, value] of Object.entries(obj)) {
      namespaceStore = HashMap.set(namespaceStore, key, value);
    }
    workspaceStore = HashMap.set(workspaceStore, namespace, namespaceStore);
  }

  return workspaceStore;
};

const storeFromPersistedConfig = (parsed: PersistedConfig): ConfigStore => {
  let store = HashMap.empty<string, WorkspaceStore>();

  if (parsed.workspaces !== undefined) {
    for (const [workspace, namespaces] of Object.entries(parsed.workspaces)) {
      store = HashMap.set(store, workspace, workspaceStoreFromPersistedNamespaces(namespaces));
    }
    return store;
  }

  return HashMap.set(store, DEFAULT_WORKSPACE, workspaceStoreFromPersistedNamespaces(parsed.data ?? {}));
};

const optionalString = (value: unknown): string | undefined =>
  Predicate.isString(value) && value.length > 0 ? value : undefined;

const requestProperty = (request: ConfigRequest, property: string): unknown =>
  Predicate.hasProperty(request, property) ? request[property] : undefined;

const rawKeys = (request: ConfigRequest): ReadonlyArray<unknown> => {
  const keys = requestProperty(request, "keys");
  return Array.isArray(keys) ? keys : [];
};

const stringKeys = (request: ConfigRequest): Array<string> =>
  rawKeys(request).filter(Predicate.isString);

const objectKeys = (request: ConfigRequest): Array<ConfigKeyLike> =>
  rawKeys(request).flatMap((key) => {
    if (!Predicate.isObject(key)) return [];
    const type = optionalString(key.type);
    if (type === undefined) return [];
    const keyValue = optionalString(key.key);
    return [
      keyValue === undefined
        ? {type}
        : {type, key: keyValue},
    ];
  });

const workspaceFor = (request: ConfigRequest): string =>
  optionalString(requestProperty(request, "workspace")) ?? DEFAULT_WORKSPACE;

const requestType = (request: ConfigRequest): string | undefined =>
  optionalString(requestProperty(request, "type")) ?? stringKeys(request)[0];

const configValues = (request: ConfigRequest): Array<ConfigValueLike> => {
  const rawValues = requestProperty(request, "values");
  const workspace = workspaceFor(request);

  if (Array.isArray(rawValues)) {
    return rawValues.flatMap((value) => {
      if (!Predicate.isObject(value)) return [];
      const type = optionalString(value.type);
      const key = optionalString(value.key);
      if (type === undefined || key === undefined) return [];
      return [{
        workspace: optionalString(value.workspace) ?? workspace,
        type,
        key,
        value: value.value,
      }];
    });
  }

  if (Predicate.isObject(rawValues)) {
    const namespace = requestType(request);
    if (namespace === undefined) return [];
    return Object.entries(rawValues).map(([key, value]) => ({
      workspace,
      type: namespace,
      key,
      value,
    }));
  }

  return [];
};

const getWorkspaceStore = (
  state: ConfigServiceState,
  workspace: string,
): WorkspaceStore | undefined =>
  getHashMapValue(state.store, workspace);

const getNamespaceStore = (
  state: ConfigServiceState,
  workspace: string,
  namespace: string,
): NamespaceStore | undefined =>
  Option.flatMap(HashMap.get(state.store, workspace), HashMap.get(namespace)).pipe(Option.getOrUndefined);

const configDumpForState = (
  state: ConfigServiceState,
  workspace: string = DEFAULT_WORKSPACE,
): Record<string, unknown> => {
  const config: Record<string, unknown> = {};
  const ws = getWorkspaceStore(state, workspace);

  if (ws === undefined) return config;

  for (const [namespace, subMap] of namespaceEntries(ws)) {
    const obj: Record<string, unknown> = {};
    for (const [key, value] of valueEntries(subMap)) {
      obj[key] = value;
    }
    config[namespace] = obj;
  }

  return config;
};

const stateSnapshot = (stateRef: SynchronizedRef.SynchronizedRef<ConfigServiceState>): ConfigServiceState =>
  SynchronizedRef.getUnsafe(stateRef);

const updateHandles = (
  stateRef: SynchronizedRef.SynchronizedRef<ConfigServiceState>,
  handles: {
    readonly consumer?: BackendConsumer<ConfigRequest> | null;
    readonly responseProducer?: BackendProducer<ConfigResponse> | null;
    readonly pushProducer?: BackendProducer<ConfigPush> | null;
  },
) =>
  SynchronizedRef.updateAndGet(stateRef, (state) => ({
    ...state,
    consumer: handles.consumer === undefined ? state.consumer : handles.consumer,
    responseProducer: handles.responseProducer === undefined ? state.responseProducer : handles.responseProducer,
    pushProducer: handles.pushProducer === undefined ? state.pushProducer : handles.pushProducer,
  }));

const persistStateEffect = Effect.fn("ConfigService.persistState")(
  function* (persistPath: string | null, state: ConfigServiceState) {
    if (persistPath === null) return;
    const payload = {
      version: state.version,
      workspaces: toPersistedWorkspaces(state.store),
    };

    const json = yield* S.encodeUnknownEffect(S.UnknownFromJsonString)(payload).pipe(
      Effect.mapError((cause) => configServiceError("persist-encode", cause)),
    );

    yield* writeTextFileEffect(persistPath, json).pipe(
      Effect.mapError((cause) => configServiceError("persist-write", cause)),
    );
  },
  (effect) =>
    effect.pipe(
      Effect.catch((err) =>
        Effect.logError("[ConfigService] Failed to persist config", {error: err.message}),
      ),
    ),
);

const pushConfigWithStateEffect = Effect.fn("ConfigService.pushConfigWithState")(function* (
  state: ConfigServiceState,
) {
  const pushProducer = state.pushProducer;
  if (pushProducer === null) return;

  yield* pushProducer.send({
    version: state.version,
    config: configDumpForState(state),
  }).pipe(
    Effect.mapError((cause) => configServiceError("push-config", cause)),
  );

  yield* Effect.log(`[ConfigService] Pushed configuration version ${state.version}`);
});

const readPersistedConfigEffect = Effect.fn("ConfigService.readPersistedConfig")(
  function* (persistPath: string) {
    const raw = yield* readTextFileEffect(persistPath).pipe(
      Effect.mapError((cause) => configServiceError("persist-read", cause)),
    );
    return yield* S.decodeUnknownEffect(PersistedConfigJsonSchema)(raw).pipe(
      Effect.mapError((cause) => configServiceError("persist-decode", cause)),
    );
  },
  (effect) =>
    effect.pipe(
      Effect.catch(() =>
        Effect.log("[ConfigService] No persisted config found, starting fresh").pipe(
          Effect.flatMap(() => Effect.succeed<PersistedConfig | null>(null)),
        )
      ),
    ),
  );

const handleGetWithState = (
  state: ConfigServiceState,
  request: ConfigRequest,
): ConfigResponse => {
  const workspace = workspaceFor(request);
  const keysByObject = objectKeys(request);

  if (keysByObject.length > 0) {
    const values = keysByObject.map((key) => ({
      type: key.type,
      key: key.key ?? "",
      value: key.key !== undefined
        ? getHashMapValue(getNamespaceStore(state, workspace, key.type) ?? HashMap.empty<string, unknown>(), key.key)
        : undefined,
    }));
    return {version: state.version, values};
  }

  const keys = stringKeys(request);
  if (keys.length === 0) {
    return {version: state.version, values: {}};
  }

  const values: Record<string, unknown> = {};
  const namespace = keys[0];
  const subMap = getNamespaceStore(state, workspace, namespace);

  if (subMap !== undefined) {
    if (keys.length === 1) {
      for (const [key, value] of valueEntries(subMap)) {
        values[key] = value;
      }
    } else {
      for (const key of keys.slice(1)) {
        const value = getHashMapValue(subMap, key);
        if (value !== undefined || HashMap.has(subMap, key)) {
          values[key] = value;
        }
      }
    }
  }

  return {version: state.version, values};
};

const applyPut = (
  state: ConfigServiceState,
  values: ReadonlyArray<ConfigValueLike>,
): ConfigServiceState => {
  let store = state.store;

  for (const item of values) {
    const workspace = item.workspace ?? DEFAULT_WORKSPACE;
    const workspaceStore = getHashMapValue(store, workspace) ?? HashMap.empty<string, NamespaceStore>();
    const namespaceStore = getHashMapValue(workspaceStore, item.type) ?? HashMap.empty<string, unknown>();
    const nextNamespaceStore = HashMap.set(namespaceStore, item.key, item.value);
    const nextWorkspaceStore = HashMap.set(workspaceStore, item.type, nextNamespaceStore);
    store = HashMap.set(store, workspace, nextWorkspaceStore);
  }

  return {
    ...state,
    store,
    version: state.version + 1,
  };
};

const applyDeleteObjectKeys = (
  state: ConfigServiceState,
  workspace: string,
  keys: ReadonlyArray<ConfigKeyLike>,
): ConfigServiceState => {
  let store = state.store;
  const ws = getHashMapValue(store, workspace);

  if (ws !== undefined) {
    let nextWorkspaceStore = ws;

    for (const key of keys) {
      if (key.key === undefined) {
        nextWorkspaceStore = HashMap.remove(nextWorkspaceStore, key.type);
      } else {
        const ns = getHashMapValue(nextWorkspaceStore, key.type);
        if (ns !== undefined) {
          const nextNamespaceStore = HashMap.remove(ns, key.key);
          nextWorkspaceStore = HashMap.size(nextNamespaceStore) === 0
            ? HashMap.remove(nextWorkspaceStore, key.type)
            : HashMap.set(nextWorkspaceStore, key.type, nextNamespaceStore);
        }
      }
    }

    store = HashMap.set(store, workspace, nextWorkspaceStore);
  }

  return {
    ...state,
    store,
    version: state.version + 1,
  };
};

const applyDeleteStringKeys = (
  state: ConfigServiceState,
  workspace: string,
  keys: ReadonlyArray<string>,
): ConfigServiceState => {
  let store = state.store;
  const namespace = keys[0];
  const ws = getHashMapValue(store, workspace);

  if (ws === undefined) return state;

  let nextWorkspaceStore = ws;

  if (keys.length === 1) {
    nextWorkspaceStore = HashMap.remove(nextWorkspaceStore, namespace);
  } else {
    const subMap = getHashMapValue(nextWorkspaceStore, namespace);
    if (subMap !== undefined) {
      let nextNamespaceStore = subMap;
      for (const key of keys.slice(1)) {
        nextNamespaceStore = HashMap.remove(nextNamespaceStore, key);
      }
      nextWorkspaceStore = HashMap.size(nextNamespaceStore) === 0
        ? HashMap.remove(nextWorkspaceStore, namespace)
        : HashMap.set(nextWorkspaceStore, namespace, nextNamespaceStore);
    }
  }

  store = HashMap.set(store, workspace, nextWorkspaceStore);

  return {
    ...state,
    store,
    version: state.version + 1,
  };
};

const handlePutEffect = Effect.fn("ConfigService.handlePut")(function* (
  stateRef: SynchronizedRef.SynchronizedRef<ConfigServiceState>,
  persistPath: string | null,
  request: ConfigRequest,
) {
  const values = configValues(request);
  if (values.length === 0) return yield* configServiceError("put", "Put requires config values");

  const next = yield* SynchronizedRef.updateAndGet(stateRef, (state) => applyPut(state, values));
  yield* persistStateEffect(persistPath, next);
  yield* pushConfigWithStateEffect(next);

  return {version: next.version};
});

const handleDeleteEffect = Effect.fn("ConfigService.handleDelete")(function* (
  stateRef: SynchronizedRef.SynchronizedRef<ConfigServiceState>,
  persistPath: string | null,
  request: ConfigRequest,
) {
  const workspace = workspaceFor(request);
  const keysByObject = objectKeys(request);

  if (keysByObject.length > 0) {
    const next = yield* SynchronizedRef.updateAndGet(
      stateRef,
      (state) => applyDeleteObjectKeys(state, workspace, keysByObject),
    );
    yield* persistStateEffect(persistPath, next);
    yield* pushConfigWithStateEffect(next);
    return {version: next.version};
  }

  const keys = stringKeys(request);
  if (keys.length === 0) {
    return yield* configServiceError("delete", "Delete requires at least one key");
  }

  const previous = yield* SynchronizedRef.get(stateRef);
  if (getWorkspaceStore(previous, workspace) === undefined) {
    return {version: previous.version};
  }

  const next = yield* SynchronizedRef.updateAndGet(
    stateRef,
    (state) => applyDeleteStringKeys(state, workspace, keys),
  );
  yield* persistStateEffect(persistPath, next);
  yield* pushConfigWithStateEffect(next);
  return {version: next.version};
});

const handleListWithState = (
  state: ConfigServiceState,
  request: ConfigRequest,
): ConfigResponse => {
  const workspace = workspaceFor(request);
  const ws = getWorkspaceStore(state, workspace);
  const namespace = requestType(request);

  if (namespace === undefined) {
    return {
      version: state.version,
      directory: ws !== undefined ? namespaceEntries(ws).map(([key]) => key) : [],
    };
  }

  const subMap = ws === undefined ? undefined : getHashMapValue(ws, namespace);
  return {
    version: state.version,
    directory: subMap !== undefined ? valueEntries(subMap).map(([key]) => key) : [],
  };
};

const handleGetValuesWithState = (
  state: ConfigServiceState,
  request: ConfigRequest,
): ConfigResponse => {
  const workspace = workspaceFor(request);
  const type = requestType(request) ?? "";
  const ws = getWorkspaceStore(state, workspace);
  const values: Array<{type: string; key: string; value: unknown}> = [];

  if (ws !== undefined) {
    for (const [namespace, subMap] of namespaceEntries(ws)) {
      if (type.length > 0 && namespace !== type) continue;
      for (const [key, value] of valueEntries(subMap)) {
        values.push({type: namespace, key, value});
      }
    }
  }

  return {version: state.version, values};
};

const handleGetValuesAllWorkspacesWithState = (
  state: ConfigServiceState,
  request: ConfigRequest,
): ConfigResponse => {
  const type = requestType(request) ?? "";
  const values: Array<{workspace: string; type: string; key: string; value: unknown}> = [];

  for (const [workspace, ws] of workspaceEntries(state.store)) {
    for (const [namespace, subMap] of namespaceEntries(ws)) {
      if (type.length > 0 && namespace !== type) continue;
      for (const [key, value] of valueEntries(subMap)) {
        values.push({workspace, type: namespace, key, value});
      }
    }
  }

  return {version: state.version, values};
};

const handleConfigDumpWithState = (
  state: ConfigServiceState,
  request: ConfigRequest,
): ConfigResponse => ({
  version: state.version,
  config: configDumpForState(state, workspaceFor(request)),
});

const closeConfigResourcesEffect = Effect.fn("ConfigService.closeResources")(function* (
  stateRef: SynchronizedRef.SynchronizedRef<ConfigServiceState>,
) {
  const state = yield* SynchronizedRef.get(stateRef);

  const consumer = state.consumer;
  if (consumer !== null) {
    yield* consumer.close.pipe(
      Effect.mapError((cause) => configServiceError("close-consumer", cause)),
    );
  }
  const responseProducer = state.responseProducer;
  if (responseProducer !== null) {
    yield* responseProducer.close.pipe(
      Effect.mapError((cause) => configServiceError("close-response-producer", cause)),
    );
  }
  const pushProducer = state.pushProducer;
  if (pushProducer !== null) {
    yield* pushProducer.close.pipe(
      Effect.mapError((cause) => configServiceError("close-push-producer", cause)),
    );
  }

  yield* updateHandles(stateRef, {
    consumer: null,
    responseProducer: null,
    pushProducer: null,
  });
});

const consumeOnceEffect = Effect.fnUntraced(function* (
  service: ConfigService,
) {
  const state = yield* SynchronizedRef.get(service.state);
  const consumer = state.consumer;
  if (consumer === null) {
    return yield* configServiceError("consume", "Config consumer not started");
  }

  const msg = yield* consumer.receive(2000).pipe(
    Effect.mapError((cause) => configServiceError("consume-receive", cause)),
  );
  if (msg === null) return;

  yield* service.handleMessageEffect(msg);
  yield* consumer.acknowledge(msg).pipe(
    Effect.mapError((cause) => configServiceError("consume-acknowledge", cause)),
  );
});

const runConfigServiceEffect = Effect.fn("ConfigService.run")(function* (
  service: ConfigService,
) {
  yield* service.loadFromDiskEffect;

  const responseProducer = yield* service.pubsub.createProducer<ConfigResponse>({
    topic: topics.configResponse,
    schema: ConfigResponseSchema,
  }).pipe(
    Effect.mapError((cause) => configServiceError("response-producer", cause)),
  );
  yield* updateHandles(service.state, {responseProducer});

  const pushProducer = yield* service.pubsub.createProducer<ConfigPush>({
    topic: topics.configPush,
    schema: ConfigPushSchema,
  }).pipe(
    Effect.mapError((cause) => configServiceError("push-producer", cause)),
  );
  yield* updateHandles(service.state, {pushProducer});

  const consumer = yield* service.pubsub.createConsumer<ConfigRequest>({
    topic: topics.configRequest,
    subscription: `${service.config.id}-config-request`,
    schema: ConfigRequestSchema,
  }).pipe(
    Effect.mapError((cause) => configServiceError("consumer", cause)),
  );
  const state = yield* updateHandles(service.state, {consumer});

  yield* pushConfigWithStateEffect(state);
  yield* Effect.log(`[ConfigService] Listening on ${topics.configRequest}`);

  yield* Effect.whileLoop({
    while: () => service.running,
    body: () =>
      consumeOnceEffect(service).pipe(
        Effect.catch((err) => {
          if (!service.running) return Effect.void;
          return Effect.logError("[ConfigService] Error in consume loop", {error: err.message}).pipe(
            Effect.flatMap(() => Effect.sleep(Duration.millis(1000))),
          );
        }),
      ),
    step: () => undefined,
  });
});

export function makeConfigService(config: ConfigServiceConfig): ConfigService {
  const state = SynchronizedRef.makeUnsafe(initialState());
  let service: ConfigService | undefined;

  const getService = Effect.sync(() => service).pipe(
    Effect.flatMap((current) =>
      current === undefined
        ? Effect.fail(configServiceError("service", "Config service not initialized"))
        : Effect.succeed(current)
    ),
  );

  const base = makeAsyncProcessor<ConfigServiceError>(config, {
    runEffect: () => getService.pipe(Effect.flatMap(runConfigServiceEffect)),
  });
  const persistPath = config.persistPath ?? null;

  const handleOperationEffect = Effect.fn("ConfigService.handleOperation")(function* (
    request: ConfigRequest,
  ) {
    const op: ConfigOperation = request.operation;

    return yield* Match.value(op).pipe(
      Match.when("get", () => Effect.succeed(handleGetWithState(stateSnapshot(state), request))),
      Match.when("put", () => handlePutEffect(state, persistPath, request)),
      Match.when("delete", () => handleDeleteEffect(state, persistPath, request)),
      Match.when("list", () => Effect.succeed(handleListWithState(stateSnapshot(state), request))),
      Match.when("config", () => Effect.succeed(handleConfigDumpWithState(stateSnapshot(state), request))),
      Match.when("getvalues", () => Effect.succeed(handleGetValuesWithState(stateSnapshot(state), request))),
      Match.when("getvalues-all-ws", () =>
        Effect.succeed(handleGetValuesAllWorkspacesWithState(stateSnapshot(state), request))
      ),
      Match.exhaustive,
    );
  });

  const handleMessageEffect = Effect.fn("handleMessageEffect")(function* (msg: Message<ConfigRequest>) {
      const request = yield* S.decodeUnknownEffect(ConfigRequestSchema)(msg.value()).pipe(
        Effect.mapError((cause) => configServiceError("decode", cause)),
      );
      const requestId = msg.properties().id;

      if (requestId === undefined || requestId.length === 0) {
        yield* Effect.logWarning("[ConfigService] Received request without id, ignoring");
        return;
      }

      const sendResponse = Effect.fnUntraced(function* (response: ConfigResponse) {
        const responseProducer = (yield* SynchronizedRef.get(state)).responseProducer;
        if (responseProducer === null) {
          return yield* configServiceError("respond", "Config response producer not started");
        }
        yield* responseProducer.send(response, {id: requestId}).pipe(
          Effect.mapError((cause) => configServiceError("respond", cause)),
        );
      });

      yield* handleOperationEffect(request).pipe(
        Effect.flatMap(sendResponse),
        Effect.catch((err) =>
          sendResponse({
            error: {type: "config-error", message: err.message},
          })
        ),
      );
    });

  const loadFromDiskEffect = Effect.fn("loadFromDiskEffect")(function* () {
      if (persistPath === null) return;
      const parsed = yield* readPersistedConfigEffect(persistPath);
      if (parsed === null) return;

      const next = yield* SynchronizedRef.updateAndGet(state, (current) => ({
        ...current,
        version: parsed.version ?? 0,
        store: storeFromPersistedConfig(parsed),
      }));

      yield* Effect.log(`[ConfigService] Loaded persisted config (version=${next.version}, workspaces=${HashMap.size(next.store)})`);
    });

  const serviceStopEffect = closeConfigResourcesEffect(state).pipe(
    Effect.mapError((cause) => processorLifecycleError(config.id, "stop", cause)),
    Effect.flatMap(() => base.stop),
  );

  const serviceBase = Object.create(base, {
    stop: {
      value: serviceStopEffect,
      writable: true,
      enumerable: true,
      configurable: true,
    },
    stopEffect: {
      value: serviceStopEffect,
      writable: true,
      enumerable: true,
      configurable: true,
    },
  });

  service = Object.assign(serviceBase, {
    state,
    persistPath,
    handleMessageEffect,
    handleOperationEffect,
    handleGet: (request: ConfigRequest) => handleGetWithState(stateSnapshot(state), request),
    handlePutEffect: (request: ConfigRequest) => handlePutEffect(state, persistPath, request),
    handleDeleteEffect: (request: ConfigRequest) => handleDeleteEffect(state, persistPath, request),
    handleList: (request: ConfigRequest) => handleListWithState(stateSnapshot(state), request),
    handleGetValues: (request: ConfigRequest) => handleGetValuesWithState(stateSnapshot(state), request),
    handleGetValuesAllWorkspaces: (request: ConfigRequest) => handleGetValuesAllWorkspacesWithState(stateSnapshot(state), request),
    handleConfigDump: (request: ConfigRequest) => handleConfigDumpWithState(stateSnapshot(state), request),
    pushConfigEffect: SynchronizedRef.get(state).pipe(Effect.flatMap(pushConfigWithStateEffect)),
    persistEffect: SynchronizedRef.get(state).pipe(Effect.flatMap((current) => persistStateEffect(persistPath, current))),
    loadFromDiskEffect: loadFromDiskEffect(),
  }) as ConfigService;

  return service;
}

export const ConfigService = makeConfigService;

export const loadConfigServiceRuntimeConfig = Effect.fn("loadConfigServiceRuntimeConfig")(function* () {
  const processorConfig = yield* loadProcessorRuntimeConfig("config-svc", {
    manageProcessSignals: false,
  });
  const persistPath = yield* optionalStringConfig("CONFIG_PERSIST_PATH");
  return {
    ...processorConfig,
    ...(persistPath !== undefined ? {persistPath} : {}),
  } satisfies ConfigServiceConfig;
});

export const program = makeProcessorProgram({
  id: "config-svc",
  loadConfig: loadConfigServiceRuntimeConfig(),
  make: (config) => makeConfigService(config),
});

export function runMain(): void {
  NodeRuntime.runMain(program);
}
