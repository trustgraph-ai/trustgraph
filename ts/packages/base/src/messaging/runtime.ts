/**
 * Effect-native messaging factories and scoped runtime helpers.
 */

import { randomUUID } from "node:crypto";
import { Context, Duration, Effect, Fiber, Layer, Queue, Scope } from "effect";
import * as O from "effect/Option";
import * as S from "effect/Schema";
import type {
  BackendConsumer,
  BackendProducer,
  CreateConsumerOptions,
  CreateProducerOptions,
  Message,
} from "../backend/types.js";
import { PubSub, type PubSubService } from "../backend/pubsub.js";
import {
  flowRuntimeError,
  messagingDeliveryError,
  messagingHandlerError,
  messagingLifecycleError,
  messagingTimeoutError,
  TooManyRequestsError,
  type FlowRuntimeError,
  type MessagingDeliveryError,
  type MessagingLifecycleError,
  type MessagingTimeoutError,
  type PubSubError,
} from "../errors.js";
import type { ProducerMetrics } from "../metrics/prometheus.js";
import type { FlowContext } from "./consumer.js";
import type { Flow } from "../processor/flow.js";
import type { SpecRuntimeRequirements } from "../spec/types.js";
import {
  loadMessagingRuntimeConfig,
  type MessagingRuntimeConfig,
} from "../runtime/messaging-config.js";

const isTooManyRequestsError = S.is(TooManyRequestsError);

export type EffectMessageHandler<T, E = never, R = never> = (
  message: T,
  properties: Record<string, string>,
  flow: FlowContext<R>,
) => Effect.Effect<void, E, R>;

export interface EffectProducerOptions {
  readonly topic: string;
  readonly schema?: S.Top;
  readonly metrics?: ProducerMetrics;
}

export interface EffectProducer<T> {
  readonly send: (id: string, message: T) => Effect.Effect<void, MessagingDeliveryError>;
  readonly flush: Effect.Effect<void, MessagingDeliveryError>;
  readonly close: Effect.Effect<void, MessagingDeliveryError>;
}

export interface EffectConsumerOptions<T, E = never, R = never> {
  readonly topic: string;
  readonly subscription: string;
  readonly handler: EffectMessageHandler<T, E, R>;
  readonly concurrency?: number;
  readonly initialPosition?: "latest" | "earliest";
  readonly schema?: S.Top;
  readonly receiveTimeoutMs?: number;
  readonly errorBackoffMs?: number;
  readonly rateLimitRetryMs?: number;
}

export interface EffectConsumer {
  readonly stop: Effect.Effect<void, MessagingLifecycleError>;
  readonly fibers: ReadonlyArray<Fiber.Fiber<void, never>>;
}

export interface EffectRequestResponseOptions {
  readonly requestTopic: string;
  readonly responseTopic: string;
  readonly subscription: string;
  readonly requestSchema?: S.Top;
  readonly responseSchema?: S.Top;
}

export interface EffectRequestOptions<TRes, E = never, R = never> {
  readonly timeoutMs?: number;
  readonly recipient?: (response: TRes) => Effect.Effect<boolean, E, R>;
}

export interface EffectRequestResponse<TReq, TRes> {
  readonly request: <E = never, R = never>(
    request: TReq,
    options?: EffectRequestOptions<TRes, E, R>,
  ) => Effect.Effect<TRes, MessagingDeliveryError | MessagingTimeoutError | E, R>;
  readonly stop: Effect.Effect<void, MessagingLifecycleError | MessagingDeliveryError>;
}

export interface ProducerFactoryService {
  readonly make: <T>(
    options: EffectProducerOptions,
  ) => Effect.Effect<EffectProducer<T>, PubSubError, Scope.Scope>;
}

export interface ConsumerFactoryService {
  readonly run: <T, E = never, R = never>(
    options: EffectConsumerOptions<T, E, R>,
    flow: FlowContext<R>,
  ) => Effect.Effect<EffectConsumer, PubSubError, Scope.Scope | R>;
}

export interface RequestResponseFactoryService {
  readonly make: <TReq, TRes>(
    options: EffectRequestResponseOptions,
  ) => Effect.Effect<EffectRequestResponse<TReq, TRes>, PubSubError, Scope.Scope>;
}

export interface FlowRuntimeService {
  readonly run: <Requirements = never>(
    flow: Flow<Requirements>,
  ) => Effect.Effect<void, FlowRuntimeError, SpecRuntimeRequirements | Requirements>;
}

