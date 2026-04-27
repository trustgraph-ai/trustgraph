---
layout: default
title: "Pub/Sub Abstraction: Broker-Independent Messaging"
parent: "Tech Specs"
---

# Pub/Sub Abstraction: Broker-Independent Messaging

## Problem

TrustGraph's messaging infrastructure is deeply coupled to Apache Pulsar in ways that go beyond the transport layer. This coupling creates several concrete problems.

### 1. Schema system is Pulsar-native

Every message type in the system is defined as a `pulsar.schema.Record` subclass using Pulsar field types (`String()`, `Integer()`, `Boolean()`, etc.). This means:

- The `pulsar` Python package is a build dependency for `trustgraph-base`, even though `trustgraph-base` contains no transport logic
- Any code that imports a message schema transitively depends on Pulsar
- The schema definitions cannot be reused with a different broker without the Pulsar library installed
- What's actually happening on the wire is JSON serialisation — the Pulsar schema machinery adds complexity without adding value over plain JSON encode/decode

### 2. Translators are named after the broker

The translator layer that converts between internal Python objects and wire format uses methods called `to_pulsar()` and `from_pulsar()`. These are really just JSON encode/decode operations — they have nothing to do with Pulsar specifically. The naming creates a false impression that the translation is broker-specific, when in reality any broker that carries JSON payloads would use identical logic.

### 3. Queue names use Pulsar URI format

Queue identifiers throughout the codebase use Pulsar's `persistent://tenant/namespace/topic` or `non-persistent://tenant/namespace/topic` URI format. These are hardcoded in schema definitions and referenced across services. RabbitMQ, Redis Streams, or any other broker would use completely different naming conventions. There is no abstraction between the logical identity of a queue and its broker-specific address.

### 4. Broker selection is not configurable

There is no mechanism to select a different pub/sub backend at deployment time. The Pulsar client is instantiated directly in the gateway and via `PulsarClient` in the base processor. Switching to a different broker would require code changes across multiple packages, not a configuration change.

### 5. Architectural requirements are implicit

TrustGraph relies on specific pub/sub behaviours — shared subscriptions for load balancing, message acknowledgement for reliability, message properties for correlation — but these requirements are not documented. This makes it difficult to evaluate whether a candidate broker (RabbitMQ, Redis Streams, NATS, etc.) actually satisfies the system's needs, or where the gaps would be.

## Design Goals

### Goal 1: Remove the link between Pulsar schemas and application code

Message types should be plain Python objects (dataclasses) that know how to serialise to and from JSON. The `pulsar.schema.Record` base class and Pulsar field types should not appear in schema definitions. The pub/sub transport layer sends and receives JSON bytes; the schema layer handles the mapping between JSON and typed Python objects independently.

### Goal 2: Remove `to_pulsar` / `from_pulsar` naming

The translator methods should reflect what they actually do: encode a Python object to a JSON-compatible dict, and decode a JSON-compatible dict back to a Python object. The naming should be broker-neutral (e.g. `encode` / `decode`, or `to_dict` / `from_dict`).

### Goal 3: Schema objects provide encode/decode

Each message type should be a Python dataclass (or similar) with a well-defined mapping to and from JSON. For example:

```python
@dataclass
class TextCompletionRequest:
    system: str
    prompt: str
    streaming: bool = False
```

Given `{"system": "You are helpful", "prompt": "Hello", "streaming": false}` on the wire, decoding produces an object where `request.system` is `"You are helpful"`, `request.prompt` is `"Hello"`, and `request.streaming` is `False`. Encoding does the reverse. This is the schema's concern, not the broker's.

### Goal 4: Abstract queue naming

Queue identifiers should not use Pulsar URI format (`persistent://tg/flow/topic`). A broker-neutral naming scheme is needed so that each backend can map logical queue names to its native format. The right approach here is not yet clear and needs to be worked through — considerations include how to express quality-of-service, multi-tenancy, and namespace separation without leaking broker concepts.

### Goal 5: Document pub/sub architectural requirements

TrustGraph's actual requirements from the pub/sub layer need to be formally specified. This includes:

