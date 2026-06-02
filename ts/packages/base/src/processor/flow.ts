/**
 * Runtime flow instance — created by FlowProcessor for each configured flow.
 *
 * Python reference: trustgraph-base/trustgraph/base/flow.py
 */

import { Context, Effect, Exit, Layer, ManagedRuntime, Scope } from "effect";
import * as O from "effect/Option";
import * as S from "effect/Schema";
import type { PubSubBackend } from "../backend/types.js";
import { makePubSubService } from "../backend/pubsub.js";
import {
  flowParameterDecodeError,
  flowResourceNotFoundError,
  type FlowParameterDecodeError,
  type FlowResourceNotFoundError,
  type PubSubError,
} from "../errors.js";
import {
  ConsumerFactory,
  ProducerFactory,
  RequestResponseFactory,
  type EffectConsumer,
  type EffectProducer,
  type EffectRequestOptions,
  type EffectRequestResponse,
  makeConsumerFactoryService,
  makeProducerFactoryService,
  makeRequestResponseFactoryService,
} from "../messaging/runtime.js";
import { loadMessagingRuntimeConfig } from "../runtime/messaging-config.js";
import type { ParameterSpec } from "../spec/parameter-spec.js";
import type { ProducerSpec } from "../spec/producer-spec.js";
import type { RequestResponseSpec } from "../spec/request-response-spec.js";
import type { Spec, SpecRuntimeRequirements } from "../spec/types.js";

export interface FlowDefinition {
  /** Topic overrides keyed by spec name */
  topics?: Record<string, string>;
  /** Parameter values keyed by spec name */
  parameters?: Record<string, unknown>;
}

export interface FlowProducer<T> {
  readonly send: (id: string, message: T) => Promise<void>;
  readonly flush: () => Promise<void>;
  readonly stop: () => Promise<void>;
}

export interface FlowConsumer {
  readonly stop: () => Promise<void>;
}

export interface FlowRequestOptions<TRes> {
  readonly timeoutMs?: number;
  readonly recipient?: (response: TRes) => Promise<boolean>;
}

export interface FlowRequestor<TReq, TRes> {
  readonly request: (
    request: TReq,
    options?: FlowRequestOptions<TRes>,
  ) => Promise<TRes>;
  readonly stop: () => Promise<void>;
}

type FlowParameterError = FlowResourceNotFoundError | FlowParameterDecodeError;

