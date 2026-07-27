---
layout: default
title: "Async Receive: Eliminating Thread-per-Consumer Architecture"
parent: "Tech Specs"
---

# Async Receive: Eliminating Thread-per-Consumer Architecture

## Problem

TrustGraph's pub/sub Consumer and Subscriber classes use a
thread-per-connection model that does not scale. Each Consumer and each
Subscriber creates a dedicated `ThreadPoolExecutor(max_workers=1)` to
run Pulsar's blocking `receive()` call off the asyncio event loop.
This means every consumer-side object in the system costs one OS
thread that sits in a blocking receive loop for the lifetime of the
object.

### 1. Thread count grows linearly with flows

A typical FlowProcessor creates 2-3 consumer-side objects per flow
(input Consumer, Subscriber for RequestResponse, Consumer for
LibrarianClient). With 40 workspaces and 4 flows per workspace, a
single processor group creates ~480 OS threads just for receive loops.
At this scale, containers hit the OS thread limit and fail with
`RuntimeError: can't start new thread`.

### 2. Flow lifecycle is heavyweight

Starting a flow means creating Pulsar consumers, each with a dedicated
thread and executor. Stopping a flow means tearing them down. This
makes workspace and flow provisioning an expensive operation —
creating a Pulsar subscription is a broker roundtrip, and spawning an
OS thread has kernel overhead. What should be a lightweight routing
change (start listening on a new topic) becomes a heavyweight
infrastructure operation.

### 3. Sequential startup amplifies the cost

Flows are started sequentially: workspaces are processed one at a
time, and within each workspace, flows are started one at a time.
`Subscriber.start()` blocks until the underlying Pulsar consumer is
ready (a synchronous `client.subscribe()` wrapped in
`run_in_executor`). This serialises hundreds of broker roundtrips that
are independent of each other. The result is progressive slowdown:
early workspaces start in under a second, later workspaces take tens
of seconds each, because the event loop is increasingly loaded by
background receive loops from already-started flows.

### 4. Producer creation blocks the event loop

`Producer.send()` lazily creates the Pulsar producer on first call via
a synchronous `self.backend.create_producer()` directly on the asyncio
event loop — unlike Consumer and Subscriber, which at least use
`run_in_executor`. Every Producer's first send blocks the entire event
loop for the duration of the broker roundtrip. This includes the
config service sending responses, meaning it blocks config delivery to
all other services.

### 5. The threading is unnecessary for Pulsar

Pulsar's Python client exposes `consumer.receive_async()`, which
returns a coroutine that is directly awaitable in asyncio. Using this,
a consumer receive loop becomes a pure async task with zero OS threads:

```python
async def consumer_loop(consumer):
    while running:
        msg = await consumer.receive_async()
        await handler(msg)
```

The current architecture pays the full cost of OS threads and
executors to work around a blocking API when a non-blocking
alternative exists. The only operation that genuinely requires a
thread is the initial `client.subscribe()` call, which is synchronous
and returns the consumer object.

### Impact

At 10 workspaces (40 flows), the system functions but is already
running hundreds of threads. At 40 workspaces (160 flows), containers
fail to start due to thread exhaustion. The target operating range for
TrustGraph is 50+ workspaces, which is unreachable under the current
architecture.

## Design Goals

### Goal 1: Eliminate OS threads from the receive path

Consumer and Subscriber receive loops must not require a dedicated OS
thread per connection. For Pulsar, use `receive_async()` which is
directly awaitable in asyncio. For RabbitMQ, reduce to the minimum
thread count the backend requires (pika's `BlockingConnection` is not
thread-safe, but a single connection can consume from multiple queues
via multiple `basic_consume()` calls driven by one
`process_data_events()` loop). The target is O(1) threads per backend,
not O(n) threads per consumer.

### Goal 2: Work within the existing pub/sub framework

The solution must operate within the existing backend abstraction
(`PubSubBackend`, `BackendConsumer`, `BackendProducer`). Both the
Pulsar and RabbitMQ backends must continue to work. The backend
interface may be extended (e.g. adding an async receive method) but
the abstraction boundary between application code and broker-specific
code must be preserved.