- **Delivery semantics**: Which queues need at-least-once delivery? Are any fire-and-forget?
- **Consumer patterns**: Shared subscriptions (competing consumers for load balancing), exclusive subscriptions, fan-out/broadcast
- **Message acknowledgement**: Positive ack, negative ack (redelivery), timeout-based redelivery
- **Message properties**: Key-value metadata on messages used for correlation (e.g. request IDs, flow routing)
- **Ordering guarantees**: Per-topic ordering, per-key ordering, or no ordering required
- **Message size**: Typical and maximum message sizes (some payloads include base64-encoded documents)
- **Persistence**: Which messages must survive broker restarts
- **Consumer positioning**: Ability to consume from earliest (replay) vs latest (live tail)
- **Connection model**: Long-lived connections with reconnection, or transient

Documenting these requirements makes it possible to evaluate RabbitMQ or any other candidate against concrete criteria rather than discovering gaps during implementation.

## Pub/Sub Architectural Requirements (As-Is)

This section documents what TrustGraph currently needs from its pub/sub layer. These are the as-is requirements — some may be revisited or relaxed in a future design if it makes broker portability easier.

### Consumer model

All consumers use **shared subscriptions** (competing consumers). Multiple instances of the same processor read from the same subscription, and each message is delivered to exactly one instance. This is the load-balancing mechanism.

No exclusive or failover subscriptions are used anywhere in the codebase, despite infrastructure support for them.

Consumers support configurable concurrency — multiple async tasks within a single process can independently call `receive()` on the same subscription.

### Delivery semantics

Almost all queues are **non-persistent / best-effort (q0)**. The only persistent queue is `config_push_queue` (q2, exactly-once), which pushes full configuration state to processors. Since config pushes are idempotent (full state, not deltas), the persistence requirement here is about surviving broker restarts, not about exactly-once semantics per se.

Flow processing queues (request/response pairs for LLM, RAG, agent, etc.) are all non-persistent. Messages in flight are lost on broker restart. This is acceptable because:

- Requests originate from a client that will time out and retry
- There is no durable work-in-progress that would be corrupted by message loss
- The system is designed for real-time query processing, not batch pipelines

### Message acknowledgement

**Positive acknowledgement**: After successful handler execution, the message is acknowledged. This removes it from the subscription.

**Negative acknowledgement**: On handler failure (unhandled exception or rate-limit timeout), the message is negatively acknowledged, which triggers redelivery by the broker. Rate-limited messages retry for up to 7200 seconds before giving up and negatively acknowledging.

**Orphaned messages**: In the request-response subscriber pattern, messages that arrive with no matching waiter (e.g. the requester timed out) are positively acknowledged and discarded. This prevents redelivery storms.

### Message properties

Messages carry a small set of key-value string properties as metadata, separate from the payload. The primary use is a `"id"` property for request-response correlation — the requester generates a unique ID, attaches it as a property, and the responder echoes it back so the subscriber can match responses to waiters.

Agent orchestration correlation (`correlation_id`, `parent_session_id`) is carried in the message payload, not in properties.

### Consumer positioning

Two modes are used:

- **Earliest**: The configuration consumer starts from the beginning of the topic to receive full configuration history on startup. This is the only use of earliest positioning.
- **Latest** (default): All flow consumers start from the current position, processing only new messages.

### Message ordering

**Not required.** The codebase explicitly does not depend on message ordering:

- Shared subscriptions distribute messages across consumers without ordering guarantees
- Concurrent handler tasks within a consumer process messages in arbitrary order
- Request-response correlation uses IDs, not positional ordering
- The supervisor fan-out/fan-in pattern collects results in a dictionary, order-independent
- Configuration pushes are full state snapshots, not ordered deltas

### Message sizes

Most messages are small JSON payloads (< 10KB). The exceptions:

- **Document content**: Large documents (PDFs, text files) can be sent through the chunking service with base64 encoding. Pulsar's chunking feature (`chunking_enabled`) handles automatic splitting of oversized messages.
- **Agent observations**: LLM-generated text can be several KB but rarely exceeds typical message size limits.

A replacement broker needs to either support large messages natively or provide a chunking/streaming mechanism. Alternatively, the large-document path could be refactored to use a side-channel (e.g. object store reference) instead of inline payload.

### Fan-out patterns

