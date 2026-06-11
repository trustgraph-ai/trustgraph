/**
 * Base async processor — foundation for all TrustGraph services.
 *
 * Handles pub/sub lifecycle, configuration subscription, and graceful shutdown.
 *
 * Python reference: trustgraph-base/trustgraph/base/async_processor.py
 */

import type { PubSubBackend } from "../backend/types.js";
import { makeNatsBackend, makeNatsBackendScoped } from "../backend/nats.js";
import type { Cause, Config as EffectConfig, } from "effect";
import { Context, Effect } from "effect";
import type { ProcessorLifecycleError } from "../errors.js";
import { processorLifecycleError, } from "../errors.js";
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
) => Effect.Effect<void, Cause.UnknownError>;

export type EffectConfigHandler<E = never, R = never> = (
  config: Record<string, unknown>,
  version: number,
) => Effect.Effect<void, E, R>;

declare const processorRunErrorType: unique symbol;
declare const processorRunRequirementsType: unique symbol;

export interface ProcessorRuntime<RunError = ProcessorLifecycleError, RunRequirements = never> {
  readonly [processorRunErrorType]?: RunError;
  readonly [processorRunRequirementsType]?: RunRequirements;
  readonly start: (
    context: Context.Context<RunRequirements>,
  ) => Effect.Effect<void, RunError | ProcessorLifecycleError>;
  readonly stop: Effect.Effect<void, ProcessorLifecycleError>;
  startEffect: Effect.Effect<void, RunError | ProcessorLifecycleError, RunRequirements>;
  stopEffect: Effect.Effect<void, ProcessorLifecycleError>;
}

export interface AsyncProcessorRuntime<
  RunError = ProcessorLifecycleError,
  RunRequirements = never,
> extends ProcessorRuntime<RunError, RunRequirements> {
  readonly config: ProcessorConfig;
  readonly pubsub: PubSubBackend;
  readonly configHandlers: Array<EffectConfigHandler<RunError | ProcessorLifecycleError, RunRequirements>>;
  readonly running: boolean;
  readonly isRunning: () => boolean;
  readonly registerConfigHandler: (
    handler: EffectConfigHandler<RunError | ProcessorLifecycleError, RunRequirements>,
  ) => void;
  readonly onShutdown: (callback: () => Effect.Effect<void, Cause.UnknownError>) => void;
  readonly run: (
    context: Context.Context<RunRequirements>,
  ) => Effect.Effect<void, RunError | ProcessorLifecycleError>;
  runEffect: Effect.Effect<void, RunError | ProcessorLifecycleError, RunRequirements>;
}

export interface AsyncProcessorRuntimeOptions<
  RunError = ProcessorLifecycleError,
  RunRequirements = never,
> {
  readonly run?: (
    processor: AsyncProcessorRuntime<RunError, RunRequirements>,
  ) => Effect.Effect<void, RunError, RunRequirements>;
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
  const configHandlers: Array<EffectConfigHandler<RunError | ProcessorLifecycleError, RunRequirements>> = [];
  const shutdownCallbacks: Array<() => Effect.Effect<void, Cause.UnknownError>> = [];
  let running = false;
  let signalHandlers: RegisteredSignalHandler[] = [];

  const registerProcessSignalHandlers = (): void => {
    if (config.manageProcessSignals === false || signalHandlers.length > 0) {
      return;
    }

    const shutdown = () => {
      Effect.runFork(
        Effect.log(`[${config.id}] Shutting down...`).pipe(
          Effect.flatMap(() => processor.stop),
          Effect.mapError((error) => processorLifecycleError(config.id, "signal-shutdown", error)),
          Effect.match({
            onFailure: () => process.exit(1),
            onSuccess: () => process.exit(0),
          }),
        ),
      );
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
    start: (context) => Effect.provide(processor.startEffect, context),
    get stop() {
      return processor.stopEffect;
    },
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
          yield* cb().pipe(
            Effect.mapError((error) => processorLifecycleError(config.id, "shutdown-callback", error)),
          );
        }

        if (ownsPubSub) {
          yield* pubsub.close.pipe(
            Effect.mapError((error) => processorLifecycleError(config.id, "close-pubsub", error)),
          );
        }
      });
      return stopProcessor();
    },
    run: (context) => Effect.provide(processor.runEffect, context),
    get runEffect() {
      if (options.runEffect !== undefined) {
        return options.runEffect(processor);
      }
      return options.run?.(processor).pipe(
        Effect.mapError((error) => processorLifecycleError(config.id, "start", error)),
      ) ?? Effect.void;
    },
  };

  return processor;
}

export const makeAsyncProcessorScoped = Effect.fn("makeAsyncProcessorScoped")(function* <
  RunError = ProcessorLifecycleError,
  RunRequirements = never,
>(
  config: ProcessorConfig,
  options: AsyncProcessorRuntimeOptions<RunError, RunRequirements> = {},
) {
  if (config.pubsub !== undefined) {
    return makeAsyncProcessor(config, options);
  }

  const pubsub = yield* makeNatsBackendScoped(config.pubsubUrl ?? "nats://localhost:4222");
  return makeAsyncProcessor(
    {
      ...config,
      pubsub,
    },
    options,
  );
});

export type AsyncProcessor<
  RunError = ProcessorLifecycleError,
  RunRequirements = never,
> = AsyncProcessorRuntime<RunError, RunRequirements>;

export const AsyncProcessor = Object.assign(
  function AsyncProcessor(config: ProcessorConfig) {
    return makeAsyncProcessor(config);
  },
  {
    launch<RunError, T extends ProcessorRuntime<RunError, never>>(
      this: new (config: ProcessorConfig) => T,
      id: string,
    ): Effect.Effect<void, ProcessorLifecycleError | EffectConfig.ConfigError> {
      const ProcessorCtor = this;
      return Effect.gen(function* () {
        const config = yield* loadProcessorRuntimeConfig(id);
        const processor = new ProcessorCtor(config);
        yield* processor.start(Context.empty()).pipe(
          Effect.mapError((error) => processorLifecycleError(id, "launch", error)),
        );
      });
    },
  },
) as unknown as {
  new <RunError = ProcessorLifecycleError, RunRequirements = never>(
    config: ProcessorConfig,
  ): AsyncProcessor<RunError, RunRequirements>;
  <RunError = ProcessorLifecycleError, RunRequirements = never>(
    config: ProcessorConfig,
  ): AsyncProcessor<RunError, RunRequirements>;
  launch<RunError, T extends ProcessorRuntime<RunError, never>>(
    this: new (config: ProcessorConfig) => T,
    id: string,
  ): Effect.Effect<void, ProcessorLifecycleError | EffectConfig.ConfigError>;
};