export class ProducerFactory extends Context.Service<ProducerFactory, ProducerFactoryService>()(
  "@trustgraph/base/messaging/runtime/ProducerFactory",
) {}

export class ConsumerFactory extends Context.Service<ConsumerFactory, ConsumerFactoryService>()(
  "@trustgraph/base/messaging/runtime/ConsumerFactory",
) {}

export class RequestResponseFactory extends Context.Service<
  RequestResponseFactory,
  RequestResponseFactoryService
>()("@trustgraph/base/messaging/runtime/RequestResponseFactory") {}

export class FlowRuntime extends Context.Service<FlowRuntime, FlowRuntimeService>()(
  "@trustgraph/base/messaging/runtime/FlowRuntime",
) {}

export function makeEffectProducerHandle<T>(
  backend: BackendProducer<T>,
  options: EffectProducerOptions,
): EffectProducer<T> {
  return {
    send: Effect.fn(`Producer.send:${options.topic}`)((id: string, message: T) =>
      Effect.tryPromise({
        try: () => backend.send(message, { id }),
        catch: (error) => messagingDeliveryError(options.topic, "send", error),
      }).pipe(
        Effect.tap(() =>
          options.metrics === undefined
            ? Effect.void
            : Effect.sync(() => {
                options.metrics?.inc();
              }),
        ),
      ),
    ),
    flush: Effect.tryPromise({
      try: () => backend.flush(),
      catch: (error) => messagingDeliveryError(options.topic, "flush", error),
    }),
    close: Effect.tryPromise({
      try: () => backend.close(),
      catch: (error) => messagingDeliveryError(options.topic, "close", error),
    }),
  };
}

export const makeEffectProducerFromPubSub = Effect.fn("makeEffectProducerFromPubSub")(function* <T>(
  pubsub: PubSubService,
  options: EffectProducerOptions,
) {
  const createOptions: CreateProducerOptions = options.schema === undefined
    ? { topic: options.topic }
    : { topic: options.topic, schema: options.schema };
  const backend = yield* pubsub.createProducer<T>(createOptions);
  const producer = makeEffectProducerHandle(backend, options);

  yield* Effect.addFinalizer(() =>
    producer.close.pipe(
      Effect.catch((error) =>
        Effect.logError("[Producer] Failed to close producer", {
          error: error.message,
          topic: error.topic,
        }),
      ),
    ),
  );

  return producer;
});

const closeConsumerBackend = <T>(
  backend: BackendConsumer<T>,
  topic: string,
  subscription: string,
) =>
  Effect.tryPromise({
    try: () => backend.close(),
    catch: (error) => messagingLifecycleError(`${topic}:${subscription}`, "close-consumer", error),
  });

const acknowledgeMessage = <T>(
  backend: BackendConsumer<T>,
  message: Message<T>,
  topic: string,
) =>
  Effect.tryPromise({
    try: () => backend.acknowledge(message),
    catch: (error) => messagingDeliveryError(topic, "acknowledge", error),
  });

const negativeAcknowledgeMessage = <T>(
  backend: BackendConsumer<T>,
  message: Message<T>,
  topic: string,
) =>
  Effect.tryPromise({
    try: () => backend.negativeAcknowledge(message),
    catch: (error) => messagingDeliveryError(topic, "negative-acknowledge", error),
  });

const receiveMessage = <T>(
  backend: BackendConsumer<T>,
  topic: string,
  timeoutMs: number,
) =>
  Effect.tryPromise({
    try: () => backend.receive(timeoutMs),
    catch: (error) => messagingDeliveryError(topic, "receive", error),
  });

const handleMessageWithRetry = Effect.fn("handleMessageWithRetry")(function* <T, E, R>(
  options: EffectConsumerOptions<T, E, R>,
  flow: FlowContext<R>,
  message: Message<T>,
  config: MessagingRuntimeConfig,
) {
  const runHandler = Effect.fn(`Consumer.handler:${options.topic}`)(() =>
    options.handler(message.value(), message.properties(), flow).pipe(
      Effect.mapError((error) => messagingHandlerError(options.topic, options.subscription, error)),
    ),
  );

  return yield* options.handler(message.value(), message.properties(), flow).pipe(
    Effect.catch((error) => {
      if (isTooManyRequestsError(error)) {
        return Effect.gen(function* () {
          yield* Effect.logWarning("[Consumer] Rate limited, retrying", {
            topic: options.topic,
            subscription: options.subscription,
            retryMs: config.rateLimitRetryMs,
          });
          yield* Effect.sleep(Duration.millis(config.rateLimitRetryMs));
          yield* runHandler();
        });
      }

      return Effect.fail(messagingHandlerError(options.topic, options.subscription, error));
    }),
  );
});

