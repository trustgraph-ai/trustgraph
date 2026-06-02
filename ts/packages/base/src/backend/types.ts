/**
 * Core pub/sub backend abstraction.
 *
 * Mirrors Python's backend.py Protocol classes. Any message broker
 * (NATS, Pulsar, Redis Streams) implements these interfaces.
 */

import type * as S from "effect/Schema";

export interface Message<T = unknown> {
  value(): T;
  properties(): Record<string, string>;
}

export interface BackendProducer<T = unknown> {
  send(message: T, properties?: Record<string, string>): Promise<void>;
  flush(): Promise<void>;
  close(): Promise<void>;
}

export interface BackendConsumer<T = unknown> {
  receive(timeoutMs?: number): Promise<Message<T> | null>;
  acknowledge(message: Message<T>): Promise<void>;
  negativeAcknowledge(message: Message<T>): Promise<void>;
  unsubscribe(): Promise<void>;
  close(): Promise<void>;
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
  createProducer<T>(options: CreateProducerOptions<T>): Promise<BackendProducer<T>>;
  createConsumer<T>(options: CreateConsumerOptions<T>): Promise<BackendConsumer<T>>;
  close(): Promise<void>;
}
