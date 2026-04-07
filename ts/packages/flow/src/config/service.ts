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

import { readFile, writeFile, mkdir } from "node:fs/promises";
import { dirname } from "node:path";
import {
  AsyncProcessor,
  type ProcessorConfig,
  topics,
  type ConfigRequest,
  type ConfigResponse,
  type ConfigOperation,
} from "@trustgraph/base";
import type { PubSubBackend, BackendProducer, BackendConsumer, Message } from "@trustgraph/base";

export interface ConfigServiceConfig extends ProcessorConfig {
  persistPath?: string;
}

interface ConfigPush {
  version: number;
  config: Record<string, unknown>;
}

export class ConfigService extends AsyncProcessor {
  private store = new Map<string, Map<string, unknown>>();
  private version = 0;
  private readonly persistPath: string | null;
  private consumer: BackendConsumer<ConfigRequest> | null = null;
  private responseProducer: BackendProducer<ConfigResponse> | null = null;
  private pushProducer: BackendProducer<ConfigPush> | null = null;

  constructor(config: ConfigServiceConfig) {
    super(config);
    this.persistPath = config.persistPath ?? process.env.CONFIG_PERSIST_PATH ?? null;
  }

  protected override async run(): Promise<void> {
    // Optionally load persisted state
    if (this.persistPath) {
      await this.loadFromDisk();
    }

    // Create producers
    this.responseProducer = await this.pubsub.createProducer<ConfigResponse>({
      topic: topics.configResponse,
    });
    this.pushProducer = await this.pubsub.createProducer<ConfigPush>({
      topic: topics.configPush,
    });

    // Create consumer for config requests
    this.consumer = await this.pubsub.createConsumer<ConfigRequest>({
      topic: topics.configRequest,
      subscription: `${this.config.id}-config-request`,
    });

    // Push initial config
    await this.pushConfig();

    console.log(`[ConfigService] Listening on ${topics.configRequest}`);

    // Main consume loop
    while (this.running) {
      try {
        const msg = await this.consumer.receive(2000);
        if (!msg) continue;

        await this.handleMessage(msg);
        await this.consumer.acknowledge(msg);
      } catch (err) {
        if (!this.running) break;
        console.error("[ConfigService] Error in consume loop:", err);
        await sleep(1000);
      }
    }
  }

  private async handleMessage(msg: Message<ConfigRequest>): Promise<void> {
    const request = msg.value();
    const props = msg.properties();
    const requestId = props.id;

    if (!requestId) {
      console.warn("[ConfigService] Received request without id, ignoring");
      return;
    }

    try {
      const response = await this.handleOperation(request);
      await this.responseProducer!.send(response, { id: requestId });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      await this.responseProducer!.send(
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

    if (subMap) {
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
    if (!subMap) {
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
      if (subMap) {
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
      directory: subMap ? [...subMap.keys()] : [],
    };
  }

  private handleGetValues(request: ConfigRequest): ConfigResponse {
    const type = request.type ?? "";

    const values: { key: string; value: unknown }[] = [];

    for (const [namespace, subMap] of this.store) {
      if (!type || namespace === type || namespace.startsWith(`${type}.`) || namespace.startsWith(`${type}/`)) {
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
    if (!this.pushProducer) return;

    const config: Record<string, unknown> = {};
    for (const [namespace, subMap] of this.store) {
      const obj: Record<string, unknown> = {};
      for (const [k, v] of subMap) {
        obj[k] = v;
      }
      config[namespace] = obj;
    }

    await this.pushProducer.send({
      version: this.version,
      config,
    });

    console.log(`[ConfigService] Pushed configuration version ${this.version}`);
  }

  private async persist(): Promise<void> {
    if (!this.persistPath) return;

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

      await mkdir(dirname(this.persistPath), { recursive: true });
      await writeFile(this.persistPath, json, "utf-8");
    } catch (err) {
      console.error("[ConfigService] Failed to persist config:", err);
    }
  }

  private async loadFromDisk(): Promise<void> {
    if (!this.persistPath) return;

    try {
      const raw = await readFile(this.persistPath, "utf-8");
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
      console.log("[ConfigService] No persisted config found, starting fresh");
    }
  }

  override async stop(): Promise<void> {
    if (this.consumer) {
      await this.consumer.close();
      this.consumer = null;
    }
    if (this.responseProducer) {
      await this.responseProducer.close();
      this.responseProducer = null;
    }
    if (this.pushProducer) {
      await this.pushProducer.close();
      this.pushProducer = null;
    }
    await super.stop();
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function run(): Promise<void> {
  await ConfigService.launch("config-svc");
}