**Supervisor fan-out**: One supervisor request decomposes into N independent sub-agent requests, each emitted as a separate message on the agent request queue. Different agent instances pick them up via the shared subscription. A correlation ID links the completions back to the original decomposition. This is not pub/sub fan-out (one message to many consumers) — it's application-level fan-out (many messages to one queue).

**Request-response isolation**: Each client creates a unique subscription name on response queues so it only receives its own responses. This means the response queue effectively has many independent subscribers, each seeing a filtered subset of messages based on the `"id"` property match.

### Reconnection and resilience

Reconnection logic lives in the Consumer/Producer/Publisher/Subscriber classes, not in the broker client. These classes handle:

- Automatic reconnection on connection loss
- Retry loops with backoff
- Graceful shutdown (unsubscribe, close)

The broker client itself is expected to provide a basic connection that can fail, and the wrapper classes handle recovery. This is important for the abstraction — the backend interface can be simple because resilience is handled above it.

### Queue inventory

| Queue | Persistence | Purpose |
|-------|-------------|---------|
| config push | Persistent (q2) | Full configuration state broadcast |
| config request/response | Non-persistent | Configuration queries |
| flow request/response | Non-persistent | Flow management |
| knowledge request/response | Non-persistent | Knowledge graph operations |
| librarian request/response | Non-persistent | Document storage operations |
| document embeddings request/response | Non-persistent | Document vector queries |
| row embeddings request/response | Non-persistent | Row vector queries |
| collection request/response | Non-persistent | Collection management |

Additionally, each processing service (LLM, RAG, agent, prompt, embeddings, etc.) has dynamically defined request/response queue pairs configured at deployment time.

### Summary of hard requirements for a replacement broker

1. **Shared subscription / competing consumers** — multiple consumers on one queue, each message delivered to exactly one
2. **Message acknowledgement** — positive ack (remove from queue) and negative ack (trigger redelivery)
3. **Message properties** — key-value metadata on messages, at minimum a string `"id"` field
4. **Two consumer start positions** — from beginning of topic and from current position
5. **Persistence for at least one queue** — config state must survive broker restart
6. **Messages up to several MB** — or a chunking mechanism for large payloads
7. **No ordering requirement** — simplifies broker selection significantly

## Candidate Brokers

A quick assessment of alternatives against the hard requirements above.

### RabbitMQ

The primary candidate. Mature, widely deployed, well understood.

- **Competing consumers**: Yes — multiple consumers on a queue, round-robin delivery. This is RabbitMQ's native model.
- **Acknowledgement**: Yes — `basic.ack` and `basic.nack` with requeue flag.
- **Message properties**: Yes — headers and properties on every message. The `correlation_id` and `message_id` fields are first-class concepts.
- **Consumer positioning**: Yes, via RabbitMQ Streams (3.9+). Streams are append-only logs that support reading from any offset — beginning, end, or timestamp. Classic queues are consumed destructively (no replay), but streams solve this cleanly. The `state` queue class maps to a RabbitMQ stream. Additionally, the Last Value Cache Exchange plugin can retain the most recent message per routing key for new consumers.
- **Persistence**: Yes — durable queues and persistent messages survive broker restart.
- **Large messages**: No hard limit but not designed for very large payloads. Practical limit around 128MB with default config. Adequate for current use.
- **Ordering**: FIFO per queue (stronger than required).
- **Operational complexity**: Low. Single binary, no ZooKeeper/BookKeeper dependencies. Significantly simpler to operate than Pulsar.
- **Ecosystem**: Excellent client libraries, management UI, mature tooling.

**Gaps**: None significant. RabbitMQ Streams cover the replay/earliest positioning requirement.

### Apache Kafka

High-throughput distributed log. More infrastructure than TrustGraph likely needs.

- **Competing consumers**: Yes — consumer groups with partition assignment.
- **Acknowledgement**: Yes — offset commits. No per-message negative ack; failed messages require application-level retry or dead-letter handling.
- **Message properties**: Yes — message headers (key-value byte arrays).
- **Consumer positioning**: Yes — seek to earliest or latest offset. Supports full replay.
- **Persistence**: Yes — all messages are persisted to the log by default.
- **Large messages**: Configurable (`max.message.bytes`), default 1MB, can be increased. Large payloads are discouraged by design.
- **Ordering**: Per-partition ordering (stronger than required).
- **Operational complexity**: High. Requires ZooKeeper (or KRaft), partition management, replication config. Overkill for typical TrustGraph deployments.
- **Ecosystem**: Excellent client libraries, schema registry, Connect framework.

