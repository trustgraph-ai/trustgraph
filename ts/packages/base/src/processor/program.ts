/**
 * Scoped Effect runtime helpers for legacy processor classes.
 *
 * These helpers make `Context.Service`/Layer composition the canonical
 * executable path while the processor internals remain Promise-based.
 */

import { Config as EffectConfig, Effect, Layer, Scope } from "effect";
import {
  processorLifecycleError,
  type FlowRuntimeError,
  type ProcessorLifecycleError,
  type PubSubError,
} from "../errors.js";
import { NatsBackend } from "../backend/nats.js";
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
  AsyncProcessor,
  EffectConfigHandler,
  ProcessorConfig,
} from "./async-processor.js";
import { runFlowProcessorDefinitionScoped } from "./flow-processor.js";
import type { Spec } from "../spec/types.js";

type ProcessorRunError<Processor> = Processor extends AsyncProcessor<infer Error, unknown> ? Error : never;
type ProcessorRunRequirements<Processor> = Processor extends AsyncProcessor<unknown, infer Requirements> ? Requirements : never;

export interface ProcessorProgramOptions<
  Config extends ProcessorConfig,
  Error,
  Requirements,
  Processor extends AsyncProcessor<unknown, unknown>,
> {
  readonly id: string;
  readonly make: (config: Config) => Processor;
  readonly loadConfig?: Effect.Effect<Config, Error, Requirements>;
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

export function runProcessorScoped<
  Config extends ProcessorConfig,
  Processor extends AsyncProcessor<unknown, unknown>,
>(
  config: Config,
  make: (config: Config) => Processor,
): Effect.Effect<
  void,
  ProcessorRunError<Processor> | ProcessorLifecycleError,
  PubSub | Scope.Scope | ProcessorRunRequirements<Processor>
> {
  return Effect.gen(function* () {
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

    const typedProcessor = processor as unknown as AsyncProcessor<
      ProcessorRunError<Processor>,
      ProcessorRunRequirements<Processor>
    >;
    yield* typedProcessor.startEffect();
  });
}

export function makeProcessorProgram<
  Config extends ProcessorConfig,
  Error = never,
  Requirements = never,
  Processor extends AsyncProcessor<unknown, unknown> = AsyncProcessor,
>(
  options: ProcessorProgramOptions<Config, Error, Requirements, Processor>,
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

      const pubsub = makePubSubService(new NatsBackend(runtimeConfig.pubsubUrl ?? "nats://localhost:4222"));
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
      const processorEffect = runProcessorScoped<Config, Processor>(
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
  options: FlowProcessorProgramOptions<Config, Error, FlowRequirements, LayerRequirements>,
): Effect.Effect<
  void,
  Error | EffectConfig.ConfigError | PubSubError | FlowRuntimeError,
  LayerRequirements
> {
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

      const pubsub = makePubSubService(new NatsBackend(runtimeConfig.pubsubUrl ?? "nats://localhost:4222"));
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
      const dependencyLayer = options.layer?.(runtimeConfig) ??
        (Layer.empty as unknown as Layer.Layer<FlowRequirements, Error, LayerRequirements>);
      const providedProcessorLayer = processorLayer.pipe(
        Layer.provide(dependencyLayer),
        Layer.provide(runtimeLayer),
      );

      return yield* Layer.launch(providedProcessorLayer);
    }),
  );
}
