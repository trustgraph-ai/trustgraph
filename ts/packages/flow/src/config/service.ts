/**
 * Config service — manages system global configuration state.
 *
 * An AsyncProcessor (NOT FlowProcessor) that:
 * 1. Listens on config-request topic
 * 2. Handles operations: get, put, delete, list, config (full dump)
 * 3. Stores config in-memory with a nested Map structure
 * 4. On any mutation: increments version, broadcasts ConfigPush on config-push topic
 * 5. Optionally persists to a JSON file for restart durability
 *
 * Python reference: trustgraph-flow/trustgraph/config/service/service.py
 */

import { Context, Duration, Effect } from "effect";
import * as S from "effect/Schema";
import {
  makeAsyncProcessor,
  type ProcessorConfig,
  type AsyncProcessorRuntime,
  topics,
  ConfigRequest as ConfigRequestSchema,
  ConfigResponse as ConfigResponseSchema,
  type ConfigRequest,
  type ConfigResponse,
  type ConfigOperation,
  errorMessage,
  loadProcessorRuntimeConfig,
  makeProcessorProgram,
  optionalStringConfig,
} from "@trustgraph/base";
import type { Message } from "@trustgraph/base";
import { readTextFile, writeTextFile } from "../runtime/effect-files.js";

export interface ConfigServiceConfig extends ProcessorConfig {
  persistPath?: string;
}

interface ConfigPush {
  version: number;
  config: Record<string, unknown>;
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
  type: string;
  key?: string;
}

interface ConfigValueLike {
  workspace?: string;
  type: string;
  key: string;
  value: unknown;
}

type NamespaceStore = Map<string, unknown>;
type WorkspaceStore = Map<string, NamespaceStore>;

const PersistedConfigSchema = S.Struct({
  version: S.optionalKey(S.Number),
  data: S.optionalKey(S.Record(S.String, S.Record(S.String, S.Unknown))),
  workspaces: S.optionalKey(S.Record(S.String, S.Record(S.String, S.Record(S.String, S.Unknown)))),
});
const PersistedConfigJsonSchema = PersistedConfigSchema.pipe(S.fromJsonString);
type PersistedConfig = typeof PersistedConfigSchema.Type;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function optionalString(value: unknown): string | undefined {
  return typeof value === "string" && value.length > 0 ? value : undefined;
}

function toPersistedWorkspaces(
  store: Map<string, WorkspaceStore>,
): Record<string, Record<string, Record<string, unknown>>> {
  const workspaces: Record<string, Record<string, Record<string, unknown>>> = {};

  for (const [workspace, ws] of store) {
    const workspaceData: Record<string, Record<string, unknown>> = {};
    for (const [namespace, subMap] of ws) {
      const obj: Record<string, unknown> = {};
      for (const [k, v] of subMap) {
        obj[k] = v;
      }
      workspaceData[namespace] = obj;
    }
    workspaces[workspace] = workspaceData;
  }

  return workspaces;
}

function hydratePersistedConfig(
  store: Map<string, WorkspaceStore>,
  parsed: PersistedConfig,
): void {
  store.clear();

  if (parsed.workspaces !== undefined) {
    for (const [workspace, namespaces] of Object.entries(parsed.workspaces)) {
      const ws = new Map<string, NamespaceStore>();
      for (const [namespace, obj] of Object.entries(namespaces)) {
        const subMap = new Map<string, unknown>();
        for (const [k, v] of Object.entries(obj)) {
          subMap.set(k, v);
        }
        ws.set(namespace, subMap);
      }
      store.set(workspace, ws);
    }
    return;
  }

  const ws = new Map<string, NamespaceStore>();
  for (const [namespace, obj] of Object.entries(parsed.data ?? {})) {
    const subMap = new Map<string, unknown>();
    for (const [k, v] of Object.entries(obj)) {
      subMap.set(k, v);
    }
    ws.set(namespace, subMap);
  }
  store.set(DEFAULT_WORKSPACE, ws);
}

export type ConfigService = AsyncProcessorRuntime & Record<string, any>;

