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
  ErrorCode,
  type NatsConnection,
  type JetStreamClient,
  type JetStreamManager,
  type Consumer as NatsJsConsumer,
  headers,
  type JsMsg,
  type JetStreamPublishOptions,
  NatsError,
  StringCodec,
  AckPolicy,
  DeliverPolicy,
} from "nats";
import { Effect } from "effect";
import * as MutableHashSet from "effect/MutableHashSet";
import * as P from "effect/Predicate";
import * as S from "effect/Schema";

import type {
  PubSubBackend,
  BackendProducer,
  BackendConsumer,
  CreateProducerOptions,
  CreateConsumerOptions,
  Message,
} from "./types.js";
import { pubSubError, type PubSubError } from "../errors.js";

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

const hasJsMsg = P.hasProperty("_jsMsg");

class NatsLookupError extends S.TaggedErrorClass<NatsLookupError>()(
  "NatsLookupError",
  {
    cause: S.Unknown,
    operation: S.String,
  },
) {}

function natsLookupError(operation: string, cause: unknown): NatsLookupError {
  return NatsLookupError.make({ cause, operation });
}

function isAckableJsMsg(value: unknown): value is Pick<JsMsg, "ack" | "nak"> {
  if (!P.isObject(value)) return false;
  if (!P.hasProperty(value, "ack")) return false;
  if (!P.hasProperty(value, "nak")) return false;
  return typeof value.ack === "function" && typeof value.nak === "function";
}

function isNatsMessage<T>(message: Message<T>): message is NatsMessage<T> {
  return hasJsMsg(message) && isAckableJsMsg(message._jsMsg);
}

function isJetStreamMissingResource(error: unknown): boolean {
  if (!(error instanceof NatsError)) {
    return false;
  }
  if (error.code === ErrorCode.JetStream404NoMessages) {
    return true;
  }

  const jsError = error.jsError();
  return jsError?.code === 404;
}

function isMissingLookupError(error: NatsLookupError): boolean {
  return isJetStreamMissingResource(error.cause);
}

function makeNatsProducer<T>(
  js: JetStreamClient,
  subject: string,
  schema?: S.Codec<T, unknown>,
): BackendProducer<T> {
  const makePublishOptions = (
    properties: Record<string, string> | undefined,
  ): Effect.Effect<Partial<JetStreamPublishOptions>, PubSubError> => {
    if (properties === undefined || Object.keys(properties).length === 0) {
      return Effect.succeed({});
    }

    return Effect.try({
      try: () => {
        const hdrs = headers();
        for (const [key, val] of Object.entries(properties)) {
          hdrs.append(key, val);
        }
        return { headers: hdrs };
      },
      catch: (error) => pubSubError(`headers:${subject}`, error),
    });
  };

  return {
    send: Effect.fn(`NatsProducer.send:${subject}`)(function*(message: T, properties?: Record<string, string>) {
      const encoded = schema !== undefined
        ? yield* S.encodeUnknownEffect(schema)(message).pipe(
            Effect.mapError((error) => pubSubError(`encode:${subject}`, error)),
          )
        : message;
      const json = yield* S.encodeUnknownEffect(S.UnknownFromJsonString)(encoded).pipe(
        Effect.mapError((error) => pubSubError(`encode-json:${subject}`, error)),
      );
      const data = sc.encode(json);
      const opts = yield* makePublishOptions(properties);

      yield* Effect.tryPromise({
        try: () => js.publish(subject, data, opts),
        catch: (error) => pubSubError(`publish:${subject}`, error),
      });
    }),
    // NATS publishes are flushed on the connection level.
    flush: Effect.void,
    // No per-producer cleanup needed for NATS.
    close: Effect.void,
  };
}

interface InitializableBackendConsumer<T> extends BackendConsumer<T> {
  readonly init: Effect.Effect<void, PubSubError>;
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

  const isReceiveTimeoutError = (error: unknown): boolean => {
    const code = P.isObject(error) ? (error as { readonly code?: unknown }).code : undefined;
    return code === 408 || code === "408" || code === ErrorCode.Timeout;
  };