const processConsumerMessage = Effect.fn("processConsumerMessage")(function* <T, E, R>(
  backend: BackendConsumer<T>,
  options: EffectConsumerOptions<T, E, R>,
  flow: FlowContext<R>,
  message: Message<T>,
  config: MessagingRuntimeConfig,
) {
  yield* handleMessageWithRetry(options, flow, message, config).pipe(
    Effect.flatMap(() => acknowledgeMessage(backend, message, options.topic)),
    Effect.catch((error) =>
      negativeAcknowledgeMessage(backend, message, options.topic).pipe(
        Effect.catch((nakError) =>
          Effect.logError("[Consumer] Failed to negative-acknowledge message", {
            error: nakError.message,
            topic: nakError.topic,
          }),
        ),
        Effect.flatMap(() =>
          Effect.logError("[Consumer] Message handling failed", {
            error: error.message,
            topic: options.topic,
            subscription: options.subscription,
          }),
        ),
      ),
    ),
  );
});

const consumerLoop = <T, E, R>(
  backend: BackendConsumer<T>,
  options: EffectConsumerOptions<T, E, R>,
  flow: FlowContext<R>,
  config: MessagingRuntimeConfig,
): Effect.Effect<void, never, R> =>
  Effect.whileLoop({
    while: () => true,
    body: () =>
      receiveMessage(backend, options.topic, options.receiveTimeoutMs ?? config.consumerReceiveTimeoutMs).pipe(
        Effect.flatMap((message) =>
          message === null
            ? Effect.sleep(Duration.millis(options.receiveTimeoutMs ?? config.consumerReceiveTimeoutMs))
            : processConsumerMessage(backend, options, flow, message, config),
        ),
        Effect.catch((error) =>
          Effect.logError("[Consumer] Receive loop failed", {
            error: error.message,
            topic: options.topic,
            subscription: options.subscription,
          }).pipe(
            Effect.flatMap(() =>
              Effect.sleep(Duration.millis(options.errorBackoffMs ?? config.consumerErrorBackoffMs)),
            ),
          ),
        ),
      ),
    step: () => undefined,
  });

export const makeEffectConsumerFromPubSub = Effect.fn("makeEffectConsumerFromPubSub")(function* <T, E, R>(
  pubsub: PubSubService,
  config: MessagingRuntimeConfig,
  options: EffectConsumerOptions<T, E, R>,
  flow: FlowContext<R>,
) {
  const createOptions: CreateConsumerOptions = {
    topic: options.topic,
    subscription: options.subscription,
    ...(options.initialPosition === undefined ? {} : { initialPosition: options.initialPosition }),
    ...(options.schema === undefined ? {} : { schema: options.schema }),
  };
  const backend = yield* pubsub.createConsumer<T>(createOptions);
  const concurrency = Math.max(1, options.concurrency ?? 1);
  const workerIndexes = Array.from({ length: concurrency }, (_value, index) => index);
  const fibers = yield* Effect.forEach(workerIndexes, () =>
    consumerLoop(backend, options, flow, {
      ...config,
      rateLimitRetryMs: options.rateLimitRetryMs ?? config.rateLimitRetryMs,
    }).pipe(Effect.forkChild),
  );

  const stop = Effect.fn(`Consumer.stop:${options.topic}`)(function* () {
    yield* Effect.forEach(fibers, Fiber.interrupt, { discard: true });
    yield* closeConsumerBackend(backend, options.topic, options.subscription);
  });

  yield* Effect.addFinalizer(() =>
    stop().pipe(
      Effect.catch((error) =>
        Effect.logError("[Consumer] Failed to stop consumer", {
          error: error.message,
          resource: error.resource,
          operation: error.operation,
        }),
      ),
    ),
  );

  return {
    fibers,
    stop: stop(),
  } satisfies EffectConsumer;
});

