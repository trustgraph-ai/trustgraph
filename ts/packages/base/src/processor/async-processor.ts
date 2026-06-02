/**
 * Base async processor — foundation for all TrustGraph services.
 *
 * Handles pub/sub lifecycle, configuration subscription, and graceful shutdown.
 *
 * Python reference: trustgraph-base/trustgraph/base/async_processor.py
 */

import type { PubSubBackend } from "../backend/types.js";
import { makeNatsBackend } from "../backend/nats.js";
import { Context, Effect } from "effect";
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

declare const processorRunErrorType: unique symbol;
declare const processorRunRequirementsType: unique symbol;

export interface ProcessorRuntime<RunError = ProcessorLifecycleError, RunRequirements = never> {
  readonly [processorRunErrorType]?: RunError;
  readonly [processorRunRequirementsType]?: RunRequirements;
  readonly start: (context: Context.Context<RunRequirements>) => Promise<void>;
  readonly stop: () => Promise<void>;
  startEffect: Effect.Effect<void, RunError | ProcessorLifecycleError, RunRequirements>;
  stopEffect: Effect.Effect<void, ProcessorLifecycleError>;
}

export interface AsyncProcessorRuntime<
  RunError = ProcessorLifecycleError,
  RunRequirements = never,
> extends ProcessorRuntime<RunError, RunRequirements> {
  readonly config: ProcessorConfig;
  readonly pubsub: PubSubBackend;
  readonly configHandlers: ConfigHandler[];
  readonly running: boolean;
  readonly isRunning: () => boolean;
  readonly registerConfigHandler: (handler: ConfigHandler) => void;
  readonly onShutdown: (callback: () => Promise<void>) => void;
  readonly run: (context: Context.Context<RunRequirements>) => Promise<void>;
  runEffect: Effect.Effect<void, RunError | ProcessorLifecycleError, RunRequirements>;
}

export interface AsyncProcessorRuntimeOptions<
  RunError = ProcessorLifecycleError,
  RunRequirements = never,
> {
  readonly run?: (
    processor: AsyncProcessorRuntime<RunError, RunRequirements>,
  ) => Promise<void>;
  readonly runEffect?: (
    processor: AsyncProcessorRuntime<RunError, RunRequirements>,
  ) => Effect.Effect<void, RunError, RunRequirements>;
}

interface RegisteredSignalHandler {
  readonly signal: NodeJS.Signals;
  readonly handler: () => void;
}

export function makeAsyncProcessor<
  RunError = ProcessorLifecycleError,
  RunRequirements = never,
>(
  config: ProcessorConfig,
  options: AsyncProcessorRuntimeOptions<RunError, RunRequirements> = {},
): AsyncProcessorRuntime<RunError, RunRequirements> {
  const pubsub = config.pubsub ?? makeNatsBackend(config.pubsubUrl ?? "nats://localhost:4222");
  const ownsPubSub = config.pubsub === undefined;
  const configHandlers: ConfigHandler[] = [];
  const shutdownCallbacks: Array<() => Promise<void>> = [];
  let running = false;
  let signalHandlers: RegisteredSignalHandler[] = [];

  const registerProcessSignalHandlers = (): void => {
    if (config.manageProcessSignals === false || signalHandlers.length > 0) {
      return;
    }

    const shutdown = () => {
      void Effect.runPromise(
        Effect.log(`[${config.id}] Shutting down...`).pipe(
          Effect.flatMap(() =>
            Effect.tryPromise({
              try: () => processor.stop(),
              catch: (error) => processorLifecycleError(config.id, "signal-shutdown", error),
            }),
          ),
        ),
      ).then(() => process.exit(0), () => process.exit(1));
    };
    const handlers: RegisteredSignalHandler[] = [
      { signal: "SIGINT", handler: shutdown },
      { signal: "SIGTERM", handler: shutdown },
    ];
    for (const { signal, handler } of handlers) {
      process.once(signal, handler);
    }
    signalHandlers = handlers;
  };

  const unregisterProcessSignalHandlers = (): void => {
    for (const { signal, handler } of signalHandlers) {
      process.off(signal, handler);
    }
    signalHandlers = [];
  };

  const processor: AsyncProcessorRuntime<RunError, RunRequirements> = {
    config,
    pubsub,
    configHandlers,
    get running() {
      return running;
    },
    isRunning: () => running,
    registerConfigHandler: (handler) => {
      configHandlers.push(handler);
    },
    start: (context) => Effect.runPromiseWith(context)(processor.startEffect),
    stop: () => Effect.runPromise(processor.stopEffect),
    onShutdown: (callback) => {
      shutdownCallbacks.push(callback);
    },
    get startEffect() {
      const startProcessor = Effect.fn("trustgraph.processor.start")(function* () {
        yield* Effect.sync(() => {
          running = true;
          registerProcessSignalHandlers();
        });

        yield* processor.runEffect;
      });
      return startProcessor().pipe(
        Effect.withSpan("trustgraph.processor.start", {
          attributes: {
            "trustgraph.processor.id": config.id,
          },
        }),
      );
    },
    get stopEffect() {
      const stopProcessor = Effect.fn("trustgraph.processor.stop")(function* () {
        yield* Effect.sync(() => {
          running = false;
          unregisterProcessSignalHandlers();
        });

        for (const cb of shutdownCallbacks) {
          yield* Effect.tryPromise({
            try: () => cb(),
            catch: (error) => processorLifecycleError(config.id, "shutdown-callback", error),
          });
        }

        if (ownsPubSub) {
          yield* Effect.tryPromise({
            try: () => pubsub.close(),
            catch: (error) => processorLifecycleError(config.id, "close-pubsub", error),
          });
        }
      });
      return stopProcessor();
    },
    run: (context) => Effect.runPromiseWith(context)(processor.runEffect),
    get runEffect() {
      if (options.runEffect !== undefined) {
        return options.runEffect(processor);
      }
      return Effect.tryPromise({
        try: () => options.run?.(processor) ?? Promise.resolve(),
        catch: (error) => processorLifecycleError(config.id, "start", error),
      });
    },
  };

  return processor;
}

export type AsyncProcessor<
  RunError = ProcessorLifecycleError,
  RunRequirements = never,
> = AsyncProcessorRuntime<RunError, RunRequirements>;

export const AsyncProcessor = Object.assign(
  function AsyncProcessor(config: ProcessorConfig) {
    return makeAsyncProcessor(config);
  },
  {
    launch<T extends ProcessorRuntime<unknown, never>>(
      this: new (config: ProcessorConfig) => T,
      id: string,
    ): Promise<void> {
      const ProcessorCtor = this;
      return Effect.runPromise(
        Effect.gen(function* () {
          const config = yield* loadProcessorRuntimeConfig(id);
          const processor = new ProcessorCtor(config);
          yield* Effect.tryPromise({
            try: () => processor.start(Context.empty()),
            catch: (error) => processorLifecycleError(id, "launch", error),
          });
        }),
      );
    },
  },
) as unknown as {
  new <RunError = ProcessorLifecycleError, RunRequirements = never>(
    config: ProcessorConfig,
  ): AsyncProcessor<RunError, RunRequirements>;
  <RunError = ProcessorLifecycleError, RunRequirements = never>(
    config: ProcessorConfig,
  ): AsyncProcessor<RunError, RunRequirements>;
  launch<T extends ProcessorRuntime<unknown, never>>(
    this: new (config: ProcessorConfig) => T,
    id: string,
  ): Promise<void>;
};