### Goal 3: Make flow lifecycle lightweight

Starting or stopping a flow should be a low-cost operation — closer
to updating a routing table than to creating broker connections and
spawning threads. The cost of managing 200 flows should not be
qualitatively different from managing 20.

### Goal 4: Do not block the asyncio event loop with broker I/O

All broker operations that involve network roundtrips — subscribing,
producing, sending — must be off the event loop. This includes
producer creation, which currently runs synchronously on the event
loop in `Producer.send()`.

## Backend API Analysis

The current `BackendConsumer` and `PubSubBackend` protocols
(`backend.py`) were designed around a synchronous,
one-connection-per-consumer model. Several aspects are challenged by
the design goals.

### 1. `BackendConsumer.receive()` is synchronous

The protocol defines `receive(timeout_millis) -> Message` as a
blocking call. This is the reason Consumer and Subscriber need threads
in the first place. To use Pulsar's `receive_async()`, we need an
async receive path. But the protocol can't simply change to async
because RabbitMQ's pika `BlockingConnection` has no awaitable receive
— pika requires a thread calling `process_data_events()`.

The backend abstraction needs to express that some backends can deliver
messages asynchronously (Pulsar) while others require a thread-driven
pump (RabbitMQ). This could be an optional `receive_async()` method on
`BackendConsumer`, or the backend could push messages into an
asyncio queue via `call_soon_threadsafe` and the consumer protocol
shifts from pull to push.

### 2. `create_consumer` and `create_producer` are synchronous

`PubSubBackend.create_consumer()` and `create_producer()` are sync
methods that perform broker roundtrips (Pulsar `client.subscribe()`,
pika `BlockingConnection()`). They are called from async code but
block the event loop or require `run_in_executor` wrapping at the
call site. The protocol doesn't express that these are potentially
expensive I/O operations.

### 3. One consumer per topic, no dynamic subscription management

`create_consumer()` creates a standalone consumer for a single topic.
There is no way to add or remove topic subscriptions from an existing
consumer. Starting a flow means creating new consumer objects;
stopping means destroying them. For the lightweight lifecycle goal,
and for future wildcard subscriptions, the API would need to support
either multi-topic consumers or a subscription registry that can be
modified at runtime.

### 4. Acknowledge threading constraints are implicit

`BackendConsumer.acknowledge()` and `negative_acknowledge()` are sync
methods with no documented threading requirements. But for RabbitMQ,
acknowledgement must happen on the same thread that owns the pika
connection — a constraint that the protocol doesn't express and that
callers (Consumer, Subscriber) must work around. Moving to a
push-based model where the backend owns the receive thread would let
the backend also own acknowledgement, keeping the threading constraint
internal.

### 5. `BackendProducer.send()` is synchronous

The protocol defines `send()` as sync, but it performs network I/O.
The application layer wraps it in `asyncio.to_thread` (in
`Producer.send()`) or calls it bare on the event loop (in
`Publisher.run()`). An async send at the protocol level would let
backends optimise — Pulsar could use its native async send, RabbitMQ
could batch publishes on its connection thread.

### Assessment

The current protocol assumes a pull-based, one-thread-per-consumer
model. Goals 1 and 3 require moving toward either a push-based model
(backend delivers messages into async queues) or an async-capable
protocol (optional `receive_async`). Goal 5 requires the concept of
dynamic subscription management, which the current one-consumer-per-
topic API does not support. The protocol needs extension, but the
changes can be additive — existing sync methods remain for backends
that need them, with new async methods for backends that can use them.

### Goal 5: Support future wildcard subscriptions

The design should accommodate a future extension where a consumer can
subscribe to a topic pattern (e.g. all flows for a workspace, or all
workspaces for a processor type) rather than individual topics. This
is not in scope for the initial implementation, but the architecture
should not preclude it.

## Technical Design: Backend API

