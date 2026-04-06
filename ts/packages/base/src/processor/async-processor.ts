/**
 * Base async processor — foundation for all TrustGraph services.
 *
 * Handles pub/sub lifecycle, configuration subscription, and graceful shutdown.
 *
 * Python reference: trustgraph-base/trustgraph/base/async_processor.py
 */

import type { PubSubBackend } from "../backend/types.js";
import { NatsBackend } from "../backend/nats.js";
import { topics } from "../schema/topics.js";

export interface ProcessorConfig {
  id: string;
  pubsubUrl?: string;
  metricsPort?: number;
}

export type ConfigHandler = (
  config: Record<string, unknown>,
  version: number,
) => Promise<void>;

export abstract class AsyncProcessor {
  protected pubsub: PubSubBackend;
  protected running = false;
  protected configHandlers: ConfigHandler[] = [];
  private shutdownCallbacks: Array<() => Promise<void>> = [];

  constructor(protected readonly config: ProcessorConfig) {
    this.pubsub = new NatsBackend(config.pubsubUrl ?? "nats://localhost:4222");
  }

  registerConfigHandler(handler: ConfigHandler): void {
    this.configHandlers.push(handler);
  }

  async start(): Promise<void> {
    this.running = true;
    // Set up graceful shutdown
    const shutdown = async () => {
      console.log(`[${this.config.id}] Shutting down...`);
      await this.stop();
      process.exit(0);
    };
    process.on("SIGINT", shutdown);
    process.on("SIGTERM", shutdown);

    await this.run();
  }

  async stop(): Promise<void> {
    this.running = false;
    for (const cb of this.shutdownCallbacks) {
      await cb();
    }
    await this.pubsub.close();
  }

  protected onShutdown(callback: () => Promise<void>): void {
    this.shutdownCallbacks.push(callback);
  }

  protected abstract run(): Promise<void>;

  /**
   * Static launch helper — parses env/args and starts the processor.
   * Subclasses call: `MyProcessor.launch("my-service")`
   */
  static async launch<T extends AsyncProcessor>(
    this: new (config: ProcessorConfig) => T,
    id: string,
  ): Promise<void> {
    const config: ProcessorConfig = {
      id,
      pubsubUrl: process.env.NATS_URL ?? process.env.PULSAR_HOST,
      metricsPort: parseInt(process.env.METRICS_PORT ?? "8000", 10),
    };

    const processor = new this(config);
    await processor.start();
  }
}
