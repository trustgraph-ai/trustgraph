/**
 * Flow-aware processor that manages dynamic flow instances.
 *
 * Subscribes to config-push topic and dynamically creates/destroys
 * flow instances based on the configuration received.
 *
 * Python reference: trustgraph-base/trustgraph/base/flow_processor.py
 */

import {
  makeAsyncProcessor,
  type AsyncProcessorRuntime,
  type ConfigHandler,
  type EffectConfigHandler,
  type ProcessorRuntime,
  type ProcessorConfig,
} from "./async-processor.js";
import type { Spec } from "../spec/types.js";
import type { BackendConsumer, PubSubBackend } from "../backend/types.js";
import { Flow, type FlowDefinition } from "./flow.js";
import { topics } from "../schema/topics.js";
import {
  pubSubError,
  type FlowRuntimeError,
  type ProcessorLifecycleError,
  type PubSubError,
} from "../errors.js";
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
import { makePubSubService, PubSub } from "../backend/pubsub.js";
import { loadMessagingRuntimeConfig } from "../runtime/messaging-config.js";
import { Duration, Effect, Exit, Layer, ManagedRuntime, Scope } from "effect";
import * as O from "effect/Option";
import * as S from "effect/Schema";

interface ConfigPush {
  version: number;
  config: Record<string, unknown>;
}

interface ActiveFlow {
  readonly scope: Scope.Closeable;
}

export interface FlowProcessorRuntimeOptions<
  FlowRequirements = never,
  ConfigHandlerError = never,
  ConfigHandlerRequirements = never,
> {
  readonly id: string;
  readonly pubsub: PubSubBackend;
  readonly specifications: ReadonlyArray<Spec<FlowRequirements>>;
  readonly configHandlers?: ReadonlyArray<
    EffectConfigHandler<ConfigHandlerError, ConfigHandlerRequirements>
  >;
  readonly isRunning?: () => boolean;
}

type FlowProcessorRuntimeRequirements<FlowRequirements> =
  | PubSub
  | FlowRuntime
  | ProducerFactory
  | ConsumerFactory
  | RequestResponseFactory
  | Scope.Scope
  | FlowRequirements;

export type FlowProcessorStartEffect<FlowRequirements> = Effect.Effect<
  void,
  PubSubError | FlowRuntimeError | ProcessorLifecycleError,
  FlowProcessorRuntimeRequirements<FlowRequirements>
>;

export interface FlowProcessorRuntime<FlowRequirements = never>
  extends ProcessorRuntime<
    PubSubError | FlowRuntimeError | ProcessorLifecycleError,
    FlowProcessorRuntimeRequirements<FlowRequirements>
  > {
  readonly config: ProcessorConfig;
  readonly pubsub: PubSubBackend;
  readonly configHandlers: ConfigHandler[];
  readonly isRunning: () => boolean;
  readonly registerConfigHandler: (handler: ConfigHandler) => void;
  readonly registerSpecification: (spec: Spec<FlowRequirements>) => void;
  readonly specifications: ReadonlyArray<Spec<FlowRequirements>>;
}

export interface MakeFlowProcessorOptions<FlowRequirements = never> {
  readonly specifications?: ReadonlyArray<Spec<FlowRequirements>>;
  readonly provide?: (
    effect: FlowProcessorStartEffect<FlowRequirements>,
  ) => FlowProcessorStartEffect<FlowRequirements>;
}

const ConfigPushSchema = S.Struct({
  version: S.Number,
  config: S.Record(S.String, S.Unknown),
});

const FlowDefinitionSchema = S.Struct({
  topics: S.optionalKey(S.Record(S.String, S.String)),
  parameters: S.optionalKey(S.Record(S.String, S.Unknown)),
});

const FlowDefinitionsSchema = S.Record(S.String, FlowDefinitionSchema);

const decodeFlowDefinitions = S.decodeUnknownOption(FlowDefinitionsSchema);

export function runFlowProcessorDefinitionScoped<
  FlowRequirements = never,
  ConfigHandlerError = never,
  ConfigHandlerRequirements = never,
>(
  options: FlowProcessorRuntimeOptions<
    FlowRequirements,
    ConfigHandlerError,
    ConfigHandlerRequirements
  >,
): Effect.Effect<
  void,
  PubSubError | FlowRuntimeError | ConfigHandlerError,
  | PubSub
  | FlowRuntime
  | ProducerFactory
  | ConsumerFactory
  | RequestResponseFactory
  | Scope.Scope
  | FlowRequirements
  | ConfigHandlerRequirements