The backend API is refactored to be async-first. The backend is
responsible for broker communication only — connecting, subscribing,
sending, acknowledging. Threading and concurrency management belong in
the `base/` layer, not the backend.

### Principles

1. All methods that perform broker I/O are `async`. The backend
   handles its own threading internally (Pulsar uses
   `receive_async()`, RabbitMQ runs a single pika thread) — the
   application layer never creates threads for broker operations.

2. `receive()` is awaitable. The caller does
   `msg = await consumer.receive()` with no timeout. Shutdown is
   handled by cancelling the task, not by polling with timeouts.

3. `acknowledge()` and `negative_acknowledge()` are async. For
   Pulsar these are near-instant. For RabbitMQ the backend routes the
   ack to the pika connection thread and awaits confirmation. Either
   way, the threading constraint is the backend's problem, not the
   caller's.

4. The factory methods `create_consumer()` and `create_producer()` are
   async, since both perform broker roundtrips.

### `BackendConsumer` protocol

```python
@runtime_checkable
class BackendConsumer(Protocol):

    async def receive(self) -> Message:
        """Await the next message.

        Blocks until a message is available. Does not time out —
        shutdown is signalled by cancelling the awaiting task.

        Pulsar: delegates to consumer.receive_async().
        RabbitMQ: awaits an asyncio.Queue fed by the pika thread.
        """
        ...

    async def acknowledge(self, message: Message) -> None:
        """Acknowledge successful processing.

        Pulsar: calls consumer.acknowledge() (thread-safe).
        RabbitMQ: routes basic_ack to the pika thread.
        """
        ...

    async def negative_acknowledge(self, message: Message) -> None:
        """Negative acknowledge — triggers redelivery.

        Pulsar: calls consumer.negative_acknowledge() (thread-safe).
        RabbitMQ: routes basic_nack to the pika thread.
        """
        ...

    async def close(self) -> None:
        """Close the consumer and release broker resources."""
        ...
```

The synchronous `ensure_connected()` and `unsubscribe()` methods are
removed. Connection readiness is guaranteed by `create_consumer()`
returning only when the subscription is active.  Unsubscription is
handled by `close()`.

The `timeout_millis` parameter on `receive()` is removed. The current
architecture uses timeouts as a polling mechanism to check shutdown
flags — with async tasks, cancellation replaces polling. This
eliminates the 250ms/2000ms wake-up cycles that generate thousands of
no-op callbacks per second on the event loop.

### `BackendProducer` protocol

```python
@runtime_checkable
class BackendProducer(Protocol):

    async def send(self, message: Any, properties: dict = {}) -> None:
        """Send a message.

        Pulsar: uses async send or asyncio.to_thread.
        RabbitMQ: routes publish to the pika thread.
        """
        ...

    async def close(self) -> None:
        """Close the producer and release broker resources."""
        ...
```

`flush()` is removed as a separate method — `close()` flushes before
closing. The sync `send()` that blocked the event loop is replaced by
an async method; the backend owns the decision of how to get the
bytes to the broker without blocking the event loop.

### `PubSubBackend` protocol

```python
@runtime_checkable
class PubSubBackend(Protocol):

    async def create_consumer(
        self, topic: str, subscription: str, schema: type,
        initial_position: str = 'latest', **options,
    ) -> BackendConsumer:
        """Create a consumer subscribed to a topic.

        Returns only when the subscription is active and ready to
        receive messages. The broker roundtrip is off the event loop.
        """
        ...

    async def create_producer(
        self, topic: str, schema: type, **options,
    ) -> BackendProducer:
        """Create a producer bound to a topic.

        Returns only when the producer is ready to send. The broker
        roundtrip is off the event loop.
        """
        ...

    async def create_topic(self, topic: str) -> None: ...
    async def delete_topic(self, topic: str) -> None: ...
    async def topic_exists(self, topic: str) -> bool: ...
    async def ensure_topic(self, topic: str) -> None: ...
    async def close(self) -> None: ...
```