const dispatchResponseLoop = <T>(
  backend: BackendConsumer<T>,
  responseTopic: string,
  subscribers: Map<string, Queue.Queue<T>>,
  config: MessagingRuntimeConfig,
): Effect.Effect<void> =>
  Effect.whileLoop({
    while: () => true,
    body: () =>
      receiveMessage(backend, responseTopic, config.consumerReceiveTimeoutMs).pipe(
        Effect.flatMap((message) => {
          if (message === null) {
            return Effect.sleep(Duration.millis(config.consumerReceiveTimeoutMs));
          }

          const id = message.properties().id;
          const queue = id === undefined ? undefined : subscribers.get(id);
          return Effect.gen(function* () {
            if (queue !== undefined) {
              yield* Queue.offer(queue, message.value());
            }
            yield* acknowledgeMessage(backend, message, responseTopic);
          });
        }),
        Effect.catch((error) =>
          Effect.logError("[RequestResponse] Response dispatch failed", {
            error: error.message,
            topic: responseTopic,
          }).pipe(Effect.flatMap(() => Effect.sleep(Duration.millis(config.consumerErrorBackoffMs)))),
        ),
      ),
    step: () => undefined,
  });

const waitForResponse = Effect.fn("waitForResponse")(function* <TRes, E, R>(
  queue: Queue.Queue<TRes>,
  options: EffectRequestOptions<TRes, E, R> | undefined,
) {
  while (true) {
    const response = yield* Queue.take(queue);
    if (options?.recipient === undefined) {
      return response;
    }

    const complete = yield* options.recipient(response);
    if (complete) {
      return response;
    }
  }
});

export const makeEffectRequestResponseFromPubSub = Effect.fn("makeEffectRequestResponseFromPubSub")(function* <
  TReq,
  TRes,
>(
  pubsub: PubSubService,
  config: MessagingRuntimeConfig,
  options: EffectRequestResponseOptions,
) {
  const producerOptions: CreateProducerOptions = options.requestSchema === undefined
    ? { topic: options.requestTopic }
    : { topic: options.requestTopic, schema: options.requestSchema };
  const producerBackend = yield* pubsub.createProducer<TReq>(producerOptions);
  const producer = makeEffectProducerHandle<TReq>(producerBackend, {
    topic: options.requestTopic,
    ...(options.requestSchema === undefined ? {} : { schema: options.requestSchema }),
  });
  const createOptions: CreateConsumerOptions = {
    topic: options.responseTopic,
    subscription: options.subscription,
    ...(options.responseSchema === undefined ? {} : { schema: options.responseSchema }),
  };
  const backend = yield* pubsub.createConsumer<TRes>(createOptions);
  const subscribers = new Map<string, Queue.Queue<TRes>>();
  const fiber = yield* dispatchResponseLoop(backend, options.responseTopic, subscribers, config).pipe(Effect.forkScoped);
  let stopped = false;

  const stop = Effect.fn(`RequestResponse.stop:${options.requestTopic}`)(function* () {
    if (stopped) return;
    stopped = true;
    yield* Fiber.interrupt(fiber);
    yield* producer.close;
    yield* closeConsumerBackend(backend, options.responseTopic, options.subscription);
  });

  yield* Effect.addFinalizer(() =>
    stop().pipe(
      Effect.catch((error) =>
        Effect.logError("[RequestResponse] Failed to stop runtime", {
          error: error.message,
        }),
      ),
    ),
  );

  return {
    request: <E = never, R = never>(
      request: TReq,
      requestOptions?: EffectRequestOptions<TRes, E, R>,
    ) => {
      const id = randomUUID();
      const timeoutMs = requestOptions?.timeoutMs ?? config.requestTimeoutMs;

      return Effect.acquireUseRelease(
        Queue.unbounded<TRes>().pipe(
          Effect.tap((queue) =>
            Effect.sync(() => {
              subscribers.set(id, queue);
            }),
          ),
        ),
        (queue) =>
          Effect.gen(function* () {
            yield* producer.send(id, request);
            const result = yield* waitForResponse(queue, requestOptions).pipe(
              Effect.timeoutOption(Duration.millis(timeoutMs)),
            );
            return yield* O.match(result, {
              onNone: () => Effect.fail(messagingTimeoutError("request-response", timeoutMs)),
              onSome: Effect.succeed,
            });
          }),
        (queue) =>
          Effect.sync(() => {
            subscribers.delete(id);
          }).pipe(
            Effect.flatMap(() => Queue.shutdown(queue)),
            Effect.ignore,
          ),
      );
    },
    stop: stop(),
  } satisfies EffectRequestResponse<TReq, TRes>;
});