> {
  const flows = new Map<string, ActiveFlow>();
  let configConsumer: BackendConsumer<ConfigPush> | null = null;
  let lastFlowsJson = "";
  const isRunning = options.isRunning ?? (() => true);

  const closeFlowEffect = (name: string, activeFlow: ActiveFlow): Effect.Effect<void> =>
    Scope.close(activeFlow.scope, Exit.void).pipe(
      Effect.tap(() => Effect.log(`[${options.id}] Flow "${name}" stopped`)),
    );

  const closeAllFlowsEffect = Effect.gen(function* () {
    const activeFlows = Array.from(flows.entries());
    for (const [name, activeFlow] of activeFlows) {
      yield* closeFlowEffect(name, activeFlow);
    }
    flows.clear();
  });

  const closeConfigConsumerEffect = (): Effect.Effect<void> => {
    const consumer = configConsumer;
    configConsumer = null;
    if (consumer === null) {
      return Effect.void;
    }
    return Effect.tryPromise({
      try: () => consumer.close(),
      catch: (error) => pubSubError("close:config-push", error),
    }).pipe(
      Effect.catch((error) =>
        Effect.logError(`[${options.id}] Failed to close config consumer`, {
          error: error.message,
        }),
      ),
    );
  };

  const startFlowEffect = (
    name: string,
    definition: FlowDefinition,
  ): Effect.Effect<
    ActiveFlow,
    FlowRuntimeError,
    FlowRuntime | ProducerFactory | ConsumerFactory | RequestResponseFactory | FlowRequirements
  > =>
    Effect.gen(function* () {
      const flowRuntime = yield* FlowRuntime;
      const scope = yield* Scope.make();
      const flow = new Flow<FlowRequirements>(
        name,
        options.id,
        options.pubsub,
        definition,
        options.specifications,
      );
      return yield* flowRuntime.run(flow).pipe(
        Scope.provide(scope),
        Effect.as({ scope } satisfies ActiveFlow),
        Effect.catch((error) =>
          Scope.close(scope, Exit.void).pipe(
            Effect.flatMap(() => Effect.fail(error)),
          ),
        ),
      );
    });

  const onConfigureFlowsEffect = (
    config: Record<string, unknown>,
    _version: number,
  ): Effect.Effect<
    void,
    FlowRuntimeError,
    FlowRuntime | ProducerFactory | ConsumerFactory | RequestResponseFactory | FlowRequirements
  > =>
    Effect.gen(function* () {
      const flowDefs = config.flows;
      if (flowDefs === undefined) {
        yield* Effect.log(`[${options.id}] No flows in config push, skipping`);
        return;
      }
      const decodedFlowDefs = decodeFlowDefinitions(flowDefs);
      if (O.isNone(decodedFlowDefs)) {
        yield* Effect.logWarning(`[${options.id}] Skipping config push: flows is not an object`);
        return;
      }
      const flowDefinitions = decodedFlowDefs.value;

      const flowsJson = yield* S.encodeUnknownEffect(S.UnknownFromJsonString)(flowDefinitions).pipe(
        Effect.catch((error) => Effect.succeed(String(error))),
      );
      if (lastFlowsJson.length > 0 && flowsJson === lastFlowsJson && flows.size > 0) {
        yield* Effect.log(`[${options.id}] Flow definitions unchanged, skipping restart`);
        return;
      }
      lastFlowsJson = flowsJson;

      for (const [name, activeFlow] of flows) {
        if (!(name in flowDefinitions)) {
          yield* Effect.log(`[${options.id}] Stopping removed flow: ${name}`);
          yield* closeFlowEffect(name, activeFlow);
          flows.delete(name);
        }
      }

      for (const [name, defn] of Object.entries(flowDefinitions)) {
        const existing = flows.get(name);
        if (existing !== undefined) {
          yield* Effect.log(`[${options.id}] Restarting flow "${name}" with updated config`);
          yield* closeFlowEffect(name, existing);
          flows.delete(name);
        }

        yield* Effect.log(`[${options.id}] Starting flow "${name}"`);
        const activeFlow = yield* startFlowEffect(name, defn);
        flows.set(name, activeFlow);
        yield* Effect.log(`[${options.id}] Flow "${name}" started`);
      }
    });

  const processNextConfigPushEffect = (): Effect.Effect<
    void,
    never,
    | FlowRuntime
    | ProducerFactory
    | ConsumerFactory
    | RequestResponseFactory
    | FlowRequirements
    | ConfigHandlerRequirements
  > =>
    Effect.gen(function* () {
      const consumer = configConsumer;
      if (consumer === null) {
        yield* Effect.sleep(Duration.millis(1000));
        return;
      }

      const msg = yield* Effect.tryPromise({
        try: () => consumer.receive(2000),
        catch: (error) => pubSubError("receive:config-push", error),
      });
      if (msg === null) {
        return;
      }

      const push = msg.value();
      yield* Effect.log(`[${options.id}] Received config push version=${push.version}`);

      yield* onConfigureFlowsEffect(push.config, push.version);

      for (const handler of options.configHandlers ?? []) {
        yield* handler(push.config, push.version);
      }

      yield* Effect.tryPromise({
        try: () => consumer.acknowledge(msg),
        catch: (error) => pubSubError("acknowledge:config-push", error),
      });
    }).pipe(
      Effect.catch((error) => {
        if (!isRunning()) {
          return Effect.void;
        }
        return Effect.logError(`[${options.id}] Config consumer error`, {
          error: error instanceof Error ? error.message : String(error),
        }).pipe(
          Effect.flatMap(() => Effect.sleep(Duration.millis(1000))),
        );
      }),
    );

  return Effect.gen(function* () {
    const pubsub = yield* PubSub;

    configConsumer = yield* pubsub.createConsumer<ConfigPush>({
      topic: topics.configPush,
      subscription: `${options.id}-config-push`,
      initialPosition: "earliest",
      schema: ConfigPushSchema,
    });

    yield* Effect.addFinalizer(() =>
      closeConfigConsumerEffect().pipe(
        Effect.flatMap(() => closeAllFlowsEffect),
      ),
    );

    yield* Effect.log(`[${options.id}] Listening for config pushes on ${topics.configPush}`);

    yield* Effect.whileLoop({
      while: isRunning,
      body: processNextConfigPushEffect,
      step: () => undefined,
    });
  });
}