**Gaps**: No native negative acknowledgement. Operational complexity is high for small-to-medium deployments. Partition count must be planned upfront for parallelism.

### Redis Streams

Lightweight option using Redis as a message broker.

- **Competing consumers**: Yes — consumer groups with `XREADGROUP`.
- **Acknowledgement**: Yes — `XACK`. Pending entries list tracks unacknowledged messages. No explicit negative ack but unacknowledged messages can be claimed after timeout via `XAUTOCLAIM`.
- **Message properties**: No native separation between properties and payload. Would need to encode properties as fields within the stream entry or in the payload.
- **Consumer positioning**: Yes — `0` (earliest) or `$` (latest) on group creation.
- **Persistence**: Yes — Redis persistence (RDB/AOF), though Redis is primarily an in-memory system.
- **Large messages**: Practical limit tied to Redis memory. Not suited for large payloads.
- **Ordering**: Per-stream ordering (stronger than required).
- **Operational complexity**: Low if Redis is already in the stack. No additional infrastructure.

**Gaps**: No native message properties. Memory-bound. Persistence depends on Redis configuration. Not a natural fit for message broker patterns.

### NATS / NATS JetStream

Lightweight, high-performance messaging. JetStream adds persistence.

- **Competing consumers**: Yes — queue groups in core NATS; consumer groups in JetStream.
- **Acknowledgement**: JetStream only — `Ack`, `Nak` (with redelivery), `InProgress` (extend timeout).
- **Message properties**: Yes — message headers (key-value).
- **Consumer positioning**: JetStream — deliver all, deliver last, deliver new, deliver by sequence/time.
- **Persistence**: JetStream only. Core NATS is fire-and-forget.
- **Large messages**: Default 1MB, configurable up to 64MB.
- **Ordering**: Per-subject ordering.
- **Operational complexity**: Very low. Single binary, no dependencies. Clustering is straightforward.

**Gaps**: Requires JetStream for persistence and acknowledgement. Smaller ecosystem than RabbitMQ/Kafka.

### Assessment Summary

| Requirement | RabbitMQ | Kafka | Redis Streams | NATS JetStream |
|---|---|---|---|---|
| Competing consumers | Yes | Yes | Yes | Yes |
| Positive/negative ack | Yes | Partial | Partial | Yes |
| Message properties | Yes | Yes | No | Yes |
| Earliest positioning | Yes (Streams) | Yes | Yes | Yes |
| Persistence | Yes | Yes | Partial | Yes |
| Large messages | Yes | Configurable | No | Configurable |
| Operational simplicity | Good | Poor | Good | Good |

**RabbitMQ** is the strongest candidate given TrustGraph's requirements and deployment profile. The only gap (earliest consumer positioning for config) has known workarounds. Operational simplicity is a significant advantage over Pulsar.

## Approach

### Current state

The codebase has already undergone a partial abstraction. The picture is better than the problem statement might suggest:

- **Backend abstraction exists**: `backend.py` defines Protocol-based interfaces (`PubSubBackend`, `BackendProducer`, `BackendConsumer`, `Message`). The Pulsar implementation lives in `pulsar_backend.py`.
- **Schemas are already dataclasses**: Message types in `schema/services/*.py` are plain Python dataclasses with type hints, not Pulsar `Record` subclasses. This was the hardest part of the old spec and it's done.
- **Serialization is JSON-based**: `pulsar_backend.py` contains `dataclass_to_dict()` and `dict_to_dataclass()` helpers that handle the round-trip. The wire format is JSON.
- **Factory pattern exists**: `pubsub.py` has `get_pubsub()` which creates a backend from configuration. Currently only Pulsar is implemented.
- **Consumer/Producer/Publisher/Subscriber are backend-agnostic**: These classes accept a `backend` parameter and delegate transport operations to it. They own retry, reconnection, metrics, and concurrency.

What remains is cleanup, not a rewrite.

### What needs to change

#### 1. Rename translator methods

