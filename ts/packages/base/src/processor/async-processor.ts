/**
 * Base async processor — foundation for all TrustGraph services.
 *
 * Handles pub/sub lifecycle, configuration subscription, and graceful shutdown.
 *
 * Python reference: trustgraph-base/trustgraph/base/async_processor.py
 */

import type { PubSubBackend } from "../backend/types.js";
import { NatsBackend } from "../backend/nats.js";
import { Effect } from "effect";
import { processorLifecycleError, type ProcessorLifecycleError } from "../errors.js";
import { loadProcessorRuntimeConfig } from "../runtime/config.js";

export interface ProcessorConfig {
  id: string;
  pubsubUrl?: string;
  metricsPort?: number;
  manageProcessSignals?: boolean;
  pubsub?: PubSubBackend;
}

export type ConfigHandler = (
  config: Record<string, unknown>,
  version: number,
) => Promise<void>;

export type EffectConfigHandler<E = never, R = never> = (
  config: Record<string, unknown>,
  version: number,
) => Effect.Effect<void, E, R>;

interface RegisteredSignalHandler {
  readonly signal: NodeJS.Signals;
  readonly handler: () => void;
}

export abstract class AsyncProcessor<RunError = ProcessorLifecycleError, RunRequirements = never> {
  protected pubsub: PubSubBackend;
  protected running = false;
  protected configHandlers: ConfigHandler[] = [];
  private shutdownCallbacks: Array<() => Promise<void>> = [];
  private signalHandlers: RegisteredSignalHandler[] = [];
  private readonly ownsPubSub: boolean;
  protected readonly config: ProcessorConfig;

  constructor(config: ProcessorConfig) {
    this.config = config;
    this.pubsub = config.pubsub ?? new NatsBackend(config.pubsubUrl ?? "nats://localhost:4222");
    this.ownsPubSub = config.pubsub === undefined;
  }

  registerConfigHandler(handler: ConfigHandler): void {
    this.configHandlers.push(handler);
  }

  async start(): Promise<void> {
    await Effect.runPromise(
      this.startEffect() as Effect.Effect<void, RunError | ProcessorLifecycleError>,
    );
  }

  async stop(): Promise<void> {
    await Effect.runPromise(this.stopEffect());
  }

  protected onShutdown(callback: () => Promise<void>): void {
    this.shutdownCallbacks.push(callback);
  }

  startEffect(): Effect.Effect<void, RunError | ProcessorLifecycleError, RunRequirements> {
    const processor = this;
    return Effect.gen(function* () {
      yield* Effect.sync(() => {
        processor.running = true;
        processor.registerProcessSignalHandlers();
      });

      yield* processor.runEffect();
    }).pipe(
      Effect.withSpan("trustgraph.processor.start", {
        attributes: {
          "trustgraph.processor.id": processor.config.id,
        },
      }),
    );
  }

  stopEffect(): Effect.Effect<void, ProcessorLifecycleError> {
    const processor = this;
    return Effect.gen(function* () {
      yield* Effect.sync(() => {
        processor.running = false;
        processor.unregisterProcessSignalHandlers();
      });

      for (const cb of processor.shutdownCallbacks) {
        yield* Effect.tryPromise({
          try: () => cb(),
          catch: (error) => processorLifecycleError(processor.config.id, "shutdown-callback", error),
        });
      }

      if (processor.ownsPubSub) {
        yield* Effect.tryPromise({
          try: () => processor.pubsub.close(),
          catch: (error) => processorLifecycleError(processor.config.id, "close-pubsub", error),
        });
      }
    });
  }

  protected run(): Promise<void> {
    return Effect.runPromise(this.runEffect() as unknown as Effect.Effect<void, RunError>);
  }

  protected runEffect(): Effect.Effect<void, RunError, RunRequirements> {
    return Effect.tryPromise({
      try: () => this.run(),
      catch: (error) => processorLifecycleError(this.config.id, "start", error),
    }) as unknown as Effect.Effect<void, RunError, RunRequirements>;
  }

  private registerProcessSignalHandlers(): void {
    if (this.config.manageProcessSignals === false || this.signalHandlers.length > 0) {
      return;
    }

    const shutdown = () => {
      console.log(`[${this.config.id}] Shutting down...`);
      void this.stop().then(() => process.exit(0));
    };
    const handlers: RegisteredSignalHandler[] = [
      { signal: "SIGINT", handler: shutdown },
      { signal: "SIGTERM", handler: shutdown },
    ];
    for (const { signal, handler } of handlers) {
      process.once(signal, handler);
    }
    this.signalHandlers = handlers;
  }

  private unregisterProcessSignalHandlers(): void {
    for (const { signal, handler } of this.signalHandlers) {
      process.off(signal, handler);
    }
    this.signalHandlers = [];
  }

  /**
   * Static launch helper — parses env/args and starts the processor.
   * Subclasses call: `MyProcessor.launch("my-service")`
   */
  static async launch<T extends AsyncProcessor<unknown, unknown>>(
    this: new (config: ProcessorConfig) => T,
    id: string,
  ): Promise<void> {
    const config = await Effect.runPromise(loadProcessorRuntimeConfig(id));
    const processor = new this(config);
    await processor.start();
  }
}