`create_consumer()` and `create_producer()` become async. For Pulsar,
these wrap the synchronous `client.subscribe()` /
`client.create_producer()` in `asyncio.to_thread`. For RabbitMQ, they
schedule queue declaration and binding on the pika connection thread.

`close()` becomes async to allow clean shutdown of backend-internal
threads (e.g. the RabbitMQ pika pump thread).

### Backend-internal threading

Everything in the runtime layer — receiver tasks, workers, sender
tasks — is async. The `base/` layer never creates OS threads. If a
backend needs an OS thread to bridge a blocking client library, that
is the backend's internal concern, invisible to the application layer.

**Pulsar**: Zero OS threads. `receive_async()` is natively awaitable.
`client.subscribe()` and `client.create_producer()` are wrapped in
`asyncio.to_thread` for the initial setup call; the thread is
released immediately after. Acknowledgement calls are thread-safe in
the Pulsar C++ client and can run directly.

**RabbitMQ**: One OS thread, owned by the backend. A single pika
`BlockingConnection` drives `process_data_events()` in a loop. All
consumer subscriptions (`basic_consume`) are registered on this
connection. Incoming messages are pushed to per-consumer
`asyncio.Queue` instances via `loop.call_soon_threadsafe()`.
Acknowledgement and publish commands are submitted to the pika thread
via a thread-safe command queue and executed during the next
`process_data_events()` cycle. From the `base/` layer's perspective,
the RabbitMQ backend's `receive()` is just another awaitable — the OS
thread is an implementation detail.

### Message protocol

`Message` is unchanged:

```python
@runtime_checkable
class Message(Protocol):
    def value(self) -> Any: ...
    def properties(self) -> dict: ...
```

Backend-specific acknowledgement state (Pulsar message ID, RabbitMQ
delivery tag) is carried internally by the backend's `Message`
implementation. The application layer never interacts with it
directly — it passes the opaque `Message` back to `acknowledge()` or
`negative_acknowledge()`.

### Migration path

The existing sync protocol methods can coexist with the new async
methods during migration. Consumer and Subscriber can be updated
incrementally to use the async API while the sync path remains
available for any code that hasn't been migrated. Once all callers use
the async API, the sync methods can be removed.

## Technical Design: Runtime Layer

The backend API describes how to talk to the broker. This section
describes the runtime components in `base/` that sit between the
backend and application handlers — who creates what, when, and how
messages flow from broker to handler and back.

There are two managed runtimes: one for receiving (consumer side) and
one for sending (producer side). The processor's base class starts
these runtimes and application code interacts with them by adding and
removing registrations.

### Component overview

```
                          ┌─────────────┐
                          │  Processor  │
                          │  (base class)│
                          └──────┬──────┘
                     starts      │      starts
                ┌────────────────┼────────────────┐
                ▼                                  ▼
        ┌───────────────┐                 ┌───────────────┐
        │ ReceiverPool  │                 │  SenderPool   │
        └───────┬───────┘                 └───────┬───────┘
                │                                  │
     add/remove │ consumer                add/remove│ producer
     registrations│                      registrations│
                │                                  │
        ┌───────┴───────┐                 ┌────────┴──────┐
        │  receiver     │                 │   sender      │
        │  tasks (async)│                 │   task (async) │
        └───┬───────┬───┘                 └────────┬──────┘
            │       ▲                              │
    messages│       │ack/nack              ┌───────┴───────┐
            │       │(completion queue)    │   Backend     │
            ▼       │                     │   Producer    │
        ┌───────────┴───┐                 │   .send()     │
        │  work queue   │                 └───────────────┘
        └───────┬───────┘
                │
        ┌───────┴───────┐
        │ worker tasks  │
        │ (concurrency) │
        └───────┬───────┘
                │
        ┌───────┴───────┐
        │   Backend     │
        │   Consumer    │
        │   .receive()  │
        └───────────────┘
```

### Message flow and acknowledgement

Workers must not perform any pub/sub communication. The receiver
task owns both receiving and acknowledging for its consumer — this
is required by some pub/sub systems where ack must happen in the
same context as receive.