The translator base class (`messaging/translators/base.py`) defines `to_pulsar()` and `from_pulsar()` as abstract methods. Every translator implements these. The methods convert between external API dicts and internal dataclass objects — nothing Pulsar-specific happens in them.

**Change**: Rename to `decode()` (external dict → dataclass) and `encode()` (dataclass → external dict). Update all translator subclasses and all call sites.

This is a mechanical rename. The method bodies don't change.

#### 2. Rename translator base classes

The base classes `Translator`, `MessageTranslator`, and `SendTranslator` reference "pulsar" in docstrings and parameter names. Clean these up so the naming reflects what the layer actually does: translating between the external API representation (JSON dicts from HTTP/WebSocket) and the internal schema (dataclasses).

#### 3. Move serialization out of the Pulsar backend

`dataclass_to_dict()` and `dict_to_dataclass()` currently live in `pulsar_backend.py` but are not Pulsar-specific. They handle the conversion between dataclasses and JSON-compatible dicts, which every backend needs.

**Change**: Move these to a shared location (e.g. `trustgraph/base/serialization.py` or alongside the schema definitions). The backend interface sends and receives dicts; serialization to/from dataclasses happens at a layer above.

This means the backend Protocol simplifies: `send()` accepts a dict and properties, `value()` returns a dict. The Consumer/Producer layer handles dataclass ↔ dict conversion using the shared serializers.

#### 4. Abstract queue naming

Queue names currently use the format `q0/tg/flow/queue-name` or `q2/tg/config/queue-name`, which the Pulsar backend maps to `non-persistent://tg/flow/queue-name` or `persistent://tg/config/queue-name`.

This is an open design question. Options:

**Option A: Simple string names.** Queues are just strings like `"text-completion-request"`. The backend is responsible for mapping to its native format (Pulsar adds `persistent://tg/flow/` prefix, RabbitMQ uses the string as-is or adds a vhost prefix). Persistence and namespace are configuration concerns, not embedded in the name.

**Option B: Structured queue descriptor.** A small object that carries the logical name plus metadata:

```python
@dataclass
class QueueDescriptor:
    name: str                    # e.g. "text-completion-request"
    namespace: str = "flow"      # logical grouping
    persistent: bool = False     # must survive broker restart
```

The backend maps this to its native format.

**Option C: Keep the current format** (`q0/tg/flow/name`) but document it as a TrustGraph convention, not a Pulsar convention. Backends parse it.

Option B is the most explicit. Option A is the simplest. Either is workable. The key constraint is that persistence is a property of the queue definition, not a runtime choice — the config push queue is persistent, everything else is not.

#### 5. Implement RabbitMQ backend

Write `rabbitmq_backend.py` implementing the `PubSubBackend` Protocol:

- **`create_producer()`**: Creates a channel and declares the target queue. `send()` publishes to the default exchange with the queue name as routing key. Properties map to AMQP basic properties (specifically `message_id` for the `"id"` property).
- **`create_consumer()`**: Declares the queue and starts consuming with `basic_consume`. Shared subscription is the default RabbitMQ model — multiple consumers on one queue get round-robin delivery. `acknowledge()` maps to `basic_ack`, `negative_acknowledge()` maps to `basic_nack` with `requeue=True`.
- **Persistence**: For persistent queues, declare as durable with `delivery_mode=2` on messages. For non-persistent queues, declare as non-durable.
- **Consumer positioning**: RabbitMQ queues are consumed destructively, so "earliest" doesn't apply in the Pulsar sense. For the config push use case, use a **fanout exchange with per-consumer exclusive queues** — each new processor gets its own queue that receives all config publishes, plus the last-value can be handled by having the config service re-publish on startup.
- **Large messages**: RabbitMQ handles messages up to `rabbit.max_message_size` (default 128MB). No chunking needed.

The factory in `pubsub.py` gets a new branch:

```python
if backend_type == 'rabbitmq':
    return RabbitMQBackend(
        host=config.get('rabbitmq_host'),
        port=config.get('rabbitmq_port'),
        username=config.get('rabbitmq_username'),
        password=config.get('rabbitmq_password'),
        vhost=config.get('rabbitmq_vhost', '/'),
    )
```

Backend selection via `PUBSUB_BACKEND=rabbitmq` environment variable or `--pubsub-backend rabbitmq` CLI flag.

