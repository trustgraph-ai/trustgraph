/**
 * Core pub/sub backend abstraction.
 *
 * Mirrors Python's backend.py Protocol classes. Any message broker
 * (NATS, Pulsar, Redis Streams) implements these interfaces.
 */

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

export interface CreateProducerOptions {
  topic: string;
}

export interface CreateConsumerOptions {
  topic: string;
  subscription: string;
  initialPosition?: InitialPosition;
  consumerType?: ConsumerType;
}

export interface PubSubBackend {
  createProducer<T>(options: CreateProducerOptions): Promise<BackendProducer<T>>;
  createConsumer<T>(options: CreateConsumerOptions): Promise<BackendConsumer<T>>;
  close(): Promise<void>;
}
