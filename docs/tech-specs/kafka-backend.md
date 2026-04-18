---
layout: default
title: "Kafka Pub/Sub Backend Technical Specification"
parent: "Tech Specs"
---

# Kafka Pub/Sub Backend Technical Specification

## Overview

Add Apache Kafka as a third pub/sub backend alongside Pulsar and RabbitMQ.
Kafka's topic model maps naturally to TrustGraph's pub/sub abstraction:
topics are first-class, consumer groups provide competing-consumer
semantics, and the AdminClient handles topic lifecycle.

## Problem

TrustGraph currently supports Pulsar and RabbitMQ. Kafka is widely
deployed and operationally familiar to many teams. Its log-based
architecture provides durable, replayable message streams with
well-understood scaling properties.

## Design

### Concept Mapping

| TrustGraph concept | Kafka equivalent |
|---|---|
| Topic (`class:topicspace:topic`) | Kafka topic (named `topicspace.class.topic`) |
| Subscription (competing consumers) | Consumer group |
| `create_topic` / `delete_topic` | `AdminClient.create_topics()` / `delete_topics()` |
| `ensure_topic` | `AdminClient.create_topics()` (idempotent) |
| Producer | `KafkaProducer` |
| Consumer | `KafkaConsumer` in a consumer group |
| Message acknowledge | Commit offset |
| Message negative acknowledge | Seek back to message offset |

### Topic Naming

The topic name follows the same convention as the RabbitMQ exchange
name:

```
class:topicspace:topic  ->  topicspace.class.topic
```

Examples:
- `flow:tg:text-completion-request` -> `tg.flow.text-completion-request`
- `request:tg:librarian` -> `tg.request.librarian`
- `response:tg:config` -> `tg.response.config`

### Topic Classes and Retention

Kafka topics are always durable (log-based). The class prefix determines
retention policy rather than durability:

| Class | Retention | Partitions | Notes |
|---|---|---|---|
| `flow` | Long or infinite | 1 | Data pipeline, order preserved |
| `request` | Short (e.g. 300s) | 1 | RPC requests, ephemeral |
| `response` | Short (e.g. 300s) | 1 | RPC responses, shared (see below) |
| `notify` | Short (e.g. 300s) | 1 | Broadcast signals |

Single partition per topic preserves message ordering and makes
offset-based acknowledgment equivalent to per-message ack. This matches
the current `prefetch_count=1` model used across all backends.

### Producers

Straightforward `KafkaProducer` wrapping. Messages are serialised as
JSON (consistent with the RabbitMQ backend). Message properties/headers
map to Kafka record headers.

### Consumers

#### Flow and Request Class (Competing Consumers)

Consumer group ID = subscription name. Multiple consumers in the same
group share the workload (Kafka's native consumer group rebalancing).

```
group_id = subscription  # e.g. "triples-store--default--input"
```

#### Response and Notify Class (Per-Subscriber)

This is where Kafka differs from RabbitMQ. Kafka has no anonymous
exclusive auto-delete queues.

Design: use a **shared response topic with unique consumer groups**.
Each subscriber gets its own consumer group (using the existing
UUID-based subscription name from `RequestResponseSpec`). Every
subscriber reads all messages from the topic and filters by correlation
ID, discarding non-matching messages.

This is slightly wasteful — N subscribers each read every response — but
request/response traffic is low-volume compared to the data pipeline.
The alternative (per-instance temporary topics) would require dynamic
topic creation/deletion for every API gateway request, which is
expensive in Kafka (AdminClient operations involve controller
coordination).

### Acknowledgment

#### Acknowledge (Success)

Commit the message's offset. With a single partition and sequential
processing, this is equivalent to per-message ack:

```
consumer.commit(offsets={partition: offset + 1})
```

#### Negative Acknowledge (Failure / Retry)

Kafka has no native nack-with-redelivery. On processing failure, seek
the consumer back to the failed message's offset:

```
consumer.seek(partition, offset)
```

The message is redelivered on the next poll. This matches the current
RabbitMQ `basic_nack(requeue=True)` behaviour: the message is retried
by the same consumer.

### Topic Lifecycle

The flow service creates and deletes topics via the Kafka AdminClient:

- **Flow start**: `AdminClient.create_topics()` for each unique topic
  in the blueprint. Topic config includes `retention.ms` based on class.
- **Flow stop**: `AdminClient.delete_topics()` for the flow's topics.
- **Service startup**: `ensure_topic` creates the topic if it doesn't
  exist (idempotent via `create_topics` with `validate_only=False`).

Unlike RabbitMQ where consumers declare their own queues, Kafka topics
must exist before consumers connect. The flow service and service
startup `ensure_topic` calls handle this.

### Message Encoding

JSON body, consistent with the RabbitMQ backend. Serialisation uses the
existing `dataclass_to_dict` / `dict_to_dataclass` helpers. Message
properties map to Kafka record headers (byte-encoded string values).

### Configuration

New CLI arguments following the existing pattern:

```
--pubsub-backend kafka
--kafka-bootstrap-servers localhost:9092
--kafka-security-protocol PLAINTEXT
--kafka-sasl-mechanism (optional)
--kafka-sasl-username (optional)
--kafka-sasl-password (optional)
```

The factory in `pubsub.py` creates a `KafkaBackend` instance when
`pubsub_backend='kafka'`.

### Dependencies

`kafka-python-ng` or `confluent-kafka`. The `confluent-kafka` package
provides both producer/consumer and AdminClient in one library with
better performance (C-backed librdkafka), but requires a C extension
build. `kafka-python-ng` is pure Python, simpler to install.

## Key Design Decisions

1. **Shared response topic with filtering** over per-instance temporary
   topics. Avoids expensive dynamic topic creation for every RPC
   exchange. Acceptable because response traffic is low-volume.

2. **Seek-back for negative acknowledge** over not-committing or retry
   topics. Provides immediate redelivery consistent with the RabbitMQ
   nack behaviour.

3. **Single partition per topic** to preserve ordering and simplify
   offset management. Parallelism comes from multiple topics and
   multiple services, not from partitioning within a topic.

4. **Retention-based class semantics** instead of durability flags.
   Kafka topics are always durable; short retention achieves the
   ephemeral behaviour needed for request/response/notify classes.

## Open Questions

- **Retention values**: exact `retention.ms` for short-lived topic
  classes. 300s (5 minutes) is a starting point; may need tuning based
  on worst-case restart/reconnect times.

- **Library choice**: `confluent-kafka` vs `kafka-python-ng`. Performance
  vs install simplicity trade-off. Could support both behind a thin
  wrapper.

- **Consumer poll timeout**: needs to align with the existing
  `receive(timeout_millis)` API. Kafka's `poll()` takes a timeout
  directly, so this maps cleanly.