export function makeFlow<Requirements = never>(
  name: string,
  processorId: string,
  pubsub: PubSubBackend,
  definition: FlowDefinition,
  specifications: ReadonlyArray<Spec<Requirements>>,
) {
  const producers = new Map<string, EffectProducer<never>>();
  const consumers = new Map<string, EffectConsumer>();
  const requestors = new Map<string, EffectRequestResponse<never, unknown>>();
  const parameters = new Map<string, unknown>();
  let compatibilityScope: Scope.Closeable | null = null;
  const compatibilityRuntime = ManagedRuntime.make(Layer.empty);

  const ensureCompatibilityScopeEffect = Effect.fn("Flow.ensureCompatibilityScope")(function* () {
    if (compatibilityScope !== null) {
      return compatibilityScope;
    }
    const scope = yield* Scope.make();
    compatibilityScope = scope;
    return scope;
  });

  const toEffectRequestOptions = <TRes>(
    options: FlowRequestOptions<TRes> | undefined,
  ): EffectRequestOptions<TRes> | undefined => {
    if (options === undefined) {
      return undefined;
    }
    const recipient = options.recipient;
    return {
      ...(options.timeoutMs === undefined ? {} : { timeoutMs: options.timeoutMs }),
      ...(recipient === undefined
        ? {}
        : {
            recipient: (response: TRes) => Effect.promise(() => recipient(response)),
          }),
    };
  };

  const getParameterEffect = (parameterName: string): Effect.Effect<unknown, FlowResourceNotFoundError> => {
    const value = parameters.get(parameterName);
    return value === undefined
      ? Effect.fail(flowResourceNotFoundError(name, "parameter", parameterName))
      : Effect.succeed(value);
  };

  const getParameter = (parameterName: string): unknown => {
    const value = parameters.get(parameterName);
    if (value === undefined) throw flowResourceNotFoundError(name, "parameter", parameterName);
    return value;
  };

  const decodeParameterEffect = <T>(
    spec: ParameterSpec<T>,
    value: unknown,
  ): Effect.Effect<T, FlowParameterDecodeError> =>
    S.decodeUnknownEffect(spec.schema)(value).pipe(
      Effect.mapError((error) => flowParameterDecodeError(name, spec.name, error)),
    );

  const decodeParameter = <T>(spec: ParameterSpec<T>, value: unknown): T => {
    const decoded = S.decodeUnknownOption(spec.schema)(value);
    if (O.isSome(decoded)) return decoded.value;
    throw flowParameterDecodeError(name, spec.name, "Parameter value does not match schema");
  };

  const getProducerEffect = (
    producerName: string,
  ): Effect.Effect<EffectProducer<never>, FlowResourceNotFoundError> => {
    const producer = producers.get(producerName);
    return producer === undefined
      ? Effect.fail(flowResourceNotFoundError(name, "producer", producerName))
      : Effect.succeed(producer);
  };

  const getProducer = (producerName: string): EffectProducer<never> => {
    const producer = producers.get(producerName);
    if (producer === undefined) throw flowResourceNotFoundError(name, "producer", producerName);
    return producer;
  };

  const getRequestorEffect = (
    requestorName: string,
  ): Effect.Effect<EffectRequestResponse<never, unknown>, FlowResourceNotFoundError> => {
    const requestor = requestors.get(requestorName);
    return requestor === undefined
      ? Effect.fail(flowResourceNotFoundError(name, "requestor", requestorName))
      : Effect.succeed(requestor);
  };

  const getRequestor = (
    requestorName: string,
  ): EffectRequestResponse<never, unknown> => {
    const requestor = requestors.get(requestorName);
    if (requestor === undefined) throw flowResourceNotFoundError(name, "requestor", requestorName);
    return requestor;
  };

  const toFlowProducer = <T>(producer: EffectProducer<T>): FlowProducer<T> => ({
    send: (id, message) => compatibilityRuntime.runPromise(producer.send(id, message)),
    flush: () => compatibilityRuntime.runPromise(producer.flush),
    stop: () => compatibilityRuntime.runPromise(producer.flush.pipe(Effect.flatMap(() => producer.close))),
  });

  const toFlowRequestor = <TReq, TRes>(
    requestor: EffectRequestResponse<TReq, TRes>,
  ): FlowRequestor<TReq, TRes> => ({
    request: (request, options) =>
      compatibilityRuntime.runPromise(
        requestor.request(
          request,
          toEffectRequestOptions(options),
        ),
      ),
    stop: () => compatibilityRuntime.runPromise(requestor.stop),
  });

  function producerEffect<T>(
    producerSpec: ProducerSpec<T>,
  ): Effect.Effect<EffectProducer<T>, FlowResourceNotFoundError>;
  function producerEffect(
    producerName: string,
  ): Effect.Effect<EffectProducer<never>, FlowResourceNotFoundError>;
  function producerEffect<T>(
    producer: string | ProducerSpec<T>,
  ) {
    if (typeof producer === "string") {
      return getProducerEffect(producer);
    }
    if (!producers.has(producer.name)) {
      return Effect.fail(flowResourceNotFoundError(name, "producer", producer.name));
    }
    return producer.producerEffect(flow);
  }

  function requestorEffect<TReq, TRes>(
    requestorSpec: RequestResponseSpec<TReq, TRes>,
  ): Effect.Effect<EffectRequestResponse<TReq, TRes>, FlowResourceNotFoundError>;
  function requestorEffect(
    requestorName: string,
  ): Effect.Effect<EffectRequestResponse<never, unknown>, FlowResourceNotFoundError>;
  function requestorEffect<TReq, TRes>(
    requestor: string | RequestResponseSpec<TReq, TRes>,
  ) {
    if (typeof requestor === "string") {
      return getRequestorEffect(requestor);
    }
    if (!requestors.has(requestor.name)) {
      return Effect.fail(flowResourceNotFoundError(name, "requestor", requestor.name));
    }
    return requestor.requestorEffect(flow);
  }

  function parameterEffect<T>(
    parameterSpec: ParameterSpec<T>,
  ): Effect.Effect<T, FlowParameterError>;
  function parameterEffect(
    parameterName: string,
  ): Effect.Effect<unknown, FlowResourceNotFoundError>;
  function parameterEffect<T>(
    parameter: string | ParameterSpec<T>,
  ): Effect.Effect<unknown, FlowParameterError> {
    if (typeof parameter === "string") {
      return getParameterEffect(parameter);
    }
    return getParameterEffect(parameter.name).pipe(
      Effect.flatMap((value) => decodeParameterEffect(parameter, value)),
    );
  }

  function parameter<T>(parameterSpec: ParameterSpec<T>): T;
  function parameter(parameterName: string): unknown;
  function parameter<T>(parameter: string | ParameterSpec<T>): unknown {
    const value = getParameter(typeof parameter === "string" ? parameter : parameter.name);
    if (typeof parameter === "string") {
      return value;
    }
    return decodeParameter(parameter, value);
  }

  function producer<T>(producerSpec: ProducerSpec<T>): FlowProducer<T>;
  function producer(producerName: string): FlowProducer<never>;
  function producer<T>(producer: string | ProducerSpec<T>) {
    if (typeof producer === "string") {
      return toFlowProducer(getProducer(producer));
    }
    if (!producers.has(producer.name)) {
      throw flowResourceNotFoundError(name, "producer", producer.name);
    }
    return toFlowProducer(compatibilityRuntime.runSync(producer.producerEffect(flow)));
  }

  function requestor<TReq, TRes>(
    requestorSpec: RequestResponseSpec<TReq, TRes>,
  ): FlowRequestor<TReq, TRes>;
  function requestor(requestorName: string): FlowRequestor<never, unknown>;
  function requestor<TReq, TRes>(
    requestor: string | RequestResponseSpec<TReq, TRes>,
  ) {
    if (typeof requestor === "string") {
      return toFlowRequestor(getRequestor(requestor));
    }
    if (!requestors.has(requestor.name)) {
      throw flowResourceNotFoundError(name, "requestor", requestor.name);
    }
    return toFlowRequestor(compatibilityRuntime.runSync(requestor.requestorEffect(flow)));
  }

  const flow = {
    name,
    processorId,
    startEffect(): Effect.Effect<void, PubSubError, SpecRuntimeRequirements | Requirements> {
      return Effect.gen(function* () {
        for (const spec of specifications) {
          yield* spec.addEffect(flow, definition);
        }
      });
    },
    start(context: Context.Context<Requirements>): Promise<void> {
      return compatibilityRuntime.runPromise(
        Effect.gen(function* () {
          if (compatibilityScope !== null) {
            yield* flow.stopEffect();
          }
          yield* flow.runInCompatibilityScopeEffect(flow.startEffect(), pubsub, context);
        }),
      );
    },
    stop(): Promise<void> {
      return compatibilityRuntime.runPromise(flow.stopEffect());
    },
    stopEffect(): Effect.Effect<void> {
      return Effect.gen(function* () {
        const scope = compatibilityScope;
        compatibilityScope = null;
        if (scope !== null) {
          yield* Scope.close(scope, Exit.void);
        }
        flow.clearResources();
      });
    },
    runInCompatibilityScopeEffect<A, E>(
      effect: Effect.Effect<A, E, SpecRuntimeRequirements | Requirements>,
      runtimePubsub: PubSubBackend,
      context: Context.Context<Requirements>,
    ) {
      return Effect.gen(function* () {
        const scope = yield* ensureCompatibilityScopeEffect();
        const pubsubService = makePubSubService(runtimePubsub);
        const messagingConfig = yield* loadMessagingRuntimeConfig();
        return yield* Effect.provide(
          effect.pipe(
            Effect.provideService(ProducerFactory, ProducerFactory.of(makeProducerFactoryService(pubsubService))),
            Effect.provideService(ConsumerFactory, ConsumerFactory.of(makeConsumerFactoryService(pubsubService, messagingConfig))),
            Effect.provideService(
              RequestResponseFactory,
              RequestResponseFactory.of(makeRequestResponseFactoryService(pubsubService, messagingConfig)),
            ),
            Scope.provide(scope),
          ),
          context,
        );
      });
    },
    runInCompatibilityScope<A, E>(
      effect: Effect.Effect<A, E, SpecRuntimeRequirements | Requirements>,
      runtimePubsub: PubSubBackend,
      context: Context.Context<Requirements>,
    ): Promise<A> {
      return compatibilityRuntime.runPromise(flow.runInCompatibilityScopeEffect(effect, runtimePubsub, context));
    },
    clearResources(): void {
      producers.clear();
      consumers.clear();
      requestors.clear();
      parameters.clear();
    },
    registerProducer<T>(registerName: string, producer: EffectProducer<T>): void {
      producers.set(registerName, producer);
    },
    registerConsumer(registerName: string, consumer: EffectConsumer): void {
      consumers.set(registerName, consumer);
    },
    registerRequestor<TReq, TRes>(registerName: string, rr: EffectRequestResponse<TReq, TRes>): void {
      requestors.set(registerName, rr);
    },
    setParameter(parameterName: string, value: unknown): void {
      parameters.set(parameterName, value);
    },
    producerEffect,
    consumerEffect(consumerName: string): Effect.Effect<EffectConsumer, FlowResourceNotFoundError> {
      const c = consumers.get(consumerName);
      return c === undefined
        ? Effect.fail(flowResourceNotFoundError(name, "consumer", consumerName))
        : Effect.succeed(c);
    },
    requestorEffect,
    parameterEffect,
    producer,
    consumer(consumerName: string): FlowConsumer {
      const c = consumers.get(consumerName);
      if (c === undefined) throw flowResourceNotFoundError(name, "consumer", consumerName);
      return {
        stop: () => compatibilityRuntime.runPromise(c.stop),
      };
    },
    requestor,
    parameter,
  };

  return flow;
}

export type Flow<Requirements = never> = ReturnType<typeof makeFlow<Requirements>>;

export const Flow = makeFlow as unknown as {
  new <Requirements = never>(
    name: string,
    processorId: string,
    pubsub: PubSubBackend,
    definition: FlowDefinition,
    specifications: ReadonlyArray<Spec<Requirements>>,
  ): Flow<Requirements>;
  <Requirements = never>(
    name: string,
    processorId: string,
    pubsub: PubSubBackend,
    definition: FlowDefinition,
    specifications: ReadonlyArray<Spec<Requirements>>,
  ): Flow<Requirements>;
};
