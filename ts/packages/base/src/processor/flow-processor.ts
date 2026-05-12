/**
 * Flow-aware processor that manages dynamic flow instances.
 *
 * Subscribes to config-push topic and dynamically creates/destroys
 * flow instances based on the configuration received.
 *
 * Python reference: trustgraph-base/trustgraph/base/flow_processor.py
 */

import { AsyncProcessor, type ProcessorConfig } from "./async-processor.js";
import type { Spec } from "../spec/types.js";
import type { BackendConsumer } from "../backend/types.js";
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
import { Duration, Effect, Exit, Scope } from "effect";
import * as S from "effect/Schema";

interface ConfigPush {
  version: number;
  config: Record<string, unknown>;
}

interface ActiveFlow {
  readonly scope: Scope.Closeable;
}

const ConfigPushSchema = S.Struct({
  version: S.Number,
  config: S.Record(S.String, S.Unknown),
});

export abstract class FlowProcessor<FlowRequirements = never> extends AsyncProcessor<
  PubSubError | FlowRuntimeError | ProcessorLifecycleError,
  | PubSub
  | FlowRuntime
  | ProducerFactory
  | ConsumerFactory
  | RequestResponseFactory
  | Scope.Scope
  | FlowRequirements
> {
  private specifications: Array<Spec<FlowRequirements>> = [];
  private flows = new Map<string, ActiveFlow>();
  private configConsumer: BackendConsumer<ConfigPush> | null = null;
  private lastFlowsJson = "";

  protected constructor(config: ProcessorConfig) {
    super(config);
  }

  registerSpecification<Requirements extends FlowRequirements>(
    spec: Spec<Requirements>,
  ): void {
    this.specifications.push(spec as Spec<FlowRequirements>);
  }

  override async start(): Promise<void> {
    const pubsub = makePubSubService(this.pubsub);
    const messagingConfig = await Effect.runPromise(loadMessagingRuntimeConfig());
    const start = this.startEffect().pipe(
      Effect.provideService(PubSub, pubsub),
      Effect.provideService(ProducerFactory, ProducerFactory.of(makeProducerFactoryService(pubsub))),
      Effect.provideService(ConsumerFactory, ConsumerFactory.of(makeConsumerFactoryService(pubsub, messagingConfig))),
      Effect.provideService(
        RequestResponseFactory,
        RequestResponseFactory.of(makeRequestResponseFactoryService(pubsub, messagingConfig)),
      ),
      Effect.provideService(FlowRuntime, FlowRuntime.of({ run: runFlowRuntimeScoped })),
    ) as Effect.Effect<void, PubSubError | FlowRuntimeError | ProcessorLifecycleError>;
    await Effect.runPromise(
      Effect.scoped(
        start,
      ),
    );
  }

  protected override runEffect(): Effect.Effect<
    void,
    PubSubError | FlowRuntimeError | ProcessorLifecycleError,
    | PubSub
    | FlowRuntime
    | ProducerFactory
    | ConsumerFactory
    | RequestResponseFactory
    | Scope.Scope
    | FlowRequirements
  > {
    const processor = this;
    return Effect.gen(function* () {
      const pubsub = yield* PubSub;

      // Subscribe to config-push topic to receive flow definitions.
      // Use "earliest" to replay any config pushes that arrived before this service started.
      processor.configConsumer = yield* pubsub.createConsumer<ConfigPush>({
        topic: topics.configPush,
        subscription: `${processor.config.id}-config-push`,
        initialPosition: "earliest",
        schema: ConfigPushSchema,
      });

      yield* Effect.addFinalizer(() =>
        processor.closeConfigConsumerEffect().pipe(
          Effect.flatMap(() => processor.closeAllFlowsEffect()),
        ),
      );

      yield* Effect.log(`[${processor.config.id}] Listening for config pushes on ${topics.configPush}`);

      yield* Effect.whileLoop({
        while: () => processor.running,
        body: () => processor.processNextConfigPushEffect(),
        step: () => undefined,
      });
    });
  }

  private onConfigureFlowsEffect(
    config: Record<string, unknown>,
    _version: number,
  ): Effect.Effect<
    void,
    FlowRuntimeError,
    FlowRuntime | ProducerFactory | ConsumerFactory | RequestResponseFactory | FlowRequirements
  > {
    const processor = this;
    return Effect.gen(function* () {
      const flowDefs = config.flows as Record<string, FlowDefinition> | undefined;
      if (flowDefs === undefined) {
        yield* Effect.log(`[${processor.config.id}] No flows in config push, skipping`);
        return;
      }

      // Skip flow restart if the flow definitions haven't changed.
      // This prevents disrupting in-flight requests when non-flow config
      // sections (prompts, tools, mcp) are updated.
      const flowsJson = yield* S.encodeUnknownEffect(S.UnknownFromJsonString)(flowDefs).pipe(
        Effect.catch((error) => Effect.succeed(String(error))),
      );
      if (processor.lastFlowsJson.length > 0 && flowsJson === processor.lastFlowsJson && processor.flows.size > 0) {
        yield* Effect.log(`[${processor.config.id}] Flow definitions unchanged, skipping restart`);
        return;
      }
      processor.lastFlowsJson = flowsJson;

      // Stop removed flows
      for (const [name, activeFlow] of processor.flows) {
        if (!(name in flowDefs)) {
          yield* Effect.log(`[${processor.config.id}] Stopping removed flow: ${name}`);
          yield* processor.closeFlowEffect(name, activeFlow);
          processor.flows.delete(name);
        }
      }

      // Start or update flows
      for (const [name, defn] of Object.entries(flowDefs)) {
        // Skip invalid definitions (e.g., stringified JSON)
        if (typeof defn !== "object" || defn === null) {
          yield* Effect.logWarning(`[${processor.config.id}] Skipping flow "${name}": definition is not an object`);
          continue;
        }

        // Stop existing flow before (re)starting with new config
        const existing = processor.flows.get(name);
        if (existing !== undefined) {
          yield* Effect.log(`[${processor.config.id}] Restarting flow "${name}" with updated config`);
          yield* processor.closeFlowEffect(name, existing);
          processor.flows.delete(name);
        }

        yield* Effect.log(`[${processor.config.id}] Starting flow "${name}"`);
        const activeFlow = yield* processor.startFlowEffect(name, defn);
        processor.flows.set(name, activeFlow);
        yield* Effect.log(`[${processor.config.id}] Flow "${name}" started`);
      }
    });
  }

  override stopEffect(): Effect.Effect<void, ProcessorLifecycleError> {
    return this.closeConfigConsumerEffect().pipe(
      Effect.flatMap(() => this.closeAllFlowsEffect()),
      Effect.flatMap(() => super.stopEffect()),
    );
  }

  private processNextConfigPushEffect(): Effect.Effect<
    void,
    never,
    FlowRuntime | ProducerFactory | ConsumerFactory | RequestResponseFactory | FlowRequirements
  > {
    const processor = this;
    return Effect.gen(function* () {
      const consumer = processor.configConsumer;
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
      yield* Effect.log(`[${processor.config.id}] Received config push version=${push.version}`);

      yield* processor.onConfigureFlowsEffect(push.config, push.version);

      for (const handler of processor.configHandlers) {
        yield* Effect.tryPromise({
          try: () => handler(push.config, push.version),
          catch: (error) => pubSubError("config-handler", error),
        });
      }

      yield* Effect.tryPromise({
        try: () => consumer.acknowledge(msg),
        catch: (error) => pubSubError("acknowledge:config-push", error),
      });
    }).pipe(
      Effect.catch((error) => {
        if (!processor.running) {
          return Effect.void;
        }
        return Effect.logError(`[${processor.config.id}] Config consumer error`, {
          error: error.message,
        }).pipe(
          Effect.flatMap(() => Effect.sleep(Duration.millis(1000))),
        );
      }),
    );
  }

  private startFlowEffect(
    name: string,
    definition: FlowDefinition,
  ): Effect.Effect<
    ActiveFlow,
    FlowRuntimeError,
    FlowRuntime | ProducerFactory | ConsumerFactory | RequestResponseFactory | FlowRequirements
  > {
    const processor = this;
    return Effect.gen(function* () {
      const flowRuntime = yield* FlowRuntime;
      const scope = yield* Scope.make();
      const flow = new Flow<FlowRequirements>(
        name,
        processor.config.id,
        processor.pubsub,
        definition,
        processor.specifications,
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
  }

  private closeFlowEffect(name: string, activeFlow: ActiveFlow): Effect.Effect<void> {
    return Scope.close(activeFlow.scope, Exit.void).pipe(
      Effect.tap(() => Effect.log(`[${this.config.id}] Flow "${name}" stopped`)),
    );
  }

  private closeAllFlowsEffect(): Effect.Effect<void> {
    const processor = this;
    return Effect.gen(function* () {
      const flows = Array.from(processor.flows.entries());
      for (const [name, activeFlow] of flows) {
        yield* processor.closeFlowEffect(name, activeFlow);
      }
      processor.flows.clear();
    });
  }

  private closeConfigConsumerEffect(): Effect.Effect<void> {
    const consumer = this.configConsumer;
    this.configConsumer = null;
    if (consumer === null) {
      return Effect.void;
    }
    return Effect.tryPromise({
      try: () => consumer.close(),
      catch: (error) => pubSubError("close:config-push", error),
    }).pipe(
      Effect.catch((error) =>
        Effect.logError(`[${this.config.id}] Failed to close config consumer`, {
          error: error.message,
        }),
      ),
    );
  }
}
