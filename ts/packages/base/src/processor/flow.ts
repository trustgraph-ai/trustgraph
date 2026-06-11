/**
 * Runtime flow instance — created by FlowProcessor for each configured flow.
 *
 * Python reference: trustgraph-base/trustgraph/base/flow.py
 */

import type { Config as EffectConfig, Context, } from "effect";
import { Effect, Exit, Scope } from "effect";
import * as MutableHashMap from "effect/MutableHashMap";
import * as O from "effect/Option";
import * as S from "effect/Schema";
import type { PubSubBackend } from "../backend/types.js";
import { makePubSubService } from "../backend/pubsub.js";
import type {
  FlowParameterDecodeError,
  FlowResourceNotFoundError,
  MessagingDeliveryError,
  MessagingLifecycleError,
  MessagingTimeoutError,
  PubSubError,
} from "../errors.js";
import {
  flowParameterDecodeError,
  flowResourceNotFoundError,
} from "../errors.js";
import type {
  EffectConsumer,
  EffectProducer,
  EffectRequestOptions,
  EffectRequestResponse,
} from "../messaging/runtime.js";
import {
  ConsumerFactory,
  ProducerFactory,
  RequestResponseFactory,
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
  readonly send: (id: string, message: T) => Effect.Effect<void, MessagingDeliveryError>;
  readonly flush: Effect.Effect<void, MessagingDeliveryError>;
  readonly stop: Effect.Effect<void, MessagingDeliveryError>;
}

export interface FlowConsumer {
  readonly stop: Effect.Effect<void, MessagingLifecycleError>;
}

export interface FlowRequestOptions<TRes, E = never, R = never> {
  readonly timeoutMs?: number;
  readonly recipient?: (response: TRes) => Effect.Effect<boolean, E, R>;
}

export interface FlowRequestor<TReq, TRes> {
  readonly request: <E = never, R = never>(
    request: TReq,
    options?: FlowRequestOptions<TRes, E, R>,
  ) => Effect.Effect<TRes, MessagingDeliveryError | MessagingLifecycleError | MessagingTimeoutError | E, R>;
  readonly stop: Effect.Effect<void, MessagingLifecycleError | MessagingDeliveryError>;
}

type FlowParameterError = FlowResourceNotFoundError | FlowParameterDecodeError;

export interface Flow<Requirements = never> {
  readonly name: string;
  readonly processorId: string;
  startEffect: Effect.Effect<void, PubSubError, SpecRuntimeRequirements | Requirements>;
  start: (context: Context.Context<Requirements>) => Effect.Effect<void, PubSubError | EffectConfig.ConfigError>;
  stop: Effect.Effect<void>;
  stopEffect: Effect.Effect<void>;
  runInRuntimeScopeEffect: <A, E>(
    effect: Effect.Effect<A, E, SpecRuntimeRequirements | Requirements>,
    runtimePubsub: PubSubBackend,
    context: Context.Context<Requirements>,
  ) => Effect.Effect<A, E | EffectConfig.ConfigError>;
  clearResources: () => void;
  registerProducer: <T>(registerName: string, producer: EffectProducer<T>) => void;
  registerConsumer: (registerName: string, consumer: EffectConsumer) => void;
  registerRequestor: <TReq, TRes>(
    registerName: string,
    rr: EffectRequestResponse<TReq, TRes>,
  ) => void;
  setParameter: (parameterName: string, value: unknown) => void;
  producerEffect: {
    <T>(producerSpec: ProducerSpec<T>): Effect.Effect<EffectProducer<T>, FlowResourceNotFoundError>;
    (producerName: string): Effect.Effect<EffectProducer<never>, FlowResourceNotFoundError>;
  };
  consumerEffect: (consumerName: string) => Effect.Effect<EffectConsumer, FlowResourceNotFoundError>;
  requestorEffect: {
    <TReq, TRes>(
      requestorSpec: RequestResponseSpec<TReq, TRes>,
    ): Effect.Effect<EffectRequestResponse<TReq, TRes>, FlowResourceNotFoundError>;
    (requestorName: string): Effect.Effect<EffectRequestResponse<never, unknown>, FlowResourceNotFoundError>;
  };
  parameterEffect: {
    <T>(parameterSpec: ParameterSpec<T>): Effect.Effect<T, FlowParameterError>;
    (parameterName: string): Effect.Effect<unknown, FlowResourceNotFoundError>;
  };
  producer: {
    <T>(producerSpec: ProducerSpec<T>): Effect.Effect<FlowProducer<T>, FlowResourceNotFoundError>;
    (producerName: string): Effect.Effect<FlowProducer<never>, FlowResourceNotFoundError>;
  };
  consumer: (consumerName: string) => Effect.Effect<FlowConsumer, FlowResourceNotFoundError>;
  requestor: {
    <TReq, TRes>(
      requestorSpec: RequestResponseSpec<TReq, TRes>,
    ): Effect.Effect<FlowRequestor<TReq, TRes>, FlowResourceNotFoundError>;
    (requestorName: string): Effect.Effect<FlowRequestor<never, unknown>, FlowResourceNotFoundError>;
  };
  parameter: {
    <T>(parameterSpec: ParameterSpec<T>): T;
    (parameterName: string): unknown;
  };
}