  return {
    init: Effect.gen(function* () {
      yield* Effect.tryPromise({
        try: () => jsm.consumers.info(streamName, subscription),
        catch: (error) => natsLookupError(`consumer-info:${streamName}:${subscription}`, error),
      }).pipe(
        Effect.catchIf(
          isMissingLookupError,
          () =>
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
            }),
          (error) => Effect.fail(pubSubError(error.operation, error.cause)),
        ),
      );
      consumer = yield* Effect.tryPromise({
        try: () => js.consumers.get(streamName, subscription),
        catch: (error) => pubSubError(`get-consumer:${streamName}:${subscription}`, error),
      });
    }),
    receive: Effect.fn(`NatsConsumer.receive:${subject}`)(function*(timeoutMs = 2000) {
      const current = consumer;
      if (current === null) {
        return yield* pubSubError("receive", "Consumer not initialized");
      }

      const msg = yield* Effect.tryPromise({
        try: () => current.next({ expires: timeoutMs }),
        catch: (error) =>
          isReceiveTimeoutError(error)
            ? pubSubError(`receive-timeout:${subject}`, error)
            : pubSubError(`receive:${subject}`, error),
      }).pipe(
        Effect.catchIf(
          (error) => error.operation === `receive-timeout:${subject}`,
          () => Effect.succeed(null),
        ),
      );
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
    acknowledge: Effect.fn(`NatsConsumer.acknowledge:${subject}`)(function*(message: Message<T>) {
      if (!isNatsMessage(message)) {
        return yield* pubSubError(
          `acknowledge:${subject}`,
          "Message was not produced by NATS backend",
        );
      }
      yield* Effect.try({
        try: () => {
          message._jsMsg.ack();
        },
        catch: (error) => pubSubError(`acknowledge:${subject}`, error),
      });
    }),
    negativeAcknowledge: Effect.fn(`NatsConsumer.negativeAcknowledge:${subject}`)(function*(message: Message<T>) {
      if (!isNatsMessage(message)) {
        return yield* pubSubError(
          `negative-acknowledge:${subject}`,
          "Message was not produced by NATS backend",
        );
      }
      yield* Effect.try({
        try: () => {
          message._jsMsg.nak();
        },
        catch: (error) => pubSubError(`negative-acknowledge:${subject}`, error),
      });
    }),
    unsubscribe: Effect.sync(() => {
      consumer = null;
    }),
    close: Effect.sync(() => {
      consumer = null;
    }),
  };
}

export function makeNatsBackend(url = "nats://localhost:4222"): PubSubBackend {
  let connection: NatsConnection | null = null;
  let js: JetStreamClient | null = null;
  let jsm: JetStreamManager | null = null;
  const initializedStreams = MutableHashSet.empty<string>();

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

    if (MutableHashSet.has(initializedStreams, streamName)) return streamName;

    const wildcardSubject = `${parts.slice(0, 2).join(".")}.>`;

    const manager = jsm;
    if (manager === null) {
      return yield* pubSubError("ensure-stream", "NATS backend not connected");
    }

    yield* Effect.tryPromise({
      try: () => manager.streams.info(streamName),
      catch: (error) => natsLookupError(`stream-info:${streamName}`, error),
    }).pipe(
      Effect.catchIf(
        isMissingLookupError,
        () =>
          Effect.tryPromise({
            try: () =>
              manager.streams.add({
                name: streamName,
                subjects: [wildcardSubject],
              }),
            catch: (error) => pubSubError(`stream-add:${streamName}`, error),
          }),
        (error) => Effect.fail(pubSubError(error.operation, error.cause)),
      ),
    );
    MutableHashSet.add(initializedStreams, streamName);
    return streamName;
  });

  return {
    createProducer: Effect.fn("NatsBackend.createProducer")(function*<T>(options: CreateProducerOptions<T>) {
      yield* ensureConnected();
      yield* ensureStream(options.topic);
      const client = js;
      if (client === null) {
        return yield* pubSubError("create-producer", "NATS backend not connected");
      }
      return makeNatsProducer<T>(client, options.topic, options.schema);
    }),
    createConsumer: Effect.fn("NatsBackend.createConsumer")(function*<T>(options: CreateConsumerOptions<T>) {
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
      yield* consumer.init.pipe(
        Effect.mapError((error) => pubSubError(`init-consumer:${options.topic}`, error)),
      );
      return consumer;
    }),
    close: Effect.gen(function* () {
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
  };
}

export const makeNatsBackendScoped = (url = "nats://localhost:4222") =>
  Effect.acquireRelease(
    Effect.sync(() => makeNatsBackend(url)),
    (backend) =>
      backend.close.pipe(
        Effect.catch((error) =>
          Effect.logError("[NatsBackend] Failed to close scoped backend", {
            error: error.message,
            operation: error.operation,
          })
        ),
      ),
  );
