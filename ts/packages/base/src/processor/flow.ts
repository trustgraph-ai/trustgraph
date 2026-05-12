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

export class Flow<Requirements = never> {
  private producers = new Map<string, EffectProducer<unknown>>();
  private consumers = new Map<string, EffectConsumer>();
  private requestors = new Map<string, EffectRequestResponse<unknown, unknown>>();
  private parameters = new Map<string, unknown>();
  private compatibilityScope: Scope.Closeable | null = null;
  public readonly name: string;
  public readonly processorId: string;
  private readonly pubsub: PubSubBackend;
  private readonly definition: FlowDefinition;
  private readonly specifications: ReadonlyArray<Spec<Requirements>>;

  constructor(
    name: string,
    processorId: string,
    pubsub: PubSubBackend,
    definition: FlowDefinition,
    specifications: ReadonlyArray<Spec<Requirements>>,
  ) {
    this.name = name;
    this.processorId = processorId;
    this.pubsub = pubsub;
    this.definition = definition;
    this.specifications = specifications;
  }

  startEffect(): Effect.Effect<void, PubSubError, SpecRuntimeRequirements | Requirements> {
    const flow = this;
    return Effect.gen(function* () {
      for (const spec of flow.specifications) {
        yield* spec.addEffect(flow, flow.definition);
      }
    });
  }

  async start(): Promise<void> {
    if (this.compatibilityScope !== null) {
      await this.stop();
    }
    await this.runInCompatibilityScope(
      this.startEffect() as Effect.Effect<void, PubSubError, SpecRuntimeRequirements>,
      this.pubsub,
    );
  }

  async stop(): Promise<void> {
    const scope = this.compatibilityScope;
    this.compatibilityScope = null;
    if (scope !== null) {
      await Effect.runPromise(Scope.close(scope, Exit.void));
    }
    this.clearResources();
  }

  async runInCompatibilityScope<A, E>(
    effect: Effect.Effect<A, E, SpecRuntimeRequirements>,
    pubsub: PubSubBackend,
  ): Promise<A> {
    const scope = await this.ensureCompatibilityScope();
    const pubsubService = makePubSubService(pubsub);
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
  }

  clearResources(): void {
    this.producers.clear();
    this.consumers.clear();
    this.requestors.clear();
    this.parameters.clear();
  }

  registerProducer(name: string, producer: EffectProducer<unknown>): void {
    this.producers.set(name, producer);
  }

  registerConsumer(name: string, consumer: EffectConsumer): void {
    this.consumers.set(name, consumer);
  }

  registerRequestor(name: string, rr: EffectRequestResponse<unknown, unknown>): void {
    this.requestors.set(name, rr);
  }

  setParameter(name: string, value: unknown): void {
    this.parameters.set(name, value);
  }

  producerEffect<T>(name: string): Effect.Effect<EffectProducer<T>, FlowResourceNotFoundError> {
    const p = this.producers.get(name);
    return p === undefined
      ? Effect.fail(flowResourceNotFoundError(this.name, "producer", name))
      : Effect.succeed(p as EffectProducer<T>);
  }

  consumerEffect(name: string): Effect.Effect<EffectConsumer, FlowResourceNotFoundError> {
    const c = this.consumers.get(name);
    return c === undefined
      ? Effect.fail(flowResourceNotFoundError(this.name, "consumer", name))
      : Effect.succeed(c);
  }

  requestorEffect<TReq, TRes>(
    name: string,
  ): Effect.Effect<EffectRequestResponse<TReq, TRes>, FlowResourceNotFoundError> {
    const rr = this.requestors.get(name);
    return rr === undefined
      ? Effect.fail(flowResourceNotFoundError(this.name, "requestor", name))
      : Effect.succeed(rr as EffectRequestResponse<TReq, TRes>);
  }

  parameterEffect<T>(name: string): Effect.Effect<T, FlowResourceNotFoundError> {
    const v = this.parameters.get(name);
    return v === undefined
      ? Effect.fail(flowResourceNotFoundError(this.name, "parameter", name))
      : Effect.succeed(v as T);
  }

  producer<T>(name: string): FlowProducer<T> {
    const p = this.producers.get(name);
    if (p === undefined) throw flowResourceNotFoundError(this.name, "producer", name);
    return {
      send: (id, message) => Effect.runPromise((p as EffectProducer<T>).send(id, message)),
      flush: () => Effect.runPromise(p.flush),
      stop: () => Effect.runPromise(p.flush.pipe(Effect.flatMap(() => p.close))),
    };
  }

  consumer(name: string): FlowConsumer {
    const c = this.consumers.get(name);
    if (c === undefined) throw flowResourceNotFoundError(this.name, "consumer", name);
    return {
      stop: () => Effect.runPromise(c.stop),
    };
  }

  requestor<TReq, TRes>(name: string): FlowRequestor<TReq, TRes> {
    const rr = this.requestors.get(name);
    if (rr === undefined) throw flowResourceNotFoundError(this.name, "requestor", name);
    return {
      request: (request, options) =>
        Effect.runPromise(
          (rr as EffectRequestResponse<TReq, TRes>).request(
            request,
            this.toEffectRequestOptions(options),
          ),
        ),
      stop: () => Effect.runPromise(rr.stop),
    };
  }

  parameter<T>(name: string): T {
    const v = this.parameters.get(name);
    if (v === undefined) throw flowResourceNotFoundError(this.name, "parameter", name);
    return v as T;
  }

  private async ensureCompatibilityScope(): Promise<Scope.Closeable> {
    if (this.compatibilityScope !== null) {
      return this.compatibilityScope;
    }
    this.compatibilityScope = await Effect.runPromise(Scope.make());
    return this.compatibilityScope;
  }

  private toEffectRequestOptions<TRes>(
    options: FlowRequestOptions<TRes> | undefined,
  ): EffectRequestOptions<TRes> | undefined {
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
  }
}
