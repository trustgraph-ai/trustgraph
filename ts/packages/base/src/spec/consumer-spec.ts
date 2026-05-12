/**
 * Consumer specification — declares a message consumer for a flow.
 *
 * Python reference: trustgraph-base/trustgraph/base/consumer_spec.py
 */

import { Effect } from "effect";
import * as S from "effect/Schema";
import type { Spec } from "./types.js";
import type { SpecRuntimeRequirements } from "./types.js";
import type { PubSubBackend } from "../backend/types.js";
import type { Flow, FlowDefinition } from "../processor/flow.js";
import { type MessageHandler } from "../messaging/consumer.js";
import {
  ConsumerFactory,
  type EffectMessageHandler,
} from "../messaging/runtime.js";
import {
  messagingHandlerError,
  TooManyRequestsError,
  type MessagingHandlerError,
  type PubSubError,
} from "../errors.js";

const isTooManyRequestsError = S.is(TooManyRequestsError);

export class ConsumerSpec<T, E = never, R = never> implements Spec<R> {
  public readonly name: string;
  private readonly handler: EffectMessageHandler<T, E, R>;
  private readonly concurrency: number;

  constructor(
    name: string,
    handler: EffectMessageHandler<T, E, R>,
    concurrency = 1,
  ) {
    this.name = name;
    this.handler = handler;
    this.concurrency = concurrency;
  }

  static fromPromise<T>(
    name: string,
    handler: MessageHandler<T>,
    concurrency = 1,
  ): ConsumerSpec<T, TooManyRequestsError | MessagingHandlerError> {
    return new ConsumerSpec<T, TooManyRequestsError | MessagingHandlerError>(
      name,
      (message, properties, flow) =>
        Effect.tryPromise({
          try: () => handler(message, properties, flow),
          catch: (error) =>
            isTooManyRequestsError(error)
              ? error
              : messagingHandlerError(name, `${flow.id}-${flow.name}-${name}`, error),
        }),
      concurrency,
    );
  }

  addEffect(flow: Flow<R>, definition: FlowDefinition) {
    const spec = this;
    return Effect.gen(function* () {
      const topic = definition.topics?.[spec.name] ?? spec.name;
      const factory = yield* ConsumerFactory;
      const consumer = yield* factory.run<T, E, R>(
        {
          topic,
          subscription: `${flow.processorId}-${flow.name}-${spec.name}`,
          handler: spec.handler,
          concurrency: spec.concurrency,
        },
        { id: flow.processorId, name: flow.name, flow },
      );
      flow.registerConsumer(spec.name, consumer);
    });
  }

  async add(flow: Flow, pubsub: PubSubBackend, definition: FlowDefinition): Promise<void> {
    const effect = this.addEffect(flow, definition) as Effect.Effect<
      void,
      PubSubError,
      SpecRuntimeRequirements
    >;
    await flow.runInCompatibilityScope(effect, pubsub);
  }
}
