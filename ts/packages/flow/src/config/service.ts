/**
 * Config service — manages system global configuration state.
 *
 * Python reference: trustgraph-flow/trustgraph/config/service/service.py
 */

import {NodeRuntime} from "@effect/platform-node";
import {Duration, Effect, Layer, ManagedRuntime, Match, SynchronizedRef} from "effect";
import * as Predicate from "effect/Predicate";
import * as S from "effect/Schema";
import {
  ConfigRequest as ConfigRequestSchema,
  ConfigResponse as ConfigResponseSchema,
  errorMessage,
  loadProcessorRuntimeConfig,
  makeAsyncProcessor,
  makeProcessorProgram,
  optionalStringConfig,
  topics,
  type AsyncProcessorRuntime,
  type BackendConsumer,
  type BackendProducer,
  type ConfigOperation,
  type ConfigRequest,
  type ConfigResponse,
  type Message,
  type ProcessorConfig,
} from "@trustgraph/base";
import {readTextFile, writeTextFile} from "../runtime/effect-files.js";

export interface ConfigServiceConfig extends ProcessorConfig {
  readonly persistPath?: string;
}

interface ConfigPush {
  readonly version: number;
  readonly config: Record<string, unknown>;
}

const ConfigPushSchema = S.Struct({
  version: S.Number,
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

type NamespaceStore = Map<string, unknown>;
type WorkspaceStore = Map<string, NamespaceStore>;
type WorkspaceSnapshot = Record<string, Record<string, Record<string, unknown>>>;

interface ConfigServiceState {
  readonly version: number;
  readonly store: Map<string, WorkspaceStore>;
  readonly consumer: BackendConsumer<ConfigRequest> | null;
  readonly responseProducer: BackendProducer<ConfigResponse> | null;
  readonly pushProducer: BackendProducer<ConfigPush> | null;
}

const PersistedConfigSchema = S.Struct({
  version: S.optionalKey(S.Number),
  data: S.optionalKey(S.Record(S.String, S.Record(S.String, S.Unknown))),
  workspaces: S.optionalKey(S.Record(S.String, S.Record(S.String, S.Record(S.String, S.Unknown)))),
});
const PersistedConfigJsonSchema = PersistedConfigSchema.pipe(S.fromJsonString);
type PersistedConfig = typeof PersistedConfigSchema.Type;

export interface ConfigService extends AsyncProcessorRuntime<ConfigServiceError> {
  readonly state: SynchronizedRef.SynchronizedRef<ConfigServiceState>;
  readonly persistPath: string | null;
  readonly handleMessage: (msg: Message<ConfigRequest>) => Promise<void>;
  readonly handleMessageEffect: (msg: Message<ConfigRequest>) => Effect.Effect<void, ConfigServiceError>;
  readonly handleOperation: (request: ConfigRequest) => Promise<ConfigResponse>;
  readonly handleOperationEffect: (request: ConfigRequest) => Effect.Effect<ConfigResponse, ConfigServiceError>;
  readonly handleGet: (request: ConfigRequest) => ConfigResponse;
  readonly handlePut: (request: ConfigRequest) => Promise<ConfigResponse>;
  readonly handlePutEffect: (request: ConfigRequest) => Effect.Effect<ConfigResponse, ConfigServiceError>;
  readonly handleDelete: (request: ConfigRequest) => Promise<ConfigResponse>;
  readonly handleDeleteEffect: (request: ConfigRequest) => Effect.Effect<ConfigResponse, ConfigServiceError>;
  readonly handleList: (request: ConfigRequest) => ConfigResponse;
  readonly handleGetValues: (request: ConfigRequest) => ConfigResponse;
  readonly handleGetValuesAllWorkspaces: (request: ConfigRequest) => ConfigResponse;
  readonly handleConfigDump: (request: ConfigRequest) => ConfigResponse;
  readonly pushConfig: () => Promise<void>;
  readonly pushConfigEffect: Effect.Effect<void, ConfigServiceError>;
  readonly persist: () => Promise<void>;
  readonly persistEffect: Effect.Effect<void>;
  readonly loadFromDisk: () => Promise<void>;
  readonly loadFromDiskEffect: Effect.Effect<void>;
}

const initialState = (): ConfigServiceState => ({
  version: 0,
  store: new Map<string, WorkspaceStore>(),
  consumer: null,
  responseProducer: null,
  pushProducer: null,
});

const cloneNamespaceStore = (source: NamespaceStore): NamespaceStore => {
  const next = new Map<string, unknown>();
  for (const [key, value] of source) {
    next.set(key, value);
  }
  return next;
};

const cloneWorkspaceStore = (source: WorkspaceStore): WorkspaceStore => {
  const next = new Map<string, NamespaceStore>();
  for (const [namespace, subMap] of source) {
    next.set(namespace, cloneNamespaceStore(subMap));
  }
  return next;
};

const cloneConfigStore = (source: Map<string, WorkspaceStore>): Map<string, WorkspaceStore> => {
  const next = new Map<string, WorkspaceStore>();
  for (const [workspace, ws] of source) {
    next.set(workspace, cloneWorkspaceStore(ws));
  }
  return next;
};

const toPersistedWorkspaces = (
  store: Map<string, WorkspaceStore>,
): WorkspaceSnapshot => {
  const workspaces: WorkspaceSnapshot = {};

  for (const [workspace, ws] of store) {
    const workspaceData: Record<string, Record<string, unknown>> = {};
    for (const [namespace, subMap] of ws) {
      const obj: Record<string, unknown> = {};
      for (const [key, value] of subMap) {
        obj[key] = value;
      }
      workspaceData[namespace] = obj;
    }
    workspaces[workspace] = workspaceData;
  }

  return workspaces;
};

const storeFromPersistedConfig = (parsed: PersistedConfig): Map<string, WorkspaceStore> => {
  const store = new Map<string, WorkspaceStore>();

  if (parsed.workspaces !== undefined) {
    for (const [workspace, namespaces] of Object.entries(parsed.workspaces)) {
      const ws = new Map<string, NamespaceStore>();
      for (const [namespace, obj] of Object.entries(namespaces)) {
        const subMap = new Map<string, unknown>();
        for (const [key, value] of Object.entries(obj)) {
          subMap.set(key, value);
        }
        ws.set(namespace, subMap);
      }
      store.set(workspace, ws);
    }
    return store;
  }

  const ws = new Map<string, NamespaceStore>();
  for (const [namespace, obj] of Object.entries(parsed.data ?? {})) {
    const subMap = new Map<string, unknown>();
    for (const [key, value] of Object.entries(obj)) {
      subMap.set(key, value);
    }
    ws.set(namespace, subMap);
  }
  store.set(DEFAULT_WORKSPACE, ws);
  return store;
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
  state.store.get(workspace);

const getNamespaceStore = (
  state: ConfigServiceState,
  workspace: string,
  namespace: string,
): NamespaceStore | undefined =>
  getWorkspaceStore(state, workspace)?.get(namespace);

const getOrCreateWorkspaceStore = (
  store: Map<string, WorkspaceStore>,
  workspace: string,
): WorkspaceStore => {
  const existing = store.get(workspace);
  if (existing !== undefined) return existing;
  const created = new Map<string, NamespaceStore>();
  store.set(workspace, created);
  return created;
};

const getOrCreateNamespaceStore = (
  store: Map<string, WorkspaceStore>,
  workspace: string,
  namespace: string,
): NamespaceStore => {
  const ws = getOrCreateWorkspaceStore(store, workspace);
  const existing = ws.get(namespace);
  if (existing !== undefined) return existing;
  const created = new Map<string, unknown>();
  ws.set(namespace, created);
  return created;
};

const configDumpForState = (
  state: ConfigServiceState,
  workspace: string = DEFAULT_WORKSPACE,
): Record<string, unknown> => {
  const config: Record<string, unknown> = {};
  const ws = getWorkspaceStore(state, workspace);

  if (ws === undefined) return config;

  for (const [namespace, subMap] of ws) {
    const obj: Record<string, unknown> = {};
    for (const [key, value] of subMap) {
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

const persistStateEffect = (
  persistPath: string | null,
  state: ConfigServiceState,
): Effect.Effect<void> =>
  Effect.gen(function* () {
    if (persistPath === null) return;
    const payload = {
      version: state.version,
      workspaces: toPersistedWorkspaces(state.store),
    };

    const json = yield* S.encodeUnknownEffect(S.UnknownFromJsonString)(payload).pipe(
      Effect.mapError((cause) => configServiceError("persist-encode", cause)),
    );

    yield* Effect.tryPromise({
      try: () => writeTextFile(persistPath, json),
      catch: (cause) => configServiceError("persist-write", cause),
    });
  }).pipe(
    Effect.catch((err) =>
      Effect.logError("[ConfigService] Failed to persist config", {error: err.message}),
    ),
  );

const pushConfigWithStateEffect = (
  state: ConfigServiceState,
): Effect.Effect<void, ConfigServiceError> =>
  Effect.gen(function* () {
    const pushProducer = state.pushProducer;
    if (pushProducer === null) return;

    yield* Effect.tryPromise({
      try: () =>
        pushProducer.send({
          version: state.version,
          config: configDumpForState(state),
        }),
      catch: (cause) => configServiceError("push-config", cause),
    });

    yield* Effect.log(`[ConfigService] Pushed configuration version ${state.version}`);
  });

const readPersistedConfigEffect = (
  persistPath: string,
): Effect.Effect<PersistedConfig | null> =>
  Effect.gen(function* () {
    const raw = yield* Effect.tryPromise({
      try: () => readTextFile(persistPath),
      catch: (cause) => configServiceError("persist-read", cause),
    });
    return yield* S.decodeUnknownEffect(PersistedConfigJsonSchema)(raw).pipe(
      Effect.mapError((cause) => configServiceError("persist-decode", cause)),
    );
  }).pipe(
    Effect.catch(() =>
      Effect.log("[ConfigService] No persisted config found, starting fresh").pipe(
        Effect.flatMap(() => Effect.succeed<PersistedConfig | null>(null)),
      )
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
        ? getNamespaceStore(state, workspace, key.type)?.get(key.key)
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
      for (const [key, value] of subMap) {
        values[key] = value;
      }
    } else {
      for (const key of keys.slice(1)) {
        if (subMap.has(key)) {
          values[key] = subMap.get(key);
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
  const store = cloneConfigStore(state.store);

  for (const item of values) {
    getOrCreateNamespaceStore(store, item.workspace ?? DEFAULT_WORKSPACE, item.type)
      .set(item.key, item.value);
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
  const store = cloneConfigStore(state.store);
  const ws = store.get(workspace);

  if (ws !== undefined) {
    for (const key of keys) {
      if (key.key === undefined) {
        ws.delete(key.type);
      } else {
        const ns = ws.get(key.type);
        ns?.delete(key.key);
        if (ns !== undefined && ns.size === 0) {
          ws.delete(key.type);
        }
      }
    }
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
  const store = cloneConfigStore(state.store);
  const namespace = keys[0];
  const ws = store.get(workspace);

  if (ws === undefined) return state;

  if (keys.length === 1) {
    ws.delete(namespace);
  } else {
    const subMap = ws.get(namespace);
    if (subMap !== undefined) {
      for (const key of keys.slice(1)) {
        subMap.delete(key);
      }
      if (subMap.size === 0) {
        ws.delete(namespace);
      }
    }
  }

  return {
    ...state,
    store,
    version: state.version + 1,
  };
};

const handlePutEffect = (
  stateRef: SynchronizedRef.SynchronizedRef<ConfigServiceState>,
  persistPath: string | null,
  request: ConfigRequest,
): Effect.Effect<ConfigResponse, ConfigServiceError> =>
  Effect.gen(function* () {
    const values = configValues(request);
    if (values.length === 0) return yield* configServiceError("put", "Put requires config values");

    const next = yield* SynchronizedRef.updateAndGet(stateRef, (state) => applyPut(state, values));
    yield* persistStateEffect(persistPath, next);
    yield* pushConfigWithStateEffect(next);

    return {version: next.version};
  });

const handleDeleteEffect = (
  stateRef: SynchronizedRef.SynchronizedRef<ConfigServiceState>,
  persistPath: string | null,
  request: ConfigRequest,
): Effect.Effect<ConfigResponse, ConfigServiceError> =>
  Effect.gen(function* () {
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
      directory: ws !== undefined ? [...ws.keys()] : [],
    };
  }

  const subMap = ws?.get(namespace);
  return {
    version: state.version,
    directory: subMap !== undefined ? [...subMap.keys()] : [],
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
    for (const [namespace, subMap] of ws) {
      if (type.length > 0 && namespace !== type) continue;
      for (const [key, value] of subMap) {
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

  for (const [workspace, ws] of state.store) {
    for (const [namespace, subMap] of ws) {
      if (type.length > 0 && namespace !== type) continue;
      for (const [key, value] of subMap) {
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

const closeConfigResourcesEffect = (
  stateRef: SynchronizedRef.SynchronizedRef<ConfigServiceState>,
): Effect.Effect<void, ConfigServiceError> =>
  Effect.gen(function* () {
    const state = yield* SynchronizedRef.get(stateRef);

    const consumer = state.consumer;
    if (consumer !== null) {
      yield* Effect.tryPromise({
        try: () => consumer.close(),
        catch: (cause) => configServiceError("close-consumer", cause),
      });
    }
    const responseProducer = state.responseProducer;
    if (responseProducer !== null) {
      yield* Effect.tryPromise({
        try: () => responseProducer.close(),
        catch: (cause) => configServiceError("close-response-producer", cause),
      });
    }
    const pushProducer = state.pushProducer;
    if (pushProducer !== null) {
      yield* Effect.tryPromise({
        try: () => pushProducer.close(),
        catch: (cause) => configServiceError("close-push-producer", cause),
      });
    }

    yield* updateHandles(stateRef, {
      consumer: null,
      responseProducer: null,
      pushProducer: null,
    });
  });

const consumeOnceEffect = (
  service: ConfigService,
): Effect.Effect<void, ConfigServiceError> =>
  Effect.gen(function* () {
    const state = yield* SynchronizedRef.get(service.state);
    const consumer = state.consumer;
    if (consumer === null) {
      return yield* configServiceError("consume", "Config consumer not started");
    }

    const msg = yield* Effect.tryPromise({
      try: () => consumer.receive(2000),
      catch: (cause) => configServiceError("consume-receive", cause),
    });
    if (msg === null) return;

    yield* service.handleMessageEffect(msg);
    yield* Effect.tryPromise({
      try: () => consumer.acknowledge(msg),
      catch: (cause) => configServiceError("consume-acknowledge", cause),
    });
  });

const runConfigServiceEffect = (
  service: ConfigService,
): Effect.Effect<void, ConfigServiceError> =>
  Effect.gen(function* () {
    yield* service.loadFromDiskEffect;

    const responseProducer = yield* Effect.tryPromise({
      try: () =>
        service.pubsub.createProducer<ConfigResponse>({
          topic: topics.configResponse,
          schema: ConfigResponseSchema,
        }),
      catch: (cause) => configServiceError("response-producer", cause),
    });
    yield* updateHandles(service.state, {responseProducer});

    const pushProducer = yield* Effect.tryPromise({
      try: () =>
        service.pubsub.createProducer<ConfigPush>({
          topic: topics.configPush,
          schema: ConfigPushSchema,
        }),
      catch: (cause) => configServiceError("push-producer", cause),
    });
    yield* updateHandles(service.state, {pushProducer});

    const consumer = yield* Effect.tryPromise({
      try: () =>
        service.pubsub.createConsumer<ConfigRequest>({
          topic: topics.configRequest,
          subscription: `${service.config.id}-config-request`,
          schema: ConfigRequestSchema,
        }),
      catch: (cause) => configServiceError("consumer", cause),
    });
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
  const baseStop = base.stop;
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
        yield* Effect.tryPromise({
          try: () => responseProducer.send(response, {id: requestId}),
          catch: (cause) => configServiceError("respond", cause),
        });
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

      yield* Effect.log(`[ConfigService] Loaded persisted config (version=${next.version}, workspaces=${next.store.size})`);
    });

  service = Object.assign(base, {
    state,
    persistPath,
    handleMessage: (msg: Message<ConfigRequest>) => Effect.runPromise(handleMessageEffect(msg)),
    handleMessageEffect,
    handleOperation: (request: ConfigRequest) => Effect.runPromise(handleOperationEffect(request)),
    handleOperationEffect,
    handleGet: (request: ConfigRequest) => handleGetWithState(stateSnapshot(state), request),
    handlePut: (request: ConfigRequest) => Effect.runPromise(handlePutEffect(state, persistPath, request)),
    handlePutEffect: (request: ConfigRequest) => handlePutEffect(state, persistPath, request),
    handleDelete: (request: ConfigRequest) => Effect.runPromise(handleDeleteEffect(state, persistPath, request)),
    handleDeleteEffect: (request: ConfigRequest) => handleDeleteEffect(state, persistPath, request),
    handleList: (request: ConfigRequest) => handleListWithState(stateSnapshot(state), request),
    handleGetValues: (request: ConfigRequest) => handleGetValuesWithState(stateSnapshot(state), request),
    handleGetValuesAllWorkspaces: (request: ConfigRequest) => handleGetValuesAllWorkspacesWithState(stateSnapshot(state), request),
    handleConfigDump: (request: ConfigRequest) => handleConfigDumpWithState(stateSnapshot(state), request),
    pushConfig: () => Effect.runPromise(SynchronizedRef.get(state).pipe(Effect.flatMap(pushConfigWithStateEffect))),
    pushConfigEffect: SynchronizedRef.get(state).pipe(Effect.flatMap(pushConfigWithStateEffect)),
    persist: () => Effect.runPromise(SynchronizedRef.get(state).pipe(Effect.flatMap((current) => persistStateEffect(persistPath, current)))),
    persistEffect: SynchronizedRef.get(state).pipe(Effect.flatMap((current) => persistStateEffect(persistPath, current))),
    loadFromDisk: () => Effect.runPromise(loadFromDiskEffect()),
    loadFromDiskEffect: loadFromDiskEffect(),
    stop: () =>
      Effect.runPromise(
        closeConfigResourcesEffect(state).pipe(
          Effect.flatMap(() =>
            Effect.tryPromise({
              try: () => baseStop(),
              catch: (cause) => configServiceError("stop", cause),
            })
          ),
        ),
      ),
  });

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

const configServiceRuntime = ManagedRuntime.make(Layer.empty);

export function run(): Promise<void> {
  return configServiceRuntime.runPromise(program);
}

export function runMain(): void {
  NodeRuntime.runMain(program);
}
