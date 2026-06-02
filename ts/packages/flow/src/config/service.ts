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

import { Effect } from "effect";
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

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function optionalString(value: unknown): string | undefined {
  return typeof value === "string" && value.length > 0 ? value : undefined;
}

export type ConfigService = AsyncProcessorRuntime & Record<string, any>;

export function makeConfigService(config: ConfigServiceConfig): ConfigService {
  const service = makeAsyncProcessor(config, {
    run: async () => {
      await service.run();
    },
  }) as ConfigService;
  const baseStop = service.stop;
  service.store = new Map<string, WorkspaceStore>();
  service.version = 0;
  service.consumer = null;
  service.responseProducer = null;
  service.pushProducer = null;
  service.persistPath = config.persistPath ?? null;
  Object.assign(service, {


      run: async function(this: ConfigService): Promise<void> {
        // Optionally load persisted state
        if (this.persistPath !== null) {
          await this.loadFromDisk();
        }

        // Create producers
        this.responseProducer = await this.pubsub.createProducer<ConfigResponse>({
          topic: topics.configResponse,
          schema: ConfigResponseSchema,
        });
        this.pushProducer = await this.pubsub.createProducer<ConfigPush>({
          topic: topics.configPush,
          schema: ConfigPushSchema,
        });

        // Create consumer for config requests
        this.consumer = await this.pubsub.createConsumer<ConfigRequest>({
          topic: topics.configRequest,
          subscription: `${this.config.id}-config-request`,
          schema: ConfigRequestSchema,
        });

        // Push initial config
        await this.pushConfig();

        console.log(`[ConfigService] Listening on ${topics.configRequest}`);

        // Main consume loop
        while (this.running) {
          try {
            const consumer = this.consumer;
            if (consumer === null) throw new Error("Config consumer not started");

            const msg = await consumer.receive(2000);
            if (msg === null) continue;

            await this.handleMessage(msg);
            await consumer.acknowledge(msg);
          } catch (err) {
            if (!this.running) break;
            console.error("[ConfigService] Error in consume loop:", err);
            await sleep(1000);
          }
        }

        },



      handleMessage: async function(this: ConfigService, msg: Message<ConfigRequest>): Promise<void> {
        const request = await Effect.runPromise(S.decodeUnknownEffect(ConfigRequestSchema)(msg.value()));
        const props = msg.properties();
        const requestId = props.id;

        if (requestId === undefined || requestId.length === 0) {
          console.warn("[ConfigService] Received request without id, ignoring");
          return;
        }

        try {
          const response = await this.handleOperation(request);
          const responseProducer = this.responseProducer;
          if (responseProducer === null) throw new Error("Config response producer not started");
          await responseProducer.send(response, { id: requestId });
        } catch (err) {
          const message = errorMessage(err);
          const responseProducer = this.responseProducer;
          if (responseProducer === null) throw new Error("Config response producer not started");
          await responseProducer.send(
            {
              error: { type: "config-error", message },
            },
            { id: requestId },
          );
        }

        },



      handleOperation: async function(this: ConfigService, request: ConfigRequest): Promise<ConfigResponse> {
        const op: ConfigOperation = request.operation;

        switch (op) {
          case "get":
            return this.handleGet(request);

          case "put":
            return await this.handlePut(request);

          case "delete":
            return await this.handleDelete(request);

          case "list":
            return this.handleList(request);

          case "config":
            return this.handleConfigDump(request);

          case "getvalues":
            return this.handleGetValues(request);

          case "getvalues-all-ws":
            return this.handleGetValuesAllWorkspaces(request);

          default:
            throw new Error(`Unknown config operation: ${op as string}`);
        }

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



      handlePut: async function(this: ConfigService, request: ConfigRequest): Promise<ConfigResponse> {
        const values = this.configValues(request);
        if (values.length === 0) throw new Error("Put requires config values");

        for (const item of values) {
          this.namespaceStore(item.workspace ?? DEFAULT_WORKSPACE, item.type, true)?.set(item.key, item.value);
        }

        this.version++;
        await this.persist();
        await this.pushConfig();

        return { version: this.version };

        },



      handleDelete: async function(this: ConfigService, request: ConfigRequest): Promise<ConfigResponse> {
        const workspace = this.workspaceFor(request);
        const objectKeys = this.objectKeys(request);
        if (objectKeys.length > 0) {
          for (const key of objectKeys) {
            const ws = this.workspaceStore(workspace, false);
            if (ws === undefined) continue;
            if (key.key === undefined) {
              ws.delete(key.type);
            } else {
              const ns = ws.get(key.type);
              ns?.delete(key.key);
              if (ns !== undefined && ns.size === 0) ws.delete(key.type);
            }
          }

          this.version++;
          await this.persist();
          await this.pushConfig();
          return { version: this.version };
        }

        const keys = this.stringKeys(request);
        if (keys.length === 0) {
          throw new Error("Delete requires at least one key");
        }

        const namespace = keys[0];
        const ws = this.workspaceStore(workspace, false);
        if (ws === undefined) return { version: this.version };

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

        this.version++;
        await this.persist();
        await this.pushConfig();

        return { version: this.version };

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



      pushConfig: async function(this: ConfigService): Promise<void> {
        const pushProducer = this.pushProducer;
        if (pushProducer === null) return;

        const config: Record<string, unknown> = {};
        const ws = this.workspaceStore(DEFAULT_WORKSPACE, false);
        for (const [namespace, subMap] of ws ?? new Map<string, NamespaceStore>()) {
          const obj: Record<string, unknown> = {};
          for (const [k, v] of subMap) {
            obj[k] = v;
          }
          config[namespace] = obj;
        }

        await pushProducer.send({
          version: this.version,
          config,
        });

        console.log(`[ConfigService] Pushed configuration version ${this.version}`);

        },



      persist: async function(this: ConfigService): Promise<void> {
        const persistPath = this.persistPath;
        if (persistPath === null) return;

        try {
          const workspaces: Record<string, Record<string, Record<string, unknown>>> = {};

          for (const [workspace, ws] of this.store) {
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

          const json = JSON.stringify(
            { version: this.version, workspaces },
            null,
            2,
          );

          await writeTextFile(persistPath, json);
        } catch (err) {
          await Effect.runPromise(Effect.logError("[ConfigService] Failed to persist config", { error: errorMessage(err) }));
        }

        },



      loadFromDisk: async function(this: ConfigService): Promise<void> {
        const persistPath = this.persistPath;
        if (persistPath === null) return;

        try {
          const raw = await readTextFile(persistPath);
          const parsed = JSON.parse(raw) as {
            version: number;
            data?: Record<string, Record<string, unknown>>;
            workspaces?: Record<string, Record<string, Record<string, unknown>>>;
          };

          this.version = parsed.version ?? 0;
          this.store.clear();

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
              this.store.set(workspace, ws);
            }
          } else {
            const ws = new Map<string, NamespaceStore>();
            for (const [namespace, obj] of Object.entries(parsed.data ?? {})) {
              const subMap = new Map<string, unknown>();
              for (const [k, v] of Object.entries(obj)) {
                subMap.set(k, v);
              }
              ws.set(namespace, subMap);
            }
            this.store.set(DEFAULT_WORKSPACE, ws);
          }

          console.log(
            `[ConfigService] Loaded persisted config (version=${this.version}, workspaces=${this.store.size})`,
          );
        } catch {
          // File doesn't exist yet or is invalid — start fresh
          await Effect.runPromise(Effect.log("[ConfigService] No persisted config found, starting fresh"));
        }

        },



      stop: async function(this: ConfigService): Promise<void> {
        if (this.consumer !== null) {
          await this.consumer.close();
          this.consumer = null;
        }
        if (this.responseProducer !== null) {
          await this.responseProducer.close();
          this.responseProducer = null;
        }
        if (this.pushProducer !== null) {
          await this.pushProducer.close();
          this.pushProducer = null;
        }
        await baseStop();

        }
  });
  return service;
}

export const ConfigService = makeConfigService;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

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

export async function run(): Promise<void> {
  await Effect.runPromise(program);
}
