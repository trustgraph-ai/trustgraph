/**
 * Core pub/sub backend abstraction.
 *
 * Mirrors Python's backend.py Protocol classes. Any message broker
 * (NATS, Pulsar, Redis Streams) implements these interfaces.
 */

import type { Effect } from "effect";
import type * as S from "effect/Schema";
import type { PubSubError } from "../errors.js";

export interface Message<T = unknown> {
  value(): T;
  properties(): Record<string, string>;
}

export interface BackendProducer<T = unknown> {
  send(message: T, properties?: Record<string, string>): Effect.Effect<void, PubSubError>;
  flush: Effect.Effect<void, PubSubError>;
  close: Effect.Effect<void, PubSubError>;
}

export interface BackendConsumer<T = unknown> {
  receive(timeoutMs?: number): Effect.Effect<Message<T> | null, PubSubError>;
  acknowledge(message: Message<T>): Effect.Effect<void, PubSubError>;
  negativeAcknowledge(message: Message<T>): Effect.Effect<void, PubSubError>;
  unsubscribe: Effect.Effect<void, PubSubError>;
  close: Effect.Effect<void, PubSubError>;
}

export type ConsumerType = "shared" | "exclusive" | "failover";
export type InitialPosition = "latest" | "earliest";

export interface CreateProducerOptions<T = unknown> {
  topic: string;
  schema?: S.Codec<T, unknown>;
}

export interface CreateConsumerOptions<T = unknown> {
  topic: string;
  subscription: string;
  initialPosition?: InitialPosition;
  consumerType?: ConsumerType;
  schema?: S.Codec<T, unknown>;
}

export interface PubSubBackend {
  createProducer<T>(options: CreateProducerOptions<T>): Effect.Effect<BackendProducer<T>, PubSubError>;
  createConsumer<T>(options: CreateConsumerOptions<T>): Effect.Effect<BackendConsumer<T>, PubSubError>;
  close: Effect.Effect<void, PubSubError>;
}
