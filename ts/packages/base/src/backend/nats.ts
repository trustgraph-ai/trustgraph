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
import * as S from "effect/Schema";

import type {
  PubSubBackend,
  BackendProducer,
  BackendConsumer,
  CreateProducerOptions,
  CreateConsumerOptions,
  Message,
} from "./types.js";

const sc = StringCodec();

interface NatsMessage<T> extends Message<T> {
  /** Exposed so acknowledge/negativeAcknowledge can access the raw JsMsg */
  readonly _jsMsg: JsMsg;
}

function makeNatsMessage<T>(msg: JsMsg, decoded: T): NatsMessage<T> {
  return {
    _jsMsg: msg,
    value: () => decoded,
    properties: () => {
      const headers = msg.headers;
      const props: Record<string, string> = {};
      if (headers !== undefined) {
        for (const [key, values] of headers) {
          const value = values[0];
          if (value !== undefined) {
            props[key] = value;
          }
        }
      }
      return props;
    },
  };
}

function makeNatsProducer<T>(
  js: JetStreamClient,
  subject: string,
  schema?: S.Top,
): BackendProducer<T> {
  return {
    send: async (message, properties) => {
      const encoded = schema !== undefined
        ? S.encodeUnknownSync(schema as S.Codec<unknown, unknown>)(message)
        : message;
      const data = sc.encode(JSON.stringify(encoded));
      const opts: Record<string, unknown> = {};

      if (properties !== undefined && Object.keys(properties).length > 0) {
        const { headers } = await import("nats");
        const hdrs = headers();
        for (const [key, val] of Object.entries(properties)) {
          hdrs.append(key, val);
        }
        opts.headers = hdrs;
      }

      await js.publish(subject, data, opts);
    },
    flush: async () => {
      // NATS publishes are flushed on the connection level.
    },
    close: async () => {
      // No per-producer cleanup needed for NATS.
    },
  };
}

interface InitializableBackendConsumer<T> extends BackendConsumer<T> {
  readonly init: () => Promise<void>;
}

function makeNatsConsumer<T>(
  js: JetStreamClient,
  jsm: JetStreamManager,
  subject: string,
  subscription: string,
  initialPosition: "latest" | "earliest",
  streamName: string,
  schema?: S.Top,
): InitializableBackendConsumer<T> {
  let consumer: NatsJsConsumer | null = null;

  return {
    init: async () => {
      // Stream is already ensured by makeNatsBackend(). Create or bind to a durable consumer.
      try {
        consumer = await js.consumers.get(streamName, subscription);
      } catch {
        const deliverPolicy =
          initialPosition === "earliest"
            ? DeliverPolicy.All
            : DeliverPolicy.New;

        await jsm.consumers.add(streamName, {
          durable_name: subscription,
          ack_policy: AckPolicy.Explicit,
          deliver_policy: deliverPolicy,
          filter_subject: subject,
        });

        consumer = await js.consumers.get(streamName, subscription);
      }
    },
    receive: async (timeoutMs = 2000) => {
      if (consumer === null) throw new Error("Consumer not initialized");

      // Pull a single message with a timeout using the pull-based API.
      // consumer.next() returns a JsMsg or null when the timeout expires.
      const msg = await consumer.next({ expires: timeoutMs });
      if (msg === null) return null;

      const parsed = JSON.parse(sc.decode(msg.data));
      const decoded = schema !== undefined
        ? S.decodeUnknownSync(schema as S.Codec<unknown, unknown>)(parsed) as T
        : parsed as T;
      return makeNatsMessage(msg, decoded);
    },
    acknowledge: async (message) => {
      const natsMsg = message as NatsMessage<T>;
      natsMsg._jsMsg.ack();
    },
    negativeAcknowledge: async (message) => {
      const natsMsg = message as NatsMessage<T>;
      natsMsg._jsMsg.nak();
    },
    unsubscribe: async () => {
      // The pull-based consumer does not have a persistent subscription to drain.
      // Clearing the reference is sufficient; the durable consumer persists server-side.
      consumer = null;
    },
    close: async () => {
      consumer = null;
    },
  };
}

export function makeNatsBackend(url = "nats://localhost:4222"): PubSubBackend {
  let connection: NatsConnection | null = null;
  let js: JetStreamClient | null = null;
  let jsm: JetStreamManager | null = null;
  const initializedStreams = new Set<string>();

  const ensureConnected = async (): Promise<void> => {
    if (connection === null) {
      connection = await connect({ servers: url });
      js = connection.jetstream();
      jsm = await connection.jetstreamManager();
    }
  };

  /**
   * Ensure the stream for a given subject exists with a wildcard filter.
   * E.g. subject "tg.flow.config-request" → stream "tg_flow" with subjects ["tg.flow.>"]
   */
  const ensureStream = async (subject: string): Promise<string> => {
    const parts = subject.split(".");
    const streamName = parts.slice(0, 2).join("_");

    if (initializedStreams.has(streamName)) return streamName;

    const wildcardSubject = `${parts.slice(0, 2).join(".")}.>`;

    const manager = jsm;
    if (manager === null) throw new Error("NATS backend not connected");

    try {
      await manager.streams.info(streamName);
    } catch {
      await manager.streams.add({
        name: streamName,
        subjects: [wildcardSubject],
      });
    }
    initializedStreams.add(streamName);
    return streamName;
  };

  return {
    createProducer: async <T>(options: CreateProducerOptions) => {
      await ensureConnected();
      await ensureStream(options.topic);
      const client = js;
      if (client === null) throw new Error("NATS backend not connected");
      return makeNatsProducer<T>(client, options.topic, options.schema);
    },
    createConsumer: async <T>(options: CreateConsumerOptions) => {
      await ensureConnected();
      const streamName = await ensureStream(options.topic);
      const client = js;
      const manager = jsm;
      if (client === null || manager === null) throw new Error("NATS backend not connected");
      const consumer = makeNatsConsumer<T>(
        client,
        manager,
        options.topic,
        options.subscription,
        options.initialPosition ?? "latest",
        streamName,
        options.schema,
      );
      await consumer.init();
      return consumer;
    },
    close: async () => {
      if (connection !== null) {
        await connection.drain();
        connection = null;
        js = null;
        jsm = null;
      }
    },
  };
}
