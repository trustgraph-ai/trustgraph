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
import { Effect } from "effect";
import * as Predicate from "effect/Predicate";
import * as S from "effect/Schema";

import type {
  PubSubBackend,
  BackendProducer,
  BackendConsumer,
  CreateProducerOptions,
  CreateConsumerOptions,
  Message,
} from "./types.js";
import { pubSubError } from "../errors.js";

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

const hasJsMsg = Predicate.hasProperty("_jsMsg");

function isAckableJsMsg(value: unknown): value is Pick<JsMsg, "ack" | "nak"> {
  if (!Predicate.isObject(value)) return false;
  if (!Predicate.hasProperty(value, "ack")) return false;
  if (!Predicate.hasProperty(value, "nak")) return false;
  return typeof value.ack === "function" && typeof value.nak === "function";
}

function isNatsMessage<T>(message: Message<T>): message is NatsMessage<T> {
  return hasJsMsg(message) && isAckableJsMsg(message._jsMsg);
}

function makeNatsProducer<T>(
  js: JetStreamClient,
  subject: string,
  schema?: S.Codec<T, unknown>,
): BackendProducer<T> {
  return {
    send: (message, properties) =>
      Effect.runPromise(
        Effect.gen(function* () {
          const encoded = schema !== undefined
            ? yield* S.encodeUnknownEffect(schema)(message).pipe(
                Effect.mapError((error) => pubSubError(`encode:${subject}`, error)),
              )
            : message;
          const json = yield* S.encodeUnknownEffect(S.UnknownFromJsonString)(encoded).pipe(
            Effect.mapError((error) => pubSubError(`encode-json:${subject}`, error)),
          );
          const data = sc.encode(json);
          const opts: Record<string, unknown> = {};

          if (properties !== undefined && Object.keys(properties).length > 0) {
            const { headers } = yield* Effect.tryPromise({
              try: () => import("nats"),
              catch: (error) => pubSubError("import:nats-headers", error),
            });
            const hdrs = headers();
            for (const [key, val] of Object.entries(properties)) {
              hdrs.append(key, val);
            }
            opts.headers = hdrs;
          }

          yield* Effect.tryPromise({
            try: () => js.publish(subject, data, opts),
            catch: (error) => pubSubError(`publish:${subject}`, error),
          });
        }),
      ),
    // NATS publishes are flushed on the connection level.
    flush: () => Promise.resolve(),
    // No per-producer cleanup needed for NATS.
    close: () => Promise.resolve(),
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
  schema?: S.Codec<T, unknown>,
): InitializableBackendConsumer<T> {
  let consumer: NatsJsConsumer | null = null;

  return {
    init: () =>
      Effect.runPromise(
        Effect.gen(function* () {
          const existing = yield* Effect.tryPromise({
            try: () => js.consumers.get(streamName, subscription),
            catch: (error) => pubSubError(`get-consumer:${streamName}:${subscription}`, error),
          }).pipe(
            Effect.catch(() =>
              Effect.gen(function* () {
                const deliverPolicy =
                  initialPosition === "earliest"
                    ? DeliverPolicy.All
                    : DeliverPolicy.New;

                yield* Effect.tryPromise({
                  try: () =>
                    jsm.consumers.add(streamName, {
                      durable_name: subscription,
                      ack_policy: AckPolicy.Explicit,
                      deliver_policy: deliverPolicy,
                      filter_subject: subject,
                    }),
                  catch: (error) => pubSubError(`add-consumer:${streamName}:${subscription}`, error),
                });

                return yield* Effect.tryPromise({
                  try: () => js.consumers.get(streamName, subscription),
                  catch: (error) => pubSubError(`get-consumer:${streamName}:${subscription}`, error),
                });
              }),
            ),
          );
          consumer = existing;
        }),
      ),
    receive: (timeoutMs = 2000) =>
      Effect.runPromise(
        Effect.gen(function* () {
          const current = consumer;
          if (current === null) {
            return yield* pubSubError("receive", "Consumer not initialized");
          }

          // Pull a single message with a timeout using the pull-based API.
          // consumer.next() returns a JsMsg or null when the timeout expires.
          const msg = yield* Effect.tryPromise({
            try: () => current.next({ expires: timeoutMs }),
            catch: (error) => pubSubError(`receive:${subject}`, error),
          });
          if (msg === null) return null;

          const parsed = yield* S.decodeUnknownEffect(S.UnknownFromJsonString)(sc.decode(msg.data)).pipe(
            Effect.mapError((error) => pubSubError(`decode-json:${subject}`, error)),
          );
          const decoded = schema !== undefined
            ? yield* S.decodeUnknownEffect(schema)(parsed).pipe(
                Effect.mapError((error) => pubSubError(`decode-schema:${subject}`, error)),
              )
            : yield* S.decodeUnknownEffect(S.Any)(parsed).pipe(
                Effect.mapError((error) => pubSubError(`decode-any:${subject}`, error)),
              );
          return makeNatsMessage(msg, decoded);
        }),
      ),
    acknowledge: (message) =>
      Effect.runPromise(
        Effect.gen(function* () {
          if (!isNatsMessage(message)) {
            return yield* pubSubError(`acknowledge:${subject}`, "Message was not produced by NATS backend");
          }
          yield* Effect.sync(() => {
            message._jsMsg.ack();
          });
        }),
      ),
    negativeAcknowledge: (message) =>
      Effect.runPromise(
        Effect.gen(function* () {
          if (!isNatsMessage(message)) {
            return yield* pubSubError(
              `negative-acknowledge:${subject}`,
              "Message was not produced by NATS backend",
            );
          }
          yield* Effect.sync(() => {
            message._jsMsg.nak();
          });
        }),
      ),
    unsubscribe: () => {
      // The pull-based consumer does not have a persistent subscription to drain.
      // Clearing the reference is sufficient; the durable consumer persists server-side.
      consumer = null;
      return Promise.resolve();
    },
    close: () => {
      consumer = null;
      return Promise.resolve();
    },
  };
}

export function makeNatsBackend(url = "nats://localhost:4222"): PubSubBackend {
  let connection: NatsConnection | null = null;
  let js: JetStreamClient | null = null;
  let jsm: JetStreamManager | null = null;
  const initializedStreams = new Set<string>();

  const ensureConnected = Effect.fn("NatsBackend.ensureConnected")(function* () {
    if (connection === null) {
      const conn = yield* Effect.tryPromise({
        try: () => connect({ servers: url }),
        catch: (error) => pubSubError("connect", error),
      });
      connection = conn;
      js = conn.jetstream();
      jsm = yield* Effect.tryPromise({
        try: () => conn.jetstreamManager(),
        catch: (error) => pubSubError("jetstream-manager", error),
      });
    }
  });

  /**
   * Ensure the stream for a given subject exists with a wildcard filter.
   * E.g. subject "tg.flow.config-request" → stream "tg_flow" with subjects ["tg.flow.>"]
   */
  const ensureStream = Effect.fn("NatsBackend.ensureStream")(function* (subject: string) {
    const parts = subject.split(".");
    const streamName = parts.slice(0, 2).join("_");

    if (initializedStreams.has(streamName)) return streamName;

    const wildcardSubject = `${parts.slice(0, 2).join(".")}.>`;

    const manager = jsm;
    if (manager === null) return yield* pubSubError("ensure-stream", "NATS backend not connected");

    yield* Effect.tryPromise({
      try: () => manager.streams.info(streamName),
      catch: (error) => pubSubError(`stream-info:${streamName}`, error),
    }).pipe(
      Effect.catch(() =>
        Effect.tryPromise({
          try: () =>
            manager.streams.add({
              name: streamName,
              subjects: [wildcardSubject],
            }),
          catch: (error) => pubSubError(`stream-add:${streamName}`, error),
        }),
      ),
    );
    initializedStreams.add(streamName);
    return streamName;
  });

  return {
    createProducer: <T>(options: CreateProducerOptions<T>) =>
      Effect.runPromise(
        Effect.gen(function* () {
          yield* ensureConnected();
          yield* ensureStream(options.topic);
          const client = js;
          if (client === null) return yield* pubSubError("create-producer", "NATS backend not connected");
          return makeNatsProducer<T>(client, options.topic, options.schema);
        }),
      ),
    createConsumer: <T>(options: CreateConsumerOptions<T>) =>
      Effect.runPromise(
        Effect.gen(function* () {
          yield* ensureConnected();
          const streamName = yield* ensureStream(options.topic);
          const client = js;
          const manager = jsm;
          if (client === null || manager === null) {
            return yield* pubSubError("create-consumer", "NATS backend not connected");
          }
          const consumer = makeNatsConsumer<T>(
            client,
            manager,
            options.topic,
            options.subscription,
            options.initialPosition ?? "latest",
            streamName,
            options.schema,
          );
          yield* Effect.tryPromise({
            try: () => consumer.init(),
            catch: (error) => pubSubError(`init-consumer:${options.topic}`, error),
          });
          return consumer;
        }),
      ),
    close: () =>
      Effect.runPromise(
        Effect.gen(function* () {
          const conn = connection;
          if (conn !== null) {
            yield* Effect.tryPromise({
              try: () => conn.drain(),
              catch: (error) => pubSubError("close", error),
            });
            connection = null;
            js = null;
            jsm = null;
          }
        }),
      ),
  };
}