The flow for each message:

1. **Receiver task** calls `await backend_consumer.receive()`, gets a
   message.
2. **Receiver task** creates an `asyncio.Future` for this message and
   puts `(message, handler, future)` on the **work queue**. The
   receiver immediately loops back to `receive()` — it does not wait.
3. **Worker task** pulls from the work queue, calls the handler, and
   sets the future result (success) or exception (failure). The worker
   never touches the backend.
4. **Receiver task** also monitors a **completion queue** fed by
   resolved futures. When a future completes, the receiver calls
   `acknowledge()` or `negative_acknowledge()` on its own backend
   consumer.

The receiver task multiplexes between receiving new messages and
processing completions. If ack and receive can happen in separate
coroutines (to be validated per backend), the completion handling
is a spawned coroutine. If they must be in the same coroutine, the
receiver selects between both using `asyncio.wait`:

```python
async def receiver_loop(self, backend_consumer, handler):
    pending_acks = set()
    receive_task = asyncio.create_task(backend_consumer.receive())

    while self.running:
        # Wait for either a new message or a completed worker
        wait_set = {receive_task} | pending_acks
        done, _ = await asyncio.wait(
            wait_set, return_when=asyncio.FIRST_COMPLETED,
        )

        for task in done:
            if task is receive_task:
                # New message — dispatch to worker
                msg = task.result()
                future = asyncio.Future()
                await self.work_queue.put((msg, handler, future))

                # Track the future for ack/nack
                ack_task = asyncio.create_task(
                    self._wait_for_completion(future, msg)
                )
                pending_acks.add(ack_task)

                # Immediately request next message
                receive_task = asyncio.create_task(
                    backend_consumer.receive()
                )
            else:
                # Worker completed — ack or nack
                pending_acks.discard(task)
                msg, success = task.result()
                if success:
                    await backend_consumer.acknowledge(msg)
                else:
                    await backend_consumer.negative_acknowledge(msg)

async def _wait_for_completion(self, future, msg):
    try:
        await future
        return (msg, True)
    except Exception:
        return (msg, False)
```

This keeps all broker communication in the receiver coroutine. The
worker's only responsibility is to process the message and resolve
the future.

### ReceiverPool

The ReceiverPool is started once by the processor base class. It
manages the consumer side: broker subscriptions, message routing, and
worker dispatch.

#### 1. Starting the pool

The processor calls `await receiver_pool.start()` during
initialisation. This creates the worker tasks (async coroutines,
number set by the concurrency parameter) which immediately begin
waiting on the shared work queue. No broker connections are created
at this point — those happen when consumers are registered.

#### 2. Adding a consumer registration

Application code (e.g. flow startup) calls:

```python
registration = await receiver_pool.add_consumer(
    topic="flow:tg:text-completion-request:ws1:default",
    subscription="text-completion",
    schema=TextCompletionRequest,
    handler=self.on_request,
)
```

This does the following:
- Calls `backend.create_consumer()` to create the broker subscription
  (async — no event loop blocking).
- Creates an asyncio task that loops on
  `await backend_consumer.receive()`, placing received messages onto
  an internal work queue along with the handler and consumer reference
  (needed for ack/nack).
- The receiver task is a lightweight coroutine, not an OS thread.

Multiple registrations can be added concurrently. Each gets its own
receiver task and its own broker consumer, but they all feed into the
same work queue.

With wildcard subscriptions (future), `add_consumer` could subscribe
once to a pattern topic. Adding a second consumer on a matching topic
would update the routing table without creating a new broker
subscription. The receiver task inspects the topic on each message
and dispatches to the right handler. This is not in scope for the
initial implementation, but the add/remove registration model supports
it.

#### 3. Worker dispatch

The pool runs a fixed number of worker tasks (set by a concurrency
parameter). Each worker loops:

```python
async def worker(self):
    while self.running:
        msg, handler, future = await self.work_queue.get()
        try:
            await handler(msg, ...)
            future.set_result(None)
        except Exception as e:
            future.set_exception(e)
```

Workers pull from the shared work queue, call the handler, and
signal completion by resolving the future. Workers never interact
with the backend — acknowledgement is handled by the receiver task
that owns the backend consumer (see Message flow above).

The number of workers controls how many messages are processed
concurrently across all consumers in the pool. This replaces the
per-Consumer concurrency setting with a pool-wide setting.

#### 4. Removing a consumer registration

Application code (e.g. flow shutdown) calls:

```python
await receiver_pool.remove_consumer(registration)
```

This:
- Cancels the receiver task for that consumer (the `await
  backend_consumer.receive()` is cancelled, the task exits cleanly).
- Calls `backend_consumer.close()` to release the broker subscription.
- Any in-flight messages from this consumer that are already on the
  work queue are still processed and acknowledged normally.

No threads are created or destroyed. No heavyweight teardown.

#### 5. Stopping the pool

The processor calls `receiver_pool.stop()` during shutdown. This:
- Cancels all receiver tasks.
- Waits for workers to drain the work queue (with a timeout).
- Closes all backend consumers.
- Cancels worker tasks.

### SenderPool

The SenderPool is started once by the processor base class. It
manages the producer side: broker connections and async send dispatch.

#### 1. Starting the pool

The processor calls `await sender_pool.start()` during initialisation.
This creates the sender task (an async coroutine that pulls from the
send queue and dispatches to backend producers). No broker connections
are created at this point — those happen when producers are
registered.

#### 2. Adding a producer registration

Application code calls:

```python
producer = await sender_pool.add_producer(
    topic="flow:tg:text-completion-response:ws1:default",
    schema=TextCompletionResponse,
)
```

This:
- Calls `backend.create_producer()` to create the broker producer
  (async — no event loop blocking).
- Returns a handle that the application uses to send messages.

#### 3. Sending a message

The application calls:

```python
await producer.send(message, properties={"id": request_id})
```

This places the message on an internal asyncio send queue. A sender
task pulls from this queue and calls `backend_producer.send()`. The
send queue decouples the application's send call from the broker I/O,
so the application never blocks on broker latency.

For low-latency request-response patterns where the caller needs to
know the send succeeded before waiting for a response, the send can
optionally await completion:

```python
await producer.send(message, properties={"id": id}, wait=True)
```

#### 4. Removing a producer registration

```python
await sender_pool.remove_producer(producer)
```

This:
- Drains any pending messages on the send queue for this producer.
- Calls `backend_producer.close()` to release the broker connection.

#### 5. Stopping the pool

The processor calls `sender_pool.stop()` during shutdown. This:
- Drains all send queues (with a timeout).
- Closes all backend producers.

### Flow lifecycle under the new model

With the pool model, starting and stopping a flow becomes:

```python
async def start_flow(self, workspace, flow, defn):
    registrations = []
    for spec in self.specifications:
        reg = await spec.register(
            self.receiver_pool, self.sender_pool,
            workspace, flow, defn,
        )
        registrations.append(reg)
    self.flows[(workspace, flow)] = registrations

async def stop_flow(self, workspace, flow):
    for reg in self.flows.pop((workspace, flow)):
        await reg.unregister()
```

Each spec's `register()` method calls `add_consumer` and/or
`add_producer` on the pools. No threads are created. No executors.
The broker subscription is the only heavyweight operation, and it
happens asynchronously.

Starting 200 flows means 200 `add_consumer` calls, each creating an
async receiver task. The broker subscriptions can be parallelised
with `asyncio.gather`. The total startup cost is bounded by the
broker's ability to process subscriptions, not by Python thread
creation.

### Extracting Consumer

The current `Consumer` class manages its own receive loop,
`ThreadPoolExecutor`, and `consume_from_queue`. Under the pool model,
all of this collapses — the receive loop becomes a receiver task in
the pool, the executor is eliminated, and message dispatch goes
through the shared work queue and worker tasks.