export function makeFlow<Requirements = never>(
  name: string,
  processorId: string,
  pubsub: PubSubBackend,
  definition: FlowDefinition,
  specifications: ReadonlyArray<Spec<Requirements>>,
): Flow<Requirements> {
  const producers = MutableHashMap.empty<string, EffectProducer<never>>();
  const consumers = MutableHashMap.empty<string, EffectConsumer>();
  const requestors = MutableHashMap.empty<string, EffectRequestResponse<never, unknown>>();
  const parameters = MutableHashMap.empty<string, unknown>();
  let runtimeScope: Scope.Closeable | null = null;

  const ensureRuntimeScopeEffect = Effect.fn("Flow.ensureRuntimeScope")(function* () {
    if (runtimeScope !== null) {
      return runtimeScope;
    }
    const scope = yield* Scope.make();
    runtimeScope = scope;
    return scope;
  });

  const toEffectRequestOptions = <TRes, E, R>(
    options: FlowRequestOptions<TRes, E, R> | undefined,
  ): EffectRequestOptions<TRes, E, R> | undefined => {
    if (options === undefined) {
      return undefined;
    }
    const recipient = options.recipient;
    return {
      ...(options.timeoutMs === undefined ? {} : { timeoutMs: options.timeoutMs }),
      ...(recipient === undefined
        ? {}
        : {
            recipient,
          }),
    };
  };

  const getParameterEffect = (parameterName: string): Effect.Effect<unknown, FlowResourceNotFoundError> => {
    const value = O.getOrUndefined(MutableHashMap.get(parameters, parameterName));
    return value === undefined
      ? Effect.fail(flowResourceNotFoundError(name, "parameter", parameterName))
      : Effect.succeed(value);
  };

  const getParameter = (parameterName: string): unknown => {
    const value = O.getOrUndefined(MutableHashMap.get(parameters, parameterName));
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
    const producer = O.getOrUndefined(MutableHashMap.get(producers, producerName));
    return producer === undefined
      ? Effect.fail(flowResourceNotFoundError(name, "producer", producerName))
      : Effect.succeed(producer);
  };

  const getRequestorEffect = (
    requestorName: string,
  ): Effect.Effect<EffectRequestResponse<never, unknown>, FlowResourceNotFoundError> => {
    const requestor = O.getOrUndefined(MutableHashMap.get(requestors, requestorName));
    return requestor === undefined
      ? Effect.fail(flowResourceNotFoundError(name, "requestor", requestorName))
      : Effect.succeed(requestor);
  };

  const toFlowProducer = <T>(producer: EffectProducer<T>): FlowProducer<T> => ({
    send: producer.send,
    flush: producer.flush,
    stop: producer.flush.pipe(Effect.flatMap(() => producer.close)),
  });

  const toFlowRequestor = <TReq, TRes>(
    requestor: EffectRequestResponse<TReq, TRes>,
  ): FlowRequestor<TReq, TRes> => ({
    request: (request, options) =>
      requestor.request(
        request,
        toEffectRequestOptions(options),
      ),
    stop: requestor.stop,
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
    if (!MutableHashMap.has(producers, producer.name)) {
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
    if (!MutableHashMap.has(requestors, requestor.name)) {
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

  function producer<T>(producerSpec: ProducerSpec<T>): Effect.Effect<FlowProducer<T>, FlowResourceNotFoundError>;
  function producer(producerName: string): Effect.Effect<FlowProducer<never>, FlowResourceNotFoundError>;
  function producer<T>(producer: string | ProducerSpec<T>) {
    if (typeof producer === "string") {
      return getProducerEffect(producer).pipe(Effect.map(toFlowProducer));
    }
    return producer.producerEffect(flow).pipe(Effect.map(toFlowProducer));
  }

  function requestor<TReq, TRes>(
    requestorSpec: RequestResponseSpec<TReq, TRes>,
  ): Effect.Effect<FlowRequestor<TReq, TRes>, FlowResourceNotFoundError>;
  function requestor(requestorName: string): Effect.Effect<FlowRequestor<never, unknown>, FlowResourceNotFoundError>;
  function requestor<TReq, TRes>(
    requestor: string | RequestResponseSpec<TReq, TRes>,
  ) {
    if (typeof requestor === "string") {
      return getRequestorEffect(requestor).pipe(Effect.map(toFlowRequestor));
    }
    return requestor.requestorEffect(flow).pipe(Effect.map(toFlowRequestor));
  }

  const flow: Flow<Requirements> = {
    name,
    processorId,
    startEffect: Effect.gen(function* () {
      for (const spec of specifications) {
        yield* spec.addEffect(flow, definition);
      }
    }).pipe(Effect.withSpan("Flow.startEffect")),
    start(context: Context.Context<Requirements>): Effect.Effect<void, PubSubError | EffectConfig.ConfigError> {
      return Effect.gen(function* () {
        if (runtimeScope !== null) {
          yield* flow.stop;
        }
        yield* flow.runInRuntimeScopeEffect(flow.startEffect, pubsub, context);
      });
    },
    get stop() {
      return flow.stopEffect;
    },
    stopEffect: Effect.gen(function* () {
      const scope = runtimeScope;
      runtimeScope = null;
      if (scope !== null) {
        yield* Scope.close(scope, Exit.void);
      }
      flow.clearResources();
    }).pipe(Effect.withSpan("Flow.stopEffect")),
    runInRuntimeScopeEffect: Effect.fn("Flow.runInRuntimeScopeEffect")(function* <A, E>(
      effect: Effect.Effect<A, E, SpecRuntimeRequirements | Requirements>,
      runtimePubsub: PubSubBackend,
      context: Context.Context<Requirements>,
    ) {
      const scope = yield* ensureRuntimeScopeEffect();
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
    }),
    clearResources(): void {
      MutableHashMap.clear(producers);
      MutableHashMap.clear(consumers);
      MutableHashMap.clear(requestors);
      MutableHashMap.clear(parameters);
    },
    registerProducer<T>(registerName: string, producer: EffectProducer<T>): void {
      MutableHashMap.set(producers, registerName, producer);
    },
    registerConsumer(registerName: string, consumer: EffectConsumer): void {
      MutableHashMap.set(consumers, registerName, consumer);
    },
    registerRequestor<TReq, TRes>(registerName: string, rr: EffectRequestResponse<TReq, TRes>): void {
      MutableHashMap.set(requestors, registerName, rr);
    },
    setParameter(parameterName: string, value: unknown): void {
      MutableHashMap.set(parameters, parameterName, value);
    },
    producerEffect,
    consumerEffect(consumerName: string): Effect.Effect<EffectConsumer, FlowResourceNotFoundError> {
      const c = O.getOrUndefined(MutableHashMap.get(consumers, consumerName));
      return c === undefined
        ? Effect.fail(flowResourceNotFoundError(name, "consumer", consumerName))
        : Effect.succeed(c);
    },
    requestorEffect,
    parameterEffect,
    producer,
    consumer(consumerName: string): Effect.Effect<FlowConsumer, FlowResourceNotFoundError> {
      return flow.consumerEffect(consumerName).pipe(
        Effect.map((c) => ({
          stop: c.stop,
        })),
      );
    },
    requestor,
    parameter,
  };

  return flow;
}

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