export function makeConfigService(config: ConfigServiceConfig): ConfigService {
  const service = makeAsyncProcessor(config, {
    run: () => service.run(Context.empty()),
  }) as ConfigService;
  const baseStop = service.stop;
  service.store = new Map<string, WorkspaceStore>();
  service.version = 0;
  service.consumer = null;
  service.responseProducer = null;
  service.pushProducer = null;
  service.persistPath = config.persistPath ?? null;
  Object.assign(service, {


      run: function(this: ConfigService): Promise<void> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            // Optionally load persisted state
            if (service.persistPath !== null) {
              yield* Effect.tryPromise({
                try: () => service.loadFromDisk(),
                catch: (cause) => configServiceError("load", cause),
              });
            }

            // Create producers
            service.responseProducer = yield* Effect.tryPromise({
              try: () =>
                service.pubsub.createProducer<ConfigResponse>({
                  topic: topics.configResponse,
                  schema: ConfigResponseSchema,
                }),
              catch: (cause) => configServiceError("response-producer", cause),
            });
            service.pushProducer = yield* Effect.tryPromise({
              try: () =>
                service.pubsub.createProducer<ConfigPush>({
                  topic: topics.configPush,
                  schema: ConfigPushSchema,
                }),
              catch: (cause) => configServiceError("push-producer", cause),
            });

            // Create consumer for config requests
            service.consumer = yield* Effect.tryPromise({
              try: () =>
                service.pubsub.createConsumer<ConfigRequest>({
                  topic: topics.configRequest,
                  subscription: `${service.config.id}-config-request`,
                  schema: ConfigRequestSchema,
                }),
              catch: (cause) => configServiceError("consumer", cause),
            });

            // Push initial config
            yield* Effect.tryPromise({
              try: () => service.pushConfig(),
              catch: (cause) => configServiceError("push-initial-config", cause),
            });

            yield* Effect.log(`[ConfigService] Listening on ${topics.configRequest}`);

            // Main consume loop
            while (service.running) {
              const shouldContinue = yield* Effect.gen(function* () {
              const consumer = service.consumer;
              if (consumer === null) {
                return yield* configServiceError("consume", "Config consumer not started");
              }

              const msg = yield* Effect.tryPromise({
                try: () => consumer.receive(2000),
                catch: (cause) => configServiceError("consume-receive", cause),
              });
              if (msg === null) return true;

              yield* Effect.tryPromise({
                try: () => service.handleMessage(msg),
                catch: (cause) => configServiceError("consume-handle", cause),
              });
              yield* Effect.tryPromise({
                try: () => consumer.acknowledge(msg),
                catch: (cause) => configServiceError("consume-acknowledge", cause),
              });

              return true;
            }).pipe(
              Effect.catch((err) => {
                if (!service.running) return Effect.succeed(false);
                return Effect.logError("[ConfigService] Error in consume loop", { error: err.message }).pipe(
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



      handleMessage: function(this: ConfigService, msg: Message<ConfigRequest>): Promise<void> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const request = yield* S.decodeUnknownEffect(ConfigRequestSchema)(msg.value()).pipe(
              Effect.mapError((cause) => configServiceError("decode", cause)),
            );
            const props = msg.properties();
            const requestId = props.id;

            if (requestId === undefined || requestId.length === 0) {
              yield* Effect.logWarning("[ConfigService] Received request without id, ignoring");
              return;
            }

            const sendResponse = (response: ConfigResponse): Effect.Effect<void, ConfigServiceError> =>
              Effect.gen(function* () {
                const responseProducer = service.responseProducer;
                if (responseProducer === null) {
                  return yield* configServiceError("respond", "Config response producer not started");
                }
                yield* Effect.tryPromise({
                  try: () => responseProducer.send(response, { id: requestId }),
                  catch: (cause) => configServiceError("respond", cause),
                });
              });

            yield* Effect.gen(function* () {
              const response = yield* Effect.tryPromise<ConfigResponse, ConfigServiceError>({
                try: () => service.handleOperation(request),
                catch: (cause) => configServiceError("operation", cause),
              });
              yield* sendResponse(response);
            }).pipe(
              Effect.catch((err) =>
                sendResponse({
                  error: { type: "config-error", message: err.message },
                }),
              ),
            );
          }),
        );

        },



      handleOperation: function(this: ConfigService, request: ConfigRequest): Promise<ConfigResponse> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const op: ConfigOperation = request.operation;

            switch (op) {
              case "get":
                return service.handleGet(request);

              case "put":
                return yield* Effect.tryPromise<ConfigResponse, ConfigServiceError>({
                  try: () => service.handlePut(request),
                  catch: (cause) => configServiceError("put", cause),
                });

              case "delete":
                return yield* Effect.tryPromise<ConfigResponse, ConfigServiceError>({
                  try: () => service.handleDelete(request),
                  catch: (cause) => configServiceError("delete", cause),
                });

              case "list":
                return service.handleList(request);

              case "config":
                return service.handleConfigDump(request);

              case "getvalues":
                return service.handleGetValues(request);

              case "getvalues-all-ws":
                return service.handleGetValuesAllWorkspaces(request);

              default:
                return yield* configServiceError("operation", `Unknown config operation: ${op as string}`);
            }
          }),
        );

        },



      requestRecord: function(this: ConfigService, request: ConfigRequest): Record<string, unknown> {
        return request as Record<string, unknown>;

        },



      workspaceFor: function(this: ConfigService, request: ConfigRequest): string {
        return optionalString(this.requestRecord(request).workspace) ?? DEFAULT_WORKSPACE;

        },



      workspaceStore: function(this: ConfigService, workspace: string, create: boolean): WorkspaceStore | undefined {
        let store = this.store.get(workspace);
        if (store === undefined && create) {
          store = new Map<string, NamespaceStore>();
          this.store.set(workspace, store);
        }
        return store;

        },



      namespaceStore: function(this: ConfigService, workspace: string, namespace: string, create: boolean): NamespaceStore | undefined {
        const ws = this.workspaceStore(workspace, create);
        if (ws === undefined) return undefined;

        let ns = ws.get(namespace);
        if (ns === undefined && create) {
          ns = new Map<string, unknown>();
          ws.set(namespace, ns);
        }
        return ns;

        },



      rawKeys: function(this: ConfigService, request: ConfigRequest): unknown[] {
        const keys = this.requestRecord(request).keys;
        return Array.isArray(keys) ? keys : [];

        },



      stringKeys: function(this: ConfigService, request: ConfigRequest): string[] {
        return (this.rawKeys(request) as unknown[]).filter((key: unknown): key is string => typeof key === "string");

        },



      objectKeys: function(this: ConfigService, request: ConfigRequest): ConfigKeyLike[] {
        return (this.rawKeys(request) as unknown[]).flatMap((key: unknown) => {
          if (!isRecord(key)) return [];
          const type = optionalString(key.type);
          if (type === undefined) return [];
          const item: ConfigKeyLike = { type };
          const keyValue = optionalString(key.key);
          if (keyValue !== undefined) item.key = keyValue;
          return [item];
        });

        },



      requestType: function(this: ConfigService, request: ConfigRequest): string | undefined {
        return optionalString(this.requestRecord(request).type) ?? this.stringKeys(request)[0];

        },



      configValues: function(this: ConfigService, request: ConfigRequest): ConfigValueLike[] {
        const req = this.requestRecord(request);
        const rawValues = req.values;
        const workspace = this.workspaceFor(request);

        if (Array.isArray(rawValues)) {
          return rawValues.flatMap((value) => {
            if (!isRecord(value)) return [];
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

        if (isRecord(rawValues)) {
          const namespace = this.requestType(request);
          if (namespace === undefined) return [];
          return Object.entries(rawValues).map(([key, value]) => ({
            workspace,
            type: namespace,
            key,
            value,
          }));
        }

        return [];

        },



      handleGet: function(this: ConfigService, request: ConfigRequest): ConfigResponse {
        const workspace = this.workspaceFor(request);
        const objectKeys = this.objectKeys(request) as ConfigKeyLike[];

        if (objectKeys.length > 0) {
          const values = objectKeys.map((key) => ({
            type: key.type,
            key: key.key ?? "",
            value: key.key !== undefined
              ? this.namespaceStore(workspace, key.type, false)?.get(key.key)
              : undefined,
          }));
          return { version: this.version, values };
        }

        const keys = this.stringKeys(request) as string[];
        if (keys.length === 0) {
          return { version: this.version, values: {} };
        }

        const values: Record<string, unknown> = {};
        const namespace = keys[0];
        const subMap = this.namespaceStore(workspace, namespace, false) as NamespaceStore | undefined;

        if (subMap !== undefined) {
          if (keys.length === 1) {
            // Return entire namespace
            for (const [k, v] of subMap) {
              values[k] = v;
            }
          } else {
            // Return specific keys within namespace
            for (let i = 1; i < keys.length; i++) {
              const key = keys[i];
              if (key !== undefined && subMap.has(key)) {
                values[key] = subMap.get(key);
              }
            }
          }
        }

        return { version: this.version, values };

        },



      handlePut: function(this: ConfigService, request: ConfigRequest): Promise<ConfigResponse> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const values = service.configValues(request);
            if (values.length === 0) return yield* configServiceError("put", "Put requires config values");

            for (const item of values) {
              service.namespaceStore(item.workspace ?? DEFAULT_WORKSPACE, item.type, true)?.set(item.key, item.value);
            }

            service.version++;
            yield* Effect.tryPromise({
              try: () => service.persist(),
              catch: (cause) => configServiceError("persist", cause),
            });
            yield* Effect.tryPromise({
              try: () => service.pushConfig(),
              catch: (cause) => configServiceError("push-config", cause),
            });

            return { version: service.version };
          }),
        );

        },



      handleDelete: function(this: ConfigService, request: ConfigRequest): Promise<ConfigResponse> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const workspace = service.workspaceFor(request);
            const objectKeys = service.objectKeys(request);
            if (objectKeys.length > 0) {
              for (const key of objectKeys) {
                const ws = service.workspaceStore(workspace, false);
                if (ws === undefined) continue;
                if (key.key === undefined) {
                  ws.delete(key.type);
                } else {
                  const ns = ws.get(key.type);
                  ns?.delete(key.key);
                  if (ns !== undefined && ns.size === 0) ws.delete(key.type);
                }
              }

              service.version++;
              yield* Effect.tryPromise({
                try: () => service.persist(),
                catch: (cause) => configServiceError("persist", cause),
              });
              yield* Effect.tryPromise({
                try: () => service.pushConfig(),
                catch: (cause) => configServiceError("push-config", cause),
              });
              return { version: service.version };
            }

            const keys = service.stringKeys(request);
            if (keys.length === 0) {
              return yield* configServiceError("delete", "Delete requires at least one key");
            }

            const namespace = keys[0];
            const ws = service.workspaceStore(workspace, false);
            if (ws === undefined) return { version: service.version };

            if (keys.length === 1) {
              // Delete entire namespace
              ws.delete(namespace);
            } else {
              // Delete specific keys within namespace
              const subMap = ws.get(namespace);
              if (subMap !== undefined) {
                for (let i = 1; i < keys.length; i++) {
                  subMap.delete(keys[i]);
                }
                if (subMap.size === 0) {
                  ws.delete(namespace);
                }
              }
            }

            service.version++;
            yield* Effect.tryPromise({
              try: () => service.persist(),
              catch: (cause) => configServiceError("persist", cause),
            });
            yield* Effect.tryPromise({
              try: () => service.pushConfig(),
              catch: (cause) => configServiceError("push-config", cause),
            });

            return { version: service.version };
          }),
        );

        },



      handleList: function(this: ConfigService, request: ConfigRequest): ConfigResponse {
        const workspace = this.workspaceFor(request);
        const ws = this.workspaceStore(workspace, false);
        const namespace = this.requestType(request);

        if (namespace === undefined) {
          // List all namespaces
          return {
            version: this.version,
            directory: ws !== undefined ? [...ws.keys()] : [],
          };
        }

        const subMap = ws?.get(namespace);

        return {
          version: this.version,
          directory: subMap !== undefined ? [...subMap.keys()] : [],
        };

        },



      handleGetValues: function(this: ConfigService, request: ConfigRequest): ConfigResponse {
        const workspace = this.workspaceFor(request);
        const type = this.requestType(request) ?? "";
        const ws = this.workspaceStore(workspace, false);

        const values: { type: string; key: string; value: unknown }[] = [];

        for (const [namespace, subMap] of ws ?? new Map<string, NamespaceStore>()) {
          if (
            type.length === 0 ||
            namespace === type
          ) {
            for (const [k, v] of subMap) {
              values.push({ type: namespace, key: k, value: v });
            }
          }
        }

        return { version: this.version, values };

        },



      handleGetValuesAllWorkspaces: function(this: ConfigService, request: ConfigRequest): ConfigResponse {
        const type = this.requestType(request) ?? "";
        const values: { workspace: string; type: string; key: string; value: unknown }[] = [];

        for (const [workspace, ws] of this.store) {
          for (const [namespace, subMap] of ws) {
            if (type.length > 0 && namespace !== type) continue;
            for (const [key, value] of subMap) {
              values.push({ workspace, type: namespace, key, value });
            }
          }
        }

        return { version: this.version, values };

        },



      handleConfigDump: function(this: ConfigService, request: ConfigRequest): ConfigResponse {
        const workspace = this.workspaceFor(request);
        const ws = this.workspaceStore(workspace, false);
        const config: Record<string, unknown> = {};

        for (const [namespace, subMap] of ws ?? new Map<string, NamespaceStore>()) {
          const obj: Record<string, unknown> = {};
          for (const [k, v] of subMap) {
            obj[k] = v;
          }
          config[namespace] = obj;
        }

        return {
          version: this.version,
          config,
        };

        },



      pushConfig: function(this: ConfigService): Promise<void> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const pushProducer = service.pushProducer;
            if (pushProducer === null) return;

            const config: Record<string, unknown> = {};
            const ws = service.workspaceStore(DEFAULT_WORKSPACE, false);
            for (const [namespace, subMap] of ws ?? new Map<string, NamespaceStore>()) {
              const obj: Record<string, unknown> = {};
              for (const [k, v] of subMap) {
                obj[k] = v;
              }
              config[namespace] = obj;
            }

            yield* Effect.tryPromise({
              try: () =>
                pushProducer.send({
                  version: service.version,
                  config,
                }),
              catch: (cause) => configServiceError("push-config", cause),
            });

            yield* Effect.log(`[ConfigService] Pushed configuration version ${service.version}`);
          }),
        );

        },



      persist: function(this: ConfigService): Promise<void> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const persistPath = service.persistPath;
            if (persistPath === null) return;
            const payload = {
              version: service.version,
              workspaces: toPersistedWorkspaces(service.store),
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
              Effect.logError("[ConfigService] Failed to persist config", { error: err.message }),
            ),
          ),
        );

        },



      loadFromDisk: function(this: ConfigService): Promise<void> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const persistPath = service.persistPath;
            if (persistPath === null) return;

            const parsed = yield* Effect.gen(function* () {
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
                  Effect.as(null as PersistedConfig | null),
                ),
              ),
            );

            if (parsed === null) return;

            service.version = parsed.version ?? 0;
            hydratePersistedConfig(service.store, parsed);

            yield* Effect.log(`[ConfigService] Loaded persisted config (version=${service.version}, workspaces=${service.store.size})`);
          }),
        );

        },



      stop: function(this: ConfigService): Promise<void> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const consumer = service.consumer;
            if (consumer !== null) {
              yield* Effect.tryPromise({
                try: () => consumer.close(),
                catch: (cause) => configServiceError("close-consumer", cause),
              });
              service.consumer = null;
            }
            const responseProducer = service.responseProducer;
            if (responseProducer !== null) {
              yield* Effect.tryPromise({
                try: () => responseProducer.close(),
                catch: (cause) => configServiceError("close-response-producer", cause),
              });
              service.responseProducer = null;
            }
            const pushProducer = service.pushProducer;
            if (pushProducer !== null) {
              yield* Effect.tryPromise({
                try: () => pushProducer.close(),
                catch: (cause) => configServiceError("close-push-producer", cause),
              });
              service.pushProducer = null;
            }
            yield* Effect.tryPromise({
              try: () => baseStop(),
              catch: (cause) => configServiceError("stop", cause),
            });
          }),
        );

        }
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
    ...(persistPath !== undefined ? { persistPath } : {}),
  } satisfies ConfigServiceConfig;
});

export const program = makeProcessorProgram({
  id: "config-svc",
  loadConfig: loadConfigServiceRuntimeConfig(),
  make: (config) => makeConfigService(config),
});

export function run(): Promise<void> {
  return Effect.runPromise(program);
}