export function makeFlowProcessor<FlowRequirements = never>(
  config: ProcessorConfig,
  options: MakeFlowProcessorOptions<FlowRequirements> = {},
): FlowProcessorRuntime<FlowRequirements> {
  const specifications: Array<Spec<FlowRequirements>> = [
    ...(options.specifications ?? []),
  ];
  const compatibilityRuntime = ManagedRuntime.make(Layer.empty);
  let processor: FlowProcessorRuntime<FlowRequirements>;
  const base: AsyncProcessorRuntime<
    PubSubError | FlowRuntimeError | ProcessorLifecycleError,
    FlowProcessorRuntimeRequirements<FlowRequirements>
  > = makeAsyncProcessor(config, {
    runEffect: (runtime) => {
      const configHandlers = runtime.configHandlers.map(
        (handler): EffectConfigHandler<PubSubError> =>
          (pushedConfig, version) =>
            Effect.tryPromise({
              try: () => handler(pushedConfig, version),
              catch: (error) => pubSubError("config-handler", error),
            }),
      );
      return runFlowProcessorDefinitionScoped({
        id: runtime.config.id,
        pubsub: runtime.pubsub,
        specifications,
        configHandlers,
        isRunning: runtime.isRunning,
      });
    },
  });

  const makeStartEffect = (): FlowProcessorStartEffect<FlowRequirements> => {
    const effect = base.startEffect;
    return options.provide?.(effect) ?? effect;
  };

  processor = {
    ...base,
    specifications,
    registerSpecification: (spec) => {
      specifications.push(spec);
    },
    get startEffect() {
      return makeStartEffect();
    },
    start: (context) =>
      compatibilityRuntime.runPromise(Effect.provide(
        Effect.gen(function* () {
          const pubsub = makePubSubService(base.pubsub);
          const messagingConfig = yield* loadMessagingRuntimeConfig();
          const start = processor.startEffect.pipe(
            Effect.provideService(PubSub, pubsub),
            Effect.provideService(ProducerFactory, ProducerFactory.of(makeProducerFactoryService(pubsub))),
            Effect.provideService(ConsumerFactory, ConsumerFactory.of(makeConsumerFactoryService(pubsub, messagingConfig))),
            Effect.provideService(
              RequestResponseFactory,
              RequestResponseFactory.of(makeRequestResponseFactoryService(pubsub, messagingConfig)),
            ),
            Effect.provideService(FlowRuntime, FlowRuntime.of({ run: runFlowRuntimeScoped })),
          );
          yield* Effect.scoped(start);
        }),
        context,
      )),
  };

  return processor;
}

export type FlowProcessor<FlowRequirements = never> = FlowProcessorRuntime<FlowRequirements>;

export const FlowProcessor = makeFlowProcessor as unknown as {
  new <FlowRequirements = never>(
    config: ProcessorConfig,
  ): FlowProcessor<FlowRequirements>;
  <FlowRequirements = never>(
    config: ProcessorConfig,
  ): FlowProcessor<FlowRequirements>;
};