export function makeProducerFactoryService(pubsub: PubSubService): ProducerFactoryService {
  return {
    make: Effect.fn("ProducerFactory.make")(<T>(options: EffectProducerOptions) =>
      makeEffectProducerFromPubSub<T>(pubsub, options),
    ),
  };
}

export function makeConsumerFactoryService(
  pubsub: PubSubService,
  config: MessagingRuntimeConfig,
): ConsumerFactoryService {
  return {
    run: Effect.fn("ConsumerFactory.run")(<T, E = never, R = never>(
      options: EffectConsumerOptions<T, E, R>,
      flow: FlowContext<R>,
    ) =>
      makeEffectConsumerFromPubSub(pubsub, config, options, flow),
    ),
  };
}

export function makeRequestResponseFactoryService(
  pubsub: PubSubService,
  config: MessagingRuntimeConfig,
): RequestResponseFactoryService {
  const make = Effect.fn("RequestResponseFactory.make")(function* <TReq, TRes>(
    options: EffectRequestResponseOptions,
  ) {
    return yield* makeEffectRequestResponseFromPubSub<TReq, TRes>(pubsub, config, options);
  }) as RequestResponseFactoryService["make"];

  return { make };
}

export const ProducerFactoryLive = Layer.effect(
  ProducerFactory,
  Effect.gen(function* () {
    const pubsub = yield* PubSub;
    return ProducerFactory.of(makeProducerFactoryService(pubsub));
  }),
);

export const ConsumerFactoryLive = Layer.effect(
  ConsumerFactory,
  Effect.gen(function* () {
    const pubsub = yield* PubSub;
    const config = yield* loadMessagingRuntimeConfig();
    return ConsumerFactory.of(makeConsumerFactoryService(pubsub, config));
  }),
);

export const RequestResponseFactoryLive = Layer.effect(
  RequestResponseFactory,
  Effect.gen(function* () {
    const pubsub = yield* PubSub;
    const config = yield* loadMessagingRuntimeConfig();
    return RequestResponseFactory.of(makeRequestResponseFactoryService(pubsub, config));
  }),
);

export const runFlowRuntimeScoped = Effect.fn("FlowRuntime.run")(function* <Requirements = never>(
  flow: Flow<Requirements>,
) {
  yield* flow.startEffect().pipe(
    Effect.mapError((error) => flowRuntimeError(flow.name, "start", error)),
  );
  yield* Effect.addFinalizer(() =>
    Effect.sync(() => {
      flow.clearResources();
    }),
  );
});

export const FlowRuntimeLive = Layer.succeed(
  FlowRuntime,
  FlowRuntime.of({
    run: runFlowRuntimeScoped,
  }),
);

export const MessagingRuntimeLive = Layer.mergeAll(
  ProducerFactoryLive,
  ConsumerFactoryLive,
  RequestResponseFactoryLive,
  FlowRuntimeLive,
);

export const runEffectProducerScoped = Effect.fn("runEffectProducerScoped")(function* <T>(
  options: EffectProducerOptions,
) {
  const pubsub = yield* PubSub;
  return yield* makeEffectProducerFromPubSub<T>(pubsub, options);
});

export const runEffectConsumerScoped = Effect.fn("runEffectConsumerScoped")(function* <T, E = never, R = never>(
  options: EffectConsumerOptions<T, E, R>,
  flow: FlowContext<R>,
) {
  const pubsub = yield* PubSub;
  const config = yield* loadMessagingRuntimeConfig();
  return yield* makeEffectConsumerFromPubSub(pubsub, config, options, flow);
});

export const runEffectRequestResponseScoped = Effect.fn("runEffectRequestResponseScoped")(function* <TReq, TRes>(
  options: EffectRequestResponseOptions,
) {
  const pubsub = yield* PubSub;
  const config = yield* loadMessagingRuntimeConfig();
  return yield* makeEffectRequestResponseFromPubSub<TReq, TRes>(pubsub, config, options);
});

export const runFlowScoped = Effect.fn("runFlowScoped")(function* (
  flow: Flow,
) {
  yield* runFlowRuntimeScoped(flow);
});
