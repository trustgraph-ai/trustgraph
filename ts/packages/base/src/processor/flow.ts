/**
 * Runtime flow instance — created by FlowProcessor for each configured flow.
 *
 * Python reference: trustgraph-base/trustgraph/base/flow.py
 */

import { Effect, Exit, Scope } from "effect";
import type { PubSubBackend } from "../backend/types.js";
import { makePubSubService } from "../backend/pubsub.js";
import {
  flowResourceNotFoundError,
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

export function makeFlow<Requirements = never>(
  name: string,
  processorId: string,
  pubsub: PubSubBackend,
  definition: FlowDefinition,
  specifications: ReadonlyArray<Spec<Requirements>>,
) {
  const producers = new Map<string, EffectProducer<unknown>>();
  const consumers = new Map<string, EffectConsumer>();
  const requestors = new Map<string, EffectRequestResponse<unknown, unknown>>();
  const parameters = new Map<string, unknown>();
  let compatibilityScope: Scope.Closeable | null = null;

  const ensureCompatibilityScope = async (): Promise<Scope.Closeable> => {
    if (compatibilityScope !== null) {
      return compatibilityScope;
    }
    compatibilityScope = await Effect.runPromise(Scope.make());
    return compatibilityScope;
  };

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
    async start(): Promise<void> {
      if (compatibilityScope !== null) {
        await flow.stop();
      }
      await flow.runInCompatibilityScope(
        flow.startEffect() as Effect.Effect<void, PubSubError, SpecRuntimeRequirements>,
        pubsub,
      );
    },
    async stop(): Promise<void> {
      const scope = compatibilityScope;
      compatibilityScope = null;
      if (scope !== null) {
        await Effect.runPromise(Scope.close(scope, Exit.void));
      }
      flow.clearResources();
    },
    async runInCompatibilityScope<A, E>(
      effect: Effect.Effect<A, E, SpecRuntimeRequirements>,
      runtimePubsub: PubSubBackend,
    ): Promise<A> {
      const scope = await ensureCompatibilityScope();
      const pubsubService = makePubSubService(runtimePubsub);
      const messagingConfig = await Effect.runPromise(loadMessagingRuntimeConfig());
      return await Effect.runPromise(
        effect.pipe(
          Effect.provideService(ProducerFactory, ProducerFactory.of(makeProducerFactoryService(pubsubService))),
          Effect.provideService(ConsumerFactory, ConsumerFactory.of(makeConsumerFactoryService(pubsubService, messagingConfig))),
          Effect.provideService(
            RequestResponseFactory,
            RequestResponseFactory.of(makeRequestResponseFactoryService(pubsubService, messagingConfig)),
          ),
          Scope.provide(scope),
        ),
      );
    },
    clearResources(): void {
      producers.clear();
      consumers.clear();
      requestors.clear();
      parameters.clear();
    },
    registerProducer(registerName: string, producer: EffectProducer<unknown>): void {
      producers.set(registerName, producer);
    },
    registerConsumer(registerName: string, consumer: EffectConsumer): void {
      consumers.set(registerName, consumer);
    },
    registerRequestor(registerName: string, rr: EffectRequestResponse<unknown, unknown>): void {
      requestors.set(registerName, rr);
    },
    setParameter(parameterName: string, value: unknown): void {
      parameters.set(parameterName, value);
    },
    producerEffect<T>(producerName: string): Effect.Effect<EffectProducer<T>, FlowResourceNotFoundError> {
      const p = producers.get(producerName);
      return p === undefined
        ? Effect.fail(flowResourceNotFoundError(name, "producer", producerName))
        : Effect.succeed(p as EffectProducer<T>);
    },
    consumerEffect(consumerName: string): Effect.Effect<EffectConsumer, FlowResourceNotFoundError> {
      const c = consumers.get(consumerName);
      return c === undefined
        ? Effect.fail(flowResourceNotFoundError(name, "consumer", consumerName))
        : Effect.succeed(c);
    },
    requestorEffect<TReq, TRes>(
      requestorName: string,
    ): Effect.Effect<EffectRequestResponse<TReq, TRes>, FlowResourceNotFoundError> {
      const rr = requestors.get(requestorName);
      return rr === undefined
        ? Effect.fail(flowResourceNotFoundError(name, "requestor", requestorName))
        : Effect.succeed(rr as EffectRequestResponse<TReq, TRes>);
    },
    parameterEffect<T>(parameterName: string): Effect.Effect<T, FlowResourceNotFoundError> {
      const v = parameters.get(parameterName);
      return v === undefined
        ? Effect.fail(flowResourceNotFoundError(name, "parameter", parameterName))
        : Effect.succeed(v as T);
    },
    producer<T>(producerName: string): FlowProducer<T> {
      const p = producers.get(producerName);
      if (p === undefined) throw flowResourceNotFoundError(name, "producer", producerName);
      return {
        send: (id, message) => Effect.runPromise((p as EffectProducer<T>).send(id, message)),
        flush: () => Effect.runPromise(p.flush),
        stop: () => Effect.runPromise(p.flush.pipe(Effect.flatMap(() => p.close))),
      };
    },
    consumer(consumerName: string): FlowConsumer {
      const c = consumers.get(consumerName);
      if (c === undefined) throw flowResourceNotFoundError(name, "consumer", consumerName);
      return {
        stop: () => Effect.runPromise(c.stop),
      };
    },
    requestor<TReq, TRes>(requestorName: string): FlowRequestor<TReq, TRes> {
      const rr = requestors.get(requestorName);
      if (rr === undefined) throw flowResourceNotFoundError(name, "requestor", requestorName);
      return {
        request: (request, options) =>
          Effect.runPromise(
            (rr as EffectRequestResponse<TReq, TRes>).request(
              request,
              toEffectRequestOptions(options),
            ),
          ),
        stop: () => Effect.runPromise(rr.stop),
      };
    },
    parameter<T>(parameterName: string): T {
      const v = parameters.get(parameterName);
      if (v === undefined) throw flowResourceNotFoundError(name, "parameter", parameterName);
      return v as T;
    },
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