## Technical Design: Request/Response

Request/Response is a separate pattern from the consumer/worker
model. It is used when a processor, while handling a message in a
worker, needs to call out to another service and wait for a reply.
Examples: SPARQL querying the triples store, a processor fetching
config, a handler calling the librarian.

Request/Response does not use the ReceiverPool or worker tasks. It
has its own lightweight infrastructure: a producer for sending
requests, a dedicated receiver coroutine for responses, and a routing
table that matches responses to waiting callers.

### Architecture

```
    Worker (handling a message)
        │
        │ await rr_client.request(req)
        │
        ▼
    ┌──────────────────────┐
    │  RequestResponse     │
    │  client              │
    │                      │
    │  pending: {          │
    │    id1: Future,      │
    │    id2: Future,      │
    │    ...               │
    │  }                   │
    └──┬───────────────┬───┘
       │               │
  send │          receive
  request         response
       │               │
       ▼               ▼
  ┌─────────┐   ┌─────────────┐
  │ Backend │   │  Backend    │
  │ Producer│   │  Consumer   │
  │ .send() │   │  .receive() │
  └─────────┘   └─────────────┘
```

### How it works

#### 1. Setup

When a flow starts and includes a RequestResponseSpec, the spec
creates a RequestResponse client:

```python
rr_client = await RequestResponseClient.create(
    backend=backend,
    request_topic="request:tg:triples:ws1:default",
    response_topic="response:tg:triples:ws1:default",
    request_schema=TriplesRequest,
    response_schema=TriplesResponse,
)
```

This:
- Creates a backend producer for the request topic (async).
- Creates a backend consumer for the response topic (async).
- Starts a receiver coroutine that loops on
  `await backend_consumer.receive()` and routes responses by ID.

The receiver coroutine is a pure async task — no OS thread, no
worker pool involvement.

#### 2. Making a request

A worker calls:

```python
response = await rr_client.request(my_request, timeout=60)
```

This:
- Generates a UUID for the request.
- Creates an `asyncio.Future` and adds it to the pending dict:
  `self.pending[id] = future`.
- Sends the request via the backend producer with the ID in message
  properties.
- Awaits the future with a timeout.

The worker is suspended (but the event loop continues — other
workers, receivers, and coroutines keep running).

#### 3. Receiving the response

The receiver coroutine runs independently:

```python
async def _response_loop(self):
    while self.running:
        msg = await self.backend_consumer.receive()
        id = msg.properties().get("id")
        future = self.pending.pop(id, None)
        if future is not None:
            future.set_result(msg.value())
        await self.backend_consumer.acknowledge(msg)
```

When a response arrives, the receiver looks up the request ID in the
pending dict, resolves the corresponding future, and acknowledges the
message. The worker that was awaiting the future wakes up and
continues processing.

There is no work queue, no worker dispatch, no completion queue. The
receiver's only job is matching responses to waiting callers. The
ack happens in the receiver coroutine, satisfying the same-context
constraint.

Messages with no matching pending ID (e.g. stale responses after a
timeout) are acknowledged and discarded.

#### 4. Timeouts

If a response does not arrive within the timeout,
`asyncio.wait_for` cancels the future. The caller gets a
`TimeoutError`. The pending entry is cleaned up:

```python
async def request(self, req, timeout=60):
    id = str(uuid.uuid4())
    future = asyncio.Future()
    self.pending[id] = future
    await self.producer.send(req, properties={"id": id})
    try:
        return await asyncio.wait_for(future, timeout=timeout)
    except asyncio.TimeoutError:
        self.pending.pop(id, None)
        raise
```

If a response arrives after the timeout, the receiver finds no
matching entry in the pending dict and discards it.

#### 5. Teardown

When the flow stops:

```python
await rr_client.close()
```

This:
- Cancels the receiver coroutine.
- Closes the backend consumer and producer.
- Any pending futures are cancelled (callers get `CancelledError`).

#### Relationship to the consumer/worker model

The two patterns are independent:

- **Consumer pattern** (ReceiverPool + workers): for processing
  incoming messages that arrive on this processor's input queues.
  Uses the work queue, worker pool, and completion-based ack flow.

- **Request/Response pattern** (RequestResponseClient): for calling
  out to other services during message processing. Uses a dedicated
  receiver coroutine with direct future routing. No worker
  involvement.

A typical flow has both: a consumer registration in the ReceiverPool
for its input queue, and one or more RequestResponse clients for
services it depends on. The worker handles the incoming message and
calls `await rr_client.request()` as needed during processing.

The LibrarianClient follows the same pattern — it is a specialised
request/response client with additional logic for streaming responses
and document assembly. It can be refactored onto the same
RequestResponseClient infrastructure.

## Backpressure

The work queue in the ReceiverPool is an `asyncio.Queue` with
`maxsize` set to the number of worker tasks. When all workers are
busy, the queue is full. The receiver task's
`await work_queue.put(...)` blocks, which means the receiver stops
calling `await backend_consumer.receive()`. Messages accumulate in
the broker, where they have proper persistence, redelivery, and
backpressure mechanisms.

No messages accumulate in Python memory beyond the worker pool size.
The broker is the backlog, not the application.

The same applies to the SenderPool: the send queue has a bounded
size. If the broker is slow to accept messages, `await
send_queue.put(...)` blocks the caller, applying backpressure up
to the worker or application code.

## Reconnection and Error Handling

Reconnection is the backend's responsibility. If the broker
connection drops, the backend's `receive()` implementation handles
reconnection internally and resumes delivering messages. The
receiver task in the `base/` layer just sees `await receive()` take
longer than usual — it does not need retry logic.

The same applies to `send()`: the backend reconnects and retries
transparently.

For errors that are not recoverable by the backend (e.g. the topic
has been deleted, authentication revoked), `receive()` or `send()`
raises an exception. The receiver task or sender task logs the error
and can be restarted by the pool, or the error propagates up to the
processor for a full restart.

## Config Fetch at Startup

`AsyncProcessor.fetch_and_apply_config()` creates short-lived
RequestResponse clients to fetch configuration from the config
service before flows are started. Under the new model, these become
short-lived `RequestResponseClient` instances:

```python
async def fetch_and_apply_config(self):
    rr_client = await RequestResponseClient.create(
        backend=self.backend,
        request_topic=config_request_queue,
        response_topic=config_response_queue,
        request_schema=ConfigRequest,
        response_schema=ConfigResponse,
    )
    try:
        resp = await rr_client.request(
            ConfigRequest(operation="getkeys-all-ws", ...),
            timeout=60,
        )
        # ... process config ...
    finally:
        await rr_client.close()
```

This works naturally with the new architecture. The client creates a
backend producer and consumer (async, no threads), runs a receiver
coroutine for the duration of the fetch, and tears down cleanly.
The retry loop in `fetch_and_apply_config` continues to handle the
case where the config service is not yet available on cold start.

## Assumptions

- **`receive_async()` is available**: Pulsar's Python client exposes
  `receive_async()` on consumer objects, returning an awaitable
  coroutine. This is confirmed in the Pulsar documentation.

- **Ack can happen in a different coroutine**: Pulsar's
  `consumer.acknowledge()` does not need to be called from the same
  asyncio coroutine that called `receive_async()`. All coroutines
  run on the same OS thread (the event loop thread), and the Pulsar
  C++ client is thread-safe, so acknowledgement from any coroutine
  is valid. If this assumption proves wrong, the fallback is the
  `asyncio.wait` multiplexing pattern described in the Message Flow
  section, where the receiver coroutine handles acks directly.

## Open Questions

- **Shared vs per-flow RequestResponse clients**: Some processors
  create one RequestResponse client per flow (e.g. TriplesClient).
  If multiple flows in the same workspace call the same service,
  they could potentially share a single RequestResponseClient.
  This is an optimisation, not a requirement — individual clients
  work correctly and can be consolidated later if needed.