#### 6. Clean up remaining Pulsar references

After the above changes, Pulsar-specific code should be confined to:

- `pulsar_backend.py` — the Pulsar implementation
- `pubsub.py` — the factory that imports it

Audit and remove any remaining Pulsar imports, Pulsar exception handling, or Pulsar-specific concepts from:

- `async_processor.py` (currently catches `_pulsar.Interrupted`)
- `consumer.py`, `subscriber.py` (if any Pulsar exceptions leak through)
- Schema files (should be clean already, but verify)
- Gateway service (currently instantiates Pulsar client directly)

The gateway is a special case — it currently bypasses the abstraction layer and creates a Pulsar client directly for dispatching API requests. It should use the same `get_pubsub()` factory as everything else.

### What stays the same

- **Schema definitions**: Already dataclasses. No changes needed.
- **Consumer/Producer/Publisher/Subscriber**: Already backend-agnostic. No changes to their core logic.
- **FlowProcessor and spec wiring**: Already uses `processor.pubsub` to create backend instances. No changes.
- **Backend Protocol**: The interface in `backend.py` is sound. Minor refinement possible (dict vs dataclass at the boundary) but the shape is right.

### Concrete cleanups

The following files have Pulsar-specific imports that should not be there after the abstraction is complete. Pulsar imports should be confined to `pulsar_backend.py` and the factory in `pubsub.py`.

**Dead imports (unused, can just be removed):**

- `trustgraph-base/trustgraph/base/pubsub.py` — `from pulsar.schema import JsonSchema`, `import pulsar`, `import _pulsar`. The `JsonSchema` import is unused since the switch to `BytesSchema`. The `pulsar`/`_pulsar` imports are only used by the legacy `PulsarClient` class which should be removed (superseded by `PulsarBackend`).
- `trustgraph-base/trustgraph/base/flow_processor.py` — `from pulsar.schema import JsonSchema`. Unused.

**Legacy `PulsarClient` class:**

- `trustgraph-base/trustgraph/base/pubsub.py` — The `PulsarClient` class is a leftover from before the backend abstraction. `get_pubsub()` still references `PulsarClient.default_pulsar_host` for defaults. Move the defaults to `PulsarBackend` or to environment variable reads in the factory, then delete `PulsarClient`.

**Client libraries using Pulsar directly:**

- `trustgraph-base/trustgraph/clients/base.py` — `import pulsar`, `import _pulsar`, `from pulsar.schema import JsonSchema`. This is the base class for the old synchronous client library. These clients predate the backend abstraction and use Pulsar directly.
- `trustgraph-base/trustgraph/clients/embeddings_client.py` — `from pulsar.schema import JsonSchema`, `import _pulsar`.
- `trustgraph-base/trustgraph/clients/*.py` (agent, config, document_embeddings, document_rag, graph_embeddings, graph_rag, llm, prompt, row_embeddings, triples_query) — all import `_pulsar` for exception handling.

These clients are the internal request-response clients used by processors. They need to be migrated to use the backend abstraction or their Pulsar exception handling needs to be wrapped behind a backend-agnostic exception type.

**Translator base class:**

- `trustgraph-base/trustgraph/messaging/translators/base.py` — `from pulsar.schema import Record`. Used in type hints. Should be removed when `to_pulsar`/`from_pulsar` are renamed.

**Gateway service (bypasses abstraction):**

- `trustgraph-flow/trustgraph/gateway/service.py` — `import pulsar`. Creates a Pulsar client directly.
- `trustgraph-flow/trustgraph/gateway/config/receiver.py` — `import pulsar`. Direct Pulsar usage.

The gateway should use `get_pubsub()` like everything else.

**Storage writers:**

- `trustgraph-flow/trustgraph/storage/triples/neo4j/write.py` — `import pulsar`
- `trustgraph-flow/trustgraph/storage/triples/memgraph/write.py` — `import pulsar`
- `trustgraph-flow/trustgraph/storage/triples/falkordb/write.py` — `import pulsar`
- `trustgraph-flow/trustgraph/storage/triples/cassandra/write.py` — `import pulsar`

These need investigation — likely Pulsar exception handling or direct client usage that should go through the abstraction.

