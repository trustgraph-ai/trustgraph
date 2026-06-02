/**
 * Scoped Effect runtime helpers for legacy processor classes.
 *
 * These helpers make `Context.Service`/Layer composition the canonical
 * executable path while the processor internals remain Promise-based.
 */

import { Config as EffectConfig, Effect, Layer } from "effect";
import {
  processorLifecycleError,
  type FlowRuntimeError,
  type ProcessorLifecycleError,
  type PubSubError,
} from "../errors.js";
import { makeNatsBackend } from "../backend/nats.js";
import { makePubSubService, PubSub } from "../backend/pubsub.js";
import {
  ConsumerFactory,
  FlowRuntime,
  ProducerFactory,
  RequestResponseFactory,
  makeConsumerFactoryService,
  makeProducerFactoryService,
  makeRequestResponseFactoryService,
  runFlowRuntimeScoped,
} from "../messaging/runtime.js";
import {
  loadProcessorRuntimeConfig,
  type ProcessorRuntimeConfigOptions,
} from "../runtime/config.js";
import { loadMessagingRuntimeConfig } from "../runtime/messaging-config.js";
import type {
  EffectConfigHandler,
  ProcessorConfig,
  ProcessorRuntime,
} from "./async-processor.js";
import { runFlowProcessorDefinitionScoped } from "./flow-processor.js";
import type { Spec } from "../spec/types.js";

export interface ProcessorProgramOptions<
  Config extends ProcessorConfig,
  LoadError,
  LoadRequirements,
  RunError,
  RunRequirements,
> {
  readonly id: string;
  readonly make: (config: Config) => ProcessorRuntime<RunError, RunRequirements>;
  readonly loadConfig?: Effect.Effect<Config, LoadError, LoadRequirements>;
}

export interface FlowProcessorProgramOptions<
  Config extends ProcessorConfig,
  Error = never,
  FlowRequirements = never,
  LayerRequirements = never,
> {
  readonly id: string;
  readonly loadConfig?: Effect.Effect<Config, Error, LayerRequirements>;
  readonly specs: (config: Config) => ReadonlyArray<Spec<FlowRequirements>>;
  readonly configHandlers?: (
    config: Config,
  ) => ReadonlyArray<EffectConfigHandler<Error, FlowRequirements>>;
  readonly layer?: (
    config: Config,
  ) => Layer.Layer<FlowRequirements, Error, LayerRequirements>;
}

export const runProcessorScoped = Effect.fn("runProcessorScoped")(function* <
  Config extends ProcessorConfig,
  RunError,
  RunRequirements,
>(
  config: Config,
  make: (config: Config) => ProcessorRuntime<RunError, RunRequirements>,
) {
    const pubsub = yield* PubSub;
    const runtimeConfig = {
      ...config,
      manageProcessSignals: false,
      pubsub: pubsub.backend,
    } as Config;
    const processor = make(runtimeConfig);

    yield* Effect.addFinalizer(() =>
      Effect.tryPromise({
        try: () => processor.stop(),
        catch: (error) => processorLifecycleError(config.id, "stop", error),
      }).pipe(
        Effect.catch((error) =>
          Effect.logError("[Processor] Failed to stop processor", {
            error: error.message,
            operation: error.operation,
            processorId: error.processorId,
          }),
        ),
      ),
    );

    yield* processor.startEffect;
});

export function makeProcessorProgram<
  Config extends ProcessorConfig,
  LoadError = never,
  LoadRequirements = never,
  RunError = ProcessorLifecycleError,
  RunRequirements = never,
>(
  options: ProcessorProgramOptions<Config, LoadError, LoadRequirements, RunError, RunRequirements>,
) {
  return Effect.scoped(
    Effect.gen(function* () {
      const config = yield* (
        options.loadConfig ??
        loadProcessorRuntimeConfig(options.id, {
          manageProcessSignals: false,
        } satisfies ProcessorRuntimeConfigOptions)
      );

      const runtimeConfig = {
        ...config,
        manageProcessSignals: false,
      } as Config;

      const pubsub = makePubSubService(makeNatsBackend(runtimeConfig.pubsubUrl ?? "nats://localhost:4222"));
      const messagingConfig = yield* loadMessagingRuntimeConfig();
      yield* Effect.addFinalizer(() =>
        pubsub.close.pipe(
          Effect.catch((error) =>
            Effect.logError("[PubSub] Failed to close processor backend", {
              error: error.message,
              operation: error.operation,
            }),
          ),
        ),
      );
      const processorEffect = runProcessorScoped<Config, RunError, RunRequirements>(
        runtimeConfig,
        options.make,
      );
      yield* processorEffect.pipe(
        Effect.provideService(PubSub, pubsub),
        Effect.provideService(ProducerFactory, ProducerFactory.of(makeProducerFactoryService(pubsub))),
        Effect.provideService(ConsumerFactory, ConsumerFactory.of(makeConsumerFactoryService(pubsub, messagingConfig))),
        Effect.provideService(
          RequestResponseFactory,
          RequestResponseFactory.of(makeRequestResponseFactoryService(pubsub, messagingConfig)),
        ),
        Effect.provideService(FlowRuntime, FlowRuntime.of({ run: runFlowRuntimeScoped })),
      );
    }),
  );
}

