/**
 * NATS JetStream backend implementation.
 *
 * Replaces Pulsar as the message broker. NATS JetStream provides
 * at-least-once delivery, consumer groups, and replay — matching
 * the QoS levels used by the Python Pulsar backend.
 *
 * Python reference: trustgraph-base/trustgraph/base/pulsar_backend.py
 */

import {
  connect,
  type NatsConnection,
  type JetStreamClient,
  type JetStreamManager,
  type Consumer as NatsJsConsumer,
  type JsMsg,
  StringCodec,
  AckPolicy,
  DeliverPolicy,
} from "nats";

import type {
  PubSubBackend,
  BackendProducer,
  BackendConsumer,
  CreateProducerOptions,
  CreateConsumerOptions,
  Message,
} from "./types.js";

const sc = StringCodec();

class NatsMessage<T> implements Message<T> {
  /** Exposed so acknowledge/negativeAcknowledge can access the raw JsMsg */
  readonly _jsMsg: JsMsg;

  constructor(
    msg: JsMsg,
    private readonly decoded: T,
  ) {
    this._jsMsg = msg;
  }

  value(): T {
    return this.decoded;
  }

  properties(): Record<string, string> {
    const headers = this._jsMsg.headers;
    const props: Record<string, string> = {};
    if (headers) {
      for (const [key, values] of headers) {
        props[key] = values[0];
      }
    }
    return props;
  }
}

class NatsProducer<T> implements BackendProducer<T> {
  constructor(
    private readonly js: JetStreamClient,
    private readonly subject: string,
  ) {}

  async send(message: T, properties?: Record<string, string>): Promise<void> {
    const data = sc.encode(JSON.stringify(message));
    const opts: Record<string, unknown> = {};

    if (properties && Object.keys(properties).length > 0) {
      const { headers } = await import("nats");
      const hdrs = headers();
      for (const [key, val] of Object.entries(properties)) {
        hdrs.append(key, val);
      }
      opts.headers = hdrs;
    }

    await this.js.publish(this.subject, data, opts);
  }

  async flush(): Promise<void> {
    // NATS publishes are flushed on the connection level
  }

  async close(): Promise<void> {
    // No per-producer cleanup needed for NATS
  }
}

class NatsConsumer<T> implements BackendConsumer<T> {
  private consumer: NatsJsConsumer | null = null;

  constructor(
    private readonly js: JetStreamClient,
    private readonly jsm: JetStreamManager,
    private readonly subject: string,
    private readonly subscription: string,
    private readonly initialPosition: "latest" | "earliest",
    private readonly streamName: string,
  ) {}

  async init(): Promise<void> {
    // Stream is already ensured by NatsBackend.ensureStream().
    // Create or bind to durable consumer.
    try {
      this.consumer = await this.js.consumers.get(this.streamName, this.subscription);
    } catch {
      const deliverPolicy =
        this.initialPosition === "earliest"
          ? DeliverPolicy.All
          : DeliverPolicy.New;

      await this.jsm.consumers.add(this.streamName, {
        durable_name: this.subscription,
        ack_policy: AckPolicy.Explicit,
        deliver_policy: deliverPolicy,
        filter_subject: this.subject,
      });

      this.consumer = await this.js.consumers.get(this.streamName, this.subscription);
    }
  }

  async receive(timeoutMs = 2000): Promise<Message<T> | null> {
    if (!this.consumer) throw new Error("Consumer not initialized");

    // Pull a single message with a timeout using the pull-based API.
    // consumer.next() returns a JsMsg or null when the timeout expires.
    const msg = await this.consumer.next({ expires: timeoutMs });
    if (!msg) return null;

    const decoded = JSON.parse(sc.decode(msg.data)) as T;
    return new NatsMessage(msg, decoded);
  }

  async acknowledge(message: Message<T>): Promise<void> {
    const natsMsg = message as NatsMessage<T>;
    natsMsg._jsMsg.ack();
  }

  async negativeAcknowledge(message: Message<T>): Promise<void> {
    const natsMsg = message as NatsMessage<T>;
    natsMsg._jsMsg.nak();
  }

  async unsubscribe(): Promise<void> {
    // The pull-based consumer does not have a persistent subscription to drain.
    // Clearing the reference is sufficient; the durable consumer persists server-side.
    this.consumer = null;
  }

  async close(): Promise<void> {
    this.consumer = null;
  }
}

export class NatsBackend implements PubSubBackend {
  private connection: NatsConnection | null = null;
  private js: JetStreamClient | null = null;
  private jsm: JetStreamManager | null = null;
  private initializedStreams = new Set<string>();

  constructor(private readonly url: string = "nats://localhost:4222") {}

  private async ensureConnected(): Promise<void> {
    if (!this.connection) {
      this.connection = await connect({ servers: this.url });
      this.js = this.connection.jetstream();
      this.jsm = await this.connection.jetstreamManager();
    }
  }

  /**
   * Ensure the stream for a given subject exists with a wildcard filter.
   * E.g. subject "tg.flow.config-request" → stream "tg_flow" with subjects ["tg.flow.>"]
   */
  private async ensureStream(subject: string): Promise<string> {
    const parts = subject.split(".");
    const streamName = parts.slice(0, 2).join("_");

    if (this.initializedStreams.has(streamName)) return streamName;

    const wildcardSubject = `${parts.slice(0, 2).join(".")}.>`;

    try {
      await this.jsm!.streams.info(streamName);
    } catch {
      await this.jsm!.streams.add({
        name: streamName,
        subjects: [wildcardSubject],
      });
    }
    this.initializedStreams.add(streamName);
    return streamName;
  }

  async createProducer<T>(options: CreateProducerOptions): Promise<BackendProducer<T>> {
    await this.ensureConnected();
    await this.ensureStream(options.topic);
    return new NatsProducer<T>(this.js!, options.topic);
  }

  async createConsumer<T>(options: CreateConsumerOptions): Promise<BackendConsumer<T>> {
    await this.ensureConnected();
    const streamName = await this.ensureStream(options.topic);
    const consumer = new NatsConsumer<T>(
      this.js!,
      this.jsm!,
      options.topic,
      options.subscription,
      options.initialPosition ?? "latest",
      streamName,
    );
    await consumer.init();
    return consumer;
  }

  async close(): Promise<void> {
    if (this.connection) {
      await this.connection.drain();
      this.connection = null;
      this.js = null;
      this.jsm = null;
    }
  }
}
