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
  AsyncProcessor,
  type ProcessorConfig,
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
import type { BackendProducer, BackendConsumer, Message } from "@trustgraph/base";
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

export class ConfigService extends AsyncProcessor {
  private store = new Map<string, Map<string, unknown>>();
  private version = 0;
  private readonly persistPath: string | null;
  private consumer: BackendConsumer<ConfigRequest> | null = null;
  private responseProducer: BackendProducer<ConfigResponse> | null = null;
  private pushProducer: BackendProducer<ConfigPush> | null = null;

  constructor(config: ConfigServiceConfig) {
    super(config);
    this.persistPath = config.persistPath ?? null;
  }

  protected override async run(): Promise<void> {
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
  }

  private async handleMessage(msg: Message<ConfigRequest>): Promise<void> {
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
  }

  private async handleOperation(request: ConfigRequest): Promise<ConfigResponse> {
    const op: ConfigOperation = request.operation;

    switch (op) {
      case "get":
        return this.handleGet(request.keys ?? []);

      case "put":
        return await this.handlePut(request.keys ?? [], request.values ?? {});

      case "delete":
        return await this.handleDelete(request.keys ?? []);

      case "list":
        return this.handleList(request.keys ?? []);

      case "config":
        return this.handleConfigDump();

      case "getvalues":
        return this.handleGetValues(request);

      default:
        throw new Error(`Unknown config operation: ${op as string}`);
    }
  }

  private handleGet(keys: string[]): ConfigResponse {
    if (keys.length === 0) {
      return { version: this.version, values: {} };
    }

    const values: Record<string, unknown> = {};
    const namespace = keys[0];
    const subMap = this.store.get(namespace);

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
          if (subMap.has(key)) {
            values[key] = subMap.get(key);
          }
        }
      }
    }

    return { version: this.version, values };
  }

  private async handlePut(
    keys: string[],
    values: Record<string, unknown>,
  ): Promise<ConfigResponse> {
    if (keys.length === 0) {
      throw new Error("Put requires at least one key (namespace)");
    }

    const namespace = keys[0];
    let subMap = this.store.get(namespace);
    if (subMap === undefined) {
      subMap = new Map<string, unknown>();
      this.store.set(namespace, subMap);
    }

    for (const [k, v] of Object.entries(values)) {
      subMap.set(k, v);
    }

    this.version++;
    await this.persist();
    await this.pushConfig();

    return { version: this.version };
  }

  private async handleDelete(keys: string[]): Promise<ConfigResponse> {
    if (keys.length === 0) {
      throw new Error("Delete requires at least one key");
    }

    const namespace = keys[0];

    if (keys.length === 1) {
      // Delete entire namespace
      this.store.delete(namespace);
    } else {
      // Delete specific keys within namespace
      const subMap = this.store.get(namespace);
      if (subMap !== undefined) {
        for (let i = 1; i < keys.length; i++) {
          subMap.delete(keys[i]);
        }
        if (subMap.size === 0) {
          this.store.delete(namespace);
        }
      }
    }

    this.version++;
    await this.persist();
    await this.pushConfig();

    return { version: this.version };
  }

  private handleList(keys: string[]): ConfigResponse {
    if (keys.length === 0) {
      // List all namespaces
      return {
        version: this.version,
        directory: [...this.store.keys()],
      };
    }

    const namespace = keys[0];
    const subMap = this.store.get(namespace);

    return {
      version: this.version,
      directory: subMap !== undefined ? [...subMap.keys()] : [],
    };
  }

  private handleGetValues(request: ConfigRequest): ConfigResponse {
    const type = request.type ?? "";

    const values: { key: string; value: unknown }[] = [];

    for (const [namespace, subMap] of this.store) {
      if (
        type.length === 0 ||
        namespace === type ||
        namespace.startsWith(`${type}.`) ||
        namespace.startsWith(`${type}/`)
      ) {
        for (const [k, v] of subMap) {
          values.push({ key: `${namespace}.${k}`, value: v });
        }
      }
    }

    return { version: this.version, values: values as unknown as Record<string, unknown> };
  }

  private handleConfigDump(): ConfigResponse {
    const config: Record<string, unknown> = {};

    for (const [namespace, subMap] of this.store) {
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
  }

  private async pushConfig(): Promise<void> {
    const pushProducer = this.pushProducer;
    if (pushProducer === null) return;

    const config: Record<string, unknown> = {};
    for (const [namespace, subMap] of this.store) {
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
  }

  private async persist(): Promise<void> {
    const persistPath = this.persistPath;
    if (persistPath === null) return;

    try {
      const data: Record<string, Record<string, unknown>> = {};

      for (const [namespace, subMap] of this.store) {
        const obj: Record<string, unknown> = {};
        for (const [k, v] of subMap) {
          obj[k] = v;
        }
        data[namespace] = obj;
      }

      const json = JSON.stringify(
        { version: this.version, data },
        null,
        2,
      );

      await writeTextFile(persistPath, json);
    } catch (err) {
      await Effect.runPromise(Effect.logError("[ConfigService] Failed to persist config", { error: errorMessage(err) }));
    }
  }

  private async loadFromDisk(): Promise<void> {
    const persistPath = this.persistPath;
    if (persistPath === null) return;

    try {
      const raw = await readTextFile(persistPath);
      const parsed = JSON.parse(raw) as {
        version: number;
        data: Record<string, Record<string, unknown>>;
      };

      this.version = parsed.version ?? 0;
      this.store.clear();

      for (const [namespace, obj] of Object.entries(parsed.data ?? {})) {
        const subMap = new Map<string, unknown>();
        for (const [k, v] of Object.entries(obj)) {
          subMap.set(k, v);
        }
        this.store.set(namespace, subMap);
      }

      console.log(
        `[ConfigService] Loaded persisted config (version=${this.version}, namespaces=${this.store.size})`,
      );
    } catch {
      // File doesn't exist yet or is invalid — start fresh
      await Effect.runPromise(Effect.log("[ConfigService] No persisted config found, starting fresh"));
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
    if (this.pushProducer !== null) {
      await this.pushProducer.close();
      this.pushProducer = null;
    }
    await super.stop();
  }
}

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
  make: (config) => new ConfigService(config),
});

export async function run(): Promise<void> {
  await Effect.runPromise(program);
}