**Log level:**

- `trustgraph-base/trustgraph/log_level.py` — `import _pulsar`. Used to set Pulsar's log level. Should be moved into `pulsar_backend.py`.

### Queue naming

The current scheme encodes QoS, tenant, namespace, and queue name into a slash-separated string (`q0/tg/request/config`) which the Pulsar backend parses and maps to a Pulsar URI (`non-persistent://tg/request/config`). This was an attempt at abstraction but it has problems:

- QoS in the name was a mistake — it's a property of the queue definition, not something that belongs in the name. A queue is either persistent or it isn't; that's decided once when the queue is defined.
- The tenant/namespace structure mirrors Pulsar's model. RabbitMQ doesn't use this — it has vhosts and exchange/queue names. Pretending the naming isn't TrustGraph-specific just leaks Pulsar concepts.
- The `topic()` helper generates these strings, and the backend parses them apart. This is unnecessary indirection.

There are two categories of queue in TrustGraph:

**Infrastructure queues** — defined in code, used for system services. These are fixed and well-known:

| Queue | Persistent | Purpose |
|-------|------------|---------|
| `config-request` | No | Config queries |
| `config-response` | No | Config query responses |
| `config-push` | Yes | Config state broadcast |
| `flow-request` | No | Flow management queries |
| `flow-response` | No | Flow management responses |
| `librarian-request` | No | Document storage operations |
| `librarian-response` | No | Document storage responses |
| `knowledge-request` | No | Knowledge graph operations |
| `knowledge-response` | No | Knowledge graph responses |
| `document-embeddings-request` | No | Document vector queries |
| `document-embeddings-response` | No | Document vector responses |
| `row-embeddings-request` | No | Row vector queries |
| `row-embeddings-response` | No | Row vector responses |
| `collection-request` | No | Collection management |
| `collection-response` | No | Collection management responses |

**Flow queues** — defined in configuration, created dynamically per flow. The queue names come from the config service (e.g. `text-completion-request`, `graph-rag-request`, `agent-request`). Each flow instance has its own set of these queues.

For infrastructure queues, the name is just a string. Persistence is a property of the queue definition, not encoded in the name. The backend maps the name to whatever its native format requires.

For flow queues, the name comes from configuration. The config service already distributes queue names as strings — the backend just needs to be able to use them.

#### Proposed scheme: CLASS:TOPICSPACE:TOPIC

A queue name has three parts separated by colons:

- **CLASS** — a small enum that defines the queue's operational characteristics. The backend knows what each class means in terms of persistence, TTL, memory limits, etc. There are only four classes:

  | Class | Persistent | TTL | Behaviour |
  |-------|------------|-----|-----------|
  | `flow` | Yes | Long | Processing pipeline queues. Messages survive broker restart. |
  | `request` | No | Short | Transient request-response. Low TTL, no persistence needed — clients retry on failure. |
  | `response` | No | Short | Same as request, for the response side. |
  | `state` | Yes | Retained | Last-value state broadcast. Consumers need the most recent value on startup, plus any future updates. Config push is the primary example. |

- **TOPICSPACE** — deployment isolation. Keeps different TrustGraph deployments separate when sharing the same pub/sub infrastructure. Most deployments just use `tg`. Avoids the overloaded terms "tenant" and "namespace".

- **TOPIC** — the logical queue identity. What the queue is for.

**Examples:**

```
flow:tg:text-completion-request
flow:tg:graph-rag-request
flow:tg:agent-request
request:tg:librarian
response:tg:librarian
request:tg:config
response:tg:config
state:tg:config
request:tg:flow
response:tg:flow
```

**Backend mapping:**

Each backend parses the three parts and maps them to its native concepts:

- **Pulsar**: `flow:tg:text-completion-request` → `persistent://tg/flow/text-completion-request`. Class maps to persistent/non-persistent and namespace. State class uses persistent topic with earliest consumer positioning.
- **RabbitMQ**: Topicspace maps to vhost. Class determines queue durability and TTL policy. State class uses a last-value queue (via plugin) or a fanout exchange pattern where each consumer gets the retained state on connect.
- **Kafka**: `flow.tg.text-completion-request` as topic name. Class determines retention and compaction policy. State class maps to a compacted topic (last value per key).