export const makeAsyncProcessorProgram = makeProcessorProgram;

export function makeFlowProcessorProgram<
  Config extends ProcessorConfig,
  Error = never,
  FlowRequirements = never,
  LayerRequirements = never,
>(
  options: FlowProcessorProgramOptions<Config, Error, FlowRequirements, LayerRequirements> & {
    readonly layer: (config: Config) => Layer.Layer<FlowRequirements, Error, LayerRequirements>;
  },
): Effect.Effect<
  never,
  Error | EffectConfig.ConfigError | PubSubError | FlowRuntimeError,
  LayerRequirements
>;

export function makeFlowProcessorProgram<
  Config extends ProcessorConfig,
  Error = never,
  FlowRequirements = never,
>(
  options: FlowProcessorProgramOptions<Config, Error, FlowRequirements, FlowRequirements> & {
    readonly layer?: undefined;
  },
): Effect.Effect<
  never,
  Error | EffectConfig.ConfigError | PubSubError | FlowRuntimeError,
  FlowRequirements
>;

export function makeFlowProcessorProgram<
  Config extends ProcessorConfig,
  Error = never,
  FlowRequirements = never,
  LayerRequirements = never,
>(
  options: FlowProcessorProgramOptions<Config, Error, FlowRequirements, LayerRequirements>,
) {
  return Effect.scoped(
    Effect.gen(function* () {
      const config = yield* (
        options.loadConfig ??
        loadProcessorRuntimeConfig(options.id, {
          manageProcessSignals: false,
        } satisfies ProcessorRuntimeConfigOptions)
      );

      const runtimeConfig = {
        ...config,
        manageProcessSignals: false,
      } as Config;

      const pubsub = makePubSubService(makeNatsBackend(runtimeConfig.pubsubUrl ?? "nats://localhost:4222"));
      const messagingConfig = yield* loadMessagingRuntimeConfig();
      yield* Effect.addFinalizer(() =>
        pubsub.close.pipe(
          Effect.catch((error) =>
            Effect.logError("[PubSub] Failed to close processor backend", {
              error: error.message,
              operation: error.operation,
            }),
          ),
        ),
      );

      const configHandlers = options.configHandlers?.(runtimeConfig);
      const processorOptions = {
        id: runtimeConfig.id,
        pubsub: pubsub.backend,
        specifications: options.specs(runtimeConfig),
        ...(configHandlers === undefined ? {} : { configHandlers }),
      };
      const processorLayer = Layer.effectDiscard(
        runFlowProcessorDefinitionScoped<FlowRequirements, Error, FlowRequirements>(processorOptions),
      );
      const runtimeLayer = Layer.mergeAll(
        Layer.succeed(PubSub, PubSub.of(pubsub)),
        Layer.succeed(ProducerFactory, ProducerFactory.of(makeProducerFactoryService(pubsub))),
        Layer.succeed(ConsumerFactory, ConsumerFactory.of(makeConsumerFactoryService(pubsub, messagingConfig))),
        Layer.succeed(
          RequestResponseFactory,
          RequestResponseFactory.of(makeRequestResponseFactoryService(pubsub, messagingConfig)),
        ),
        Layer.succeed(FlowRuntime, FlowRuntime.of({ run: runFlowRuntimeScoped })),
      );
      if (options.layer !== undefined) {
        return yield* Layer.launch(
          processorLayer.pipe(
            Layer.provide(options.layer(runtimeConfig)),
            Layer.provide(runtimeLayer),
          ),
        );
      }

      return yield* Layer.launch(processorLayer.pipe(Layer.provide(runtimeLayer)));
    }),
  );
}