**Why this works:**

- The class enum is small and stable — adding a new class is rare and deliberate
- Queue properties (persistence, TTL) are implied by class, not encoded in the name
- Dynamic registration works naturally — the config service publishes `flow:tg:text-completion-request` and the backend knows how to declare it from the `flow` class
- The colon separator is unambiguous, easy to split, doesn't conflict with URIs or path separators that backends use internally
- No pretence of being generic — this is a TrustGraph convention, and that's fine

### Serialization boundary

**Decision: the backend owns the wire format.**

The contract between the Consumer/Producer layer and the backend is dataclass objects in, dataclass objects out:

- `send()` accepts a dataclass instance and properties dict
- `receive()` returns a message whose `value()` is a dataclass instance

What happens on the wire is the backend's concern. The Pulsar backend uses JSON (via `dataclass_to_dict` / `dict_to_dataclass`). A RabbitMQ backend would likely also use JSON. A future backend could use Protobuf, MessagePack, or Avro if the broker benefits from it.

The serialization helpers stay inside the backend that uses them — they are not shared infrastructure. Each backend brings its own serialization strategy. The Consumer/Producer layer never thinks about wire format.

### Gateway service

**Decision: the gateway uses the backend abstraction like any other component.**

The gateway currently bridges WebSocket/REST to Pulsar directly, bypassing the abstraction layer. It translates incoming API JSON to Pulsar schema objects, sends them, receives responses as Pulsar schema objects, and translates back to API JSON. Since the wire format is JSON in both directions, this is effectively a no-op round trip through the schema machinery.

With the backend abstraction, the gateway follows the same pattern as every other component:

1. Incoming API JSON → translator `decode()` → dataclass
2. Dataclass → backend `send()` (backend handles wire format)
3. Backend `receive()` → dataclass
4. Dataclass → translator `encode()` → API JSON → WebSocket/REST client

This is architecturally simple — one code path, no special cases. The gateway depends on the schema dataclasses and the translator layer, which it already does. The overhead of deserialize-then-reserialize is negligible for the message sizes involved. And it keeps all options open — if a future backend uses a non-JSON wire format, the gateway still works without changes.

## Implementation Order

### Phase 1: Rename translators

Rename `to_pulsar()` → `decode()`, `from_pulsar()` → `encode()` across all translator classes and call sites. Remove `from pulsar.schema import Record` from the translator base class. Mechanical find-and-replace, no behavioural changes.

### Phase 2: Queue naming

Replace the `topic()` helper with the CLASS:TOPICSPACE:TOPIC scheme. Update all queue definitions in `schema/services/*.py` and `schema/knowledge/*.py`. Update `PulsarBackend.map_topic()` to parse the new format. Verify all existing functionality still works with Pulsar.

### Phase 3: Clean up Pulsar leaks

Work through the concrete cleanups list: remove dead imports, delete the legacy `PulsarClient` class, migrate the client libraries and gateway to use the backend abstraction. After this phase, `pulsar` imports exist only in `pulsar_backend.py`.

### Phase 4: RabbitMQ backend

Implement `rabbitmq_backend.py` against the existing `PubSubBackend` Protocol. Map queue classes to RabbitMQ concepts: `flow` → durable queues, `request`/`response` → non-durable queues with TTL, `state` → RabbitMQ streams. Add `rabbitmq` as a backend option in the factory. Test end-to-end with `PUBSUB_BACKEND=rabbitmq`.

Phases 1-3 are safe to do on main — they don't change behaviour, just clean up. Phase 4 is additive — it adds a new backend without touching the existing one.

### Config distribution on RabbitMQ

The `state` queue class needs "start from earliest" semantics — a newly started processor must receive the current configuration state.

RabbitMQ Streams (available since 3.9) solve this directly. Streams are persistent, append-only logs that support consumer offset positioning. The RabbitMQ backend maps the `state` class to a stream, and consumers attach with offset `first` to read from the beginning, or `last` to read the most recent entry plus future updates.

Since config pushes are full state snapshots (not deltas), a consumer only needs the most recent entry. The RabbitMQ backend can use `last` offset positioning for `state` class consumers, which delivers the last message in the stream followed by any new messages. This matches the current behaviour where processors read config on startup and then react to updates.
