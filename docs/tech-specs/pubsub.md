# Pub/Sub Infrastructure

## Overview

This document catalogs all connections between the TrustGraph codebase and the pub/sub infrastructure. Currently, the system is hardcoded to use Apache Pulsar. This analysis identifies all integration points to inform future refactoring toward a configurable pub/sub abstraction.

## Current State: Pulsar Integration Points

### 1. Direct Pulsar Client Usage

**Location:** `trustgraph-flow/trustgraph/gateway/service.py`

The API gateway directly imports and instantiates the Pulsar client:

- **Line 20:** `import pulsar`
- **Lines 54-61:** Direct instantiation of `pulsar.Client()` with optional `pulsar.AuthenticationToken()`
- **Lines 33-35:** Default Pulsar host configuration from environment variables
- **Lines 178-192:** CLI arguments for `--pulsar-host`, `--pulsar-api-key`, and `--pulsar-listener`
- **Lines 78, 124:** Passes `pulsar_client` to `ConfigReceiver` and `DispatcherManager`

This is the only location that directly instantiates a Pulsar client outside of the abstraction layer.

### 2. Base Processor Framework

**Location:** `trustgraph-base/trustgraph/base/async_processor.py`

The base class for all processors provides Pulsar connectivity:

- **Line 9:** `import _pulsar` (for exception handling)
- **Line 18:** `from . pubsub import PulsarClient`
- **Line 38:** Creates `pulsar_client_object = PulsarClient(**params)`
- **Lines 104-108:** Properties exposing `pulsar_host` and `pulsar_client`
- **Line 250:** Static method `add_args()` calls `PulsarClient.add_args(parser)` for CLI arguments
- **Lines 223-225:** Exception handling for `_pulsar.Interrupted`

All processors inherit from `AsyncProcessor`, making this the central integration point.

### 3. Consumer Abstraction

**Location:** `trustgraph-base/trustgraph/base/consumer.py`

Consumes messages from queues and invokes handler functions:

**Pulsar imports:**
- **Line 12:** `from pulsar.schema import JsonSchema`
- **Line 13:** `import pulsar`
- **Line 14:** `import _pulsar`

**Pulsar-specific usage:**
- **Lines 100, 102:** `pulsar.InitialPosition.Earliest` / `pulsar.InitialPosition.Latest`
- **Line 108:** `JsonSchema(self.schema)` wrapper
- **Line 110:** `pulsar.ConsumerType.Shared`
- **Lines 104-111:** `self.client.subscribe()` with Pulsar-specific parameters
- **Lines 143, 150, 65:** `consumer.unsubscribe()` and `consumer.close()` methods
- **Line 162:** `_pulsar.Timeout` exception
- **Lines 182, 205, 232:** `consumer.acknowledge()` / `consumer.negative_acknowledge()`

**Spec file:** `trustgraph-base/trustgraph/base/consumer_spec.py`
- **Line 22:** References `processor.pulsar_client`

### 4. Producer Abstraction

**Location:** `trustgraph-base/trustgraph/base/producer.py`

Sends messages to queues:

**Pulsar imports:**
- **Line 2:** `from pulsar.schema import JsonSchema`

**Pulsar-specific usage:**
- **Line 49:** `JsonSchema(self.schema)` wrapper
- **Lines 47-51:** `self.client.create_producer()` with Pulsar-specific parameters (topic, schema, chunking_enabled)
- **Lines 31, 76:** `producer.close()` method
- **Lines 64-65:** `producer.send()` with message and properties

**Spec file:** `trustgraph-base/trustgraph/base/producer_spec.py`
- **Line 18:** References `processor.pulsar_client`

### 5. Publisher Abstraction

**Location:** `trustgraph-base/trustgraph/base/publisher.py`

Asynchronous message publishing with queue buffering:

**Pulsar imports:**
- **Line 2:** `from pulsar.schema import JsonSchema`
- **Line 6:** `import pulsar`

**Pulsar-specific usage:**
- **Line 52:** `JsonSchema(self.schema)` wrapper
- **Lines 50-54:** `self.client.create_producer()` with Pulsar-specific parameters
- **Lines 101, 103:** `producer.send()` with message and optional properties
- **Lines 106-107:** `producer.flush()` and `producer.close()` methods

### 6. Subscriber Abstraction

**Location:** `trustgraph-base/trustgraph/base/subscriber.py`

Provides multi-recipient message distribution from queues:

**Pulsar imports:**
- **Line 6:** `from pulsar.schema import JsonSchema`
- **Line 8:** `import _pulsar`

**Pulsar-specific usage:**
- **Line 55:** `JsonSchema(self.schema)` wrapper
- **Line 57:** `self.client.subscribe(**subscribe_args)`
- **Lines 101, 136, 160, 167-172:** Pulsar exceptions: `_pulsar.Timeout`, `_pulsar.InvalidConfiguration`, `_pulsar.AlreadyClosed`
- **Lines 159, 166, 170:** Consumer methods: `negative_acknowledge()`, `unsubscribe()`, `close()`
- **Lines 247, 251:** Message acknowledgment: `acknowledge()`, `negative_acknowledge()`

**Spec file:** `trustgraph-base/trustgraph/base/subscriber_spec.py`
- **Line 19:** References `processor.pulsar_client`

### 7. Schema System (Heart of Darkness)

**Location:** `trustgraph-base/trustgraph/schema/`

Every message schema in the system is defined using Pulsar's schema framework.

**Core primitives:** `schema/core/primitives.py`
- **Line 2:** `from pulsar.schema import Record, String, Boolean, Array, Integer`
- All schemas inherit from Pulsar's `Record` base class
- All field types are Pulsar types: `String()`, `Integer()`, `Boolean()`, `Array()`, `Map()`, `Double()`

**Example schemas:**
- `schema/services/llm.py` (Line 2): `from pulsar.schema import Record, String, Array, Double, Integer, Boolean`
- `schema/services/config.py` (Line 2): `from pulsar.schema import Record, Bytes, String, Boolean, Array, Map, Integer`

**Topic naming:** `schema/core/topic.py`
- **Lines 2-3:** Topic format: `{kind}://{tenant}/{namespace}/{topic}`
- This URI structure is Pulsar-specific (e.g., `persistent://tg/flow/config`)

**Impact:**
- All request/response message definitions throughout the codebase use Pulsar schemas
- This includes services for: config, flow, llm, prompt, query, storage, agent, collection, diagnosis, library, lookup, nlp_query, objects_query, retrieval, structured_query
- Schema definitions are imported and used extensively across all processors and services

## Summary

### Pulsar Dependencies by Category

1. **Client instantiation:**
   - Direct: `gateway/service.py`
   - Abstracted: `async_processor.py` → `pubsub.py` (PulsarClient)

2. **Message transport:**
   - Consumer: `consumer.py`, `consumer_spec.py`
   - Producer: `producer.py`, `producer_spec.py`
   - Publisher: `publisher.py`
   - Subscriber: `subscriber.py`, `subscriber_spec.py`

3. **Schema system:**
   - Base types: `schema/core/primitives.py`
   - All service schemas: `schema/services/*.py`
   - Topic naming: `schema/core/topic.py`

4. **Pulsar-specific concepts required:**
   - Topic-based messaging
   - Schema system (Record, field types)
   - Shared subscriptions
   - Message acknowledgment (positive/negative)
   - Consumer positioning (earliest/latest)
   - Message properties
   - Initial positions and consumer types
   - Chunking support
   - Persistent vs non-persistent topics

### Refactoring Challenges

The good news: The abstraction layer (Consumer, Producer, Publisher, Subscriber) provides a clean encapsulation of most Pulsar interactions.

The challenges:
1. **Schema system pervasiveness:** Every message definition uses `pulsar.schema.Record` and Pulsar field types
2. **Pulsar-specific enums:** `InitialPosition`, `ConsumerType`
3. **Pulsar exceptions:** `_pulsar.Timeout`, `_pulsar.Interrupted`, `_pulsar.InvalidConfiguration`, `_pulsar.AlreadyClosed`
4. **Method signatures:** `acknowledge()`, `negative_acknowledge()`, `subscribe()`, `create_producer()`, etc.
5. **Topic URI format:** Pulsar's `kind://tenant/namespace/topic` structure

### Next Steps

To make the pub/sub infrastructure configurable, we need to:

1. Create an abstraction interface for the client/schema system
2. Abstract Pulsar-specific enums and exceptions
3. Create schema wrappers or alternative schema definitions
4. Implement the interface for both Pulsar and alternative systems (Kafka, RabbitMQ, Redis Streams, etc.)
5. Update `pubsub.py` to be configurable and support multiple backends
6. Provide migration path for existing deployments

## Approach Draft 1: Adapter Pattern with Schema Translation Layer

### Key Insight
The **schema system** is the deepest integration point - everything else flows from it. We need to solve this first, or we'll be rewriting the entire codebase.

### Strategy: Minimal Disruption with Adapters

**1. Keep Pulsar schemas as the internal representation**
- Don't rewrite all the schema definitions
- Schemas remain `pulsar.schema.Record` internally
- Use adapters to translate at the boundary between our code and the pub/sub backend

**2. Create a pub/sub abstraction layer:**

```
┌─────────────────────────────────────┐
│   Existing Code (unchanged)         │
│   - Uses Pulsar schemas internally  │
│   - Consumer/Producer/Publisher     │
└──────────────┬──────────────────────┘
               │
┌──────────────┴──────────────────────┐
│   PubSubFactory (configurable)      │
│   - Creates backend-specific client │
└──────────────┬──────────────────────┘
               │
        ┌──────┴──────┐
        │             │
┌───────▼─────┐  ┌────▼─────────┐
│ PulsarAdapter│  │ KafkaAdapter │  etc...
│ (passthrough)│  │ (translates) │
└──────────────┘  └──────────────┘
```

**3. Define abstract interfaces:**
- `PubSubClient` - client connection
- `PubSubProducer` - sending messages
- `PubSubConsumer` - receiving messages
- `SchemaAdapter` - translating Pulsar schemas to/from JSON or backend-specific formats

**4. Implementation details:**

For **Pulsar adapter**: Nearly passthrough, minimal translation

For **other backends** (Kafka, RabbitMQ, etc.):
- Serialize Pulsar Record objects to JSON/bytes
- Map concepts like:
  - `InitialPosition.Earliest/Latest` → Kafka's auto.offset.reset
  - `acknowledge()` → Kafka's commit
  - `negative_acknowledge()` → Re-queue or DLQ pattern
  - Topic URIs → Backend-specific topic names

### Analysis

**Pros:**
- ✅ Minimal code changes to existing services
- ✅ Schemas stay as-is (no massive rewrite)
- ✅ Gradual migration path
- ✅ Pulsar users see no difference
- ✅ New backends added via adapters

**Cons:**
- ⚠️ Still carries Pulsar dependency (for schema definitions)
- ⚠️ Some impedance mismatch translating concepts

### Alternative Consideration

Create a **TrustGraph schema system** that's pub/sub agnostic (using dataclasses or Pydantic), then generate Pulsar/Kafka/etc schemas from it. This requires rewriting every schema file and potentially breaking changes.

### Recommendation for Draft 1

Start with the **adapter approach** because:
1. It's pragmatic - works with existing code
2. Proves the concept with minimal risk
3. Can evolve to a native schema system later if needed
4. Configuration-driven: one env var switches backends

## Approach Draft 2: Backend-Agnostic Schema System with Dataclasses

### Core Concept

Use Python **dataclasses** as the neutral schema definition format. Each pub/sub backend provides its own serialization/deserialization for dataclasses, eliminating the need for Pulsar schemas to remain in the codebase.

### Schema Polymorphism at the Factory Level

Instead of translating Pulsar schemas, **each backend provides its own schema handling** that works with standard Python dataclasses.

### Publisher Flow

```python
# 1. Get the configured backend from factory
pubsub = get_pubsub()  # Returns PulsarBackend, MQTTBackend, etc.

# 2. Get schema class from the backend
# (Can be imported directly - backend-agnostic)
from trustgraph.schema.services.llm import TextCompletionRequest

# 3. Create a producer/publisher for a specific topic
producer = pubsub.create_producer(
    topic="text-completion-requests",
    schema=TextCompletionRequest  # Tells backend what schema to use
)

# 4. Create message instances (same API regardless of backend)
request = TextCompletionRequest(
    system="You are helpful",
    prompt="Hello world",
    streaming=False
)

# 5. Send the message
producer.send(request)  # Backend serializes appropriately
```

### Consumer Flow

```python
# 1. Get the configured backend
pubsub = get_pubsub()

# 2. Create a consumer
consumer = pubsub.subscribe(
    topic="text-completion-requests",
    schema=TextCompletionRequest  # Tells backend how to deserialize
)

# 3. Receive and deserialize
msg = consumer.receive()
request = msg.value()  # Returns TextCompletionRequest dataclass instance

# 4. Use the data (type-safe access)
print(request.system)   # "You are helpful"
print(request.prompt)   # "Hello world"
print(request.streaming)  # False
```

### What Happens Behind the Scenes

**For Pulsar backend:**
- `create_producer()` → creates Pulsar producer with JSON schema or dynamically generated Record
- `send(request)` → serializes dataclass to JSON/Pulsar format, sends to Pulsar
- `receive()` → gets Pulsar message, deserializes back to dataclass

**For MQTT backend:**
- `create_producer()` → connects to MQTT broker, no schema registration needed
- `send(request)` → converts dataclass to JSON, publishes to MQTT topic
- `receive()` → subscribes to MQTT topic, deserializes JSON to dataclass

**For Kafka backend:**
- `create_producer()` → creates Kafka producer, registers Avro schema if needed
- `send(request)` → serializes dataclass to Avro format, sends to Kafka
- `receive()` → gets Kafka message, deserializes Avro back to dataclass

### Key Design Points

1. **Schema object creation**: The dataclass instance (`TextCompletionRequest(...)`) is identical regardless of backend
2. **Backend handles encoding**: Each backend knows how to serialize its dataclass to the wire format
3. **Schema definition at creation**: When creating producer/consumer, you specify the schema type
4. **Type safety preserved**: You get back a proper `TextCompletionRequest` object, not a dict
5. **No backend leakage**: Application code never imports backend-specific libraries

### Example Transformation

**Current (Pulsar-specific):**
```python
# schema/services/llm.py
from pulsar.schema import Record, String, Boolean, Integer

class TextCompletionRequest(Record):
    system = String()
    prompt = String()
    streaming = Boolean()
```

**New (Backend-agnostic):**
```python
# schema/services/llm.py
from dataclasses import dataclass

@dataclass
class TextCompletionRequest:
    system: str
    prompt: str
    streaming: bool = False
```

### Backend Integration

Each backend handles serialization/deserialization of dataclasses:

**Pulsar backend:**
- Dynamically generate `pulsar.schema.Record` classes from dataclasses
- Or serialize dataclasses to JSON and use Pulsar's JSON schema
- Maintains compatibility with existing Pulsar deployments

**MQTT/Redis backend:**
- Direct JSON serialization of dataclass instances
- Use `dataclasses.asdict()` / `from_dict()`
- Lightweight, no schema registry needed

**Kafka backend:**
- Generate Avro schemas from dataclass definitions
- Use Confluent's schema registry
- Type-safe serialization with schema evolution support

### Architecture

```
┌─────────────────────────────────────┐
│   Application Code                  │
│   - Uses dataclass schemas          │
│   - Backend-agnostic                │
└──────────────┬──────────────────────┘
               │
┌──────────────┴──────────────────────┐
│   PubSubFactory (configurable)      │
│   - get_pubsub() returns backend    │
└──────────────┬──────────────────────┘
               │
        ┌──────┴──────┐
        │             │
┌───────▼─────────┐  ┌────▼──────────────┐
│ PulsarBackend   │  │ MQTTBackend       │
│ - JSON schema   │  │ - JSON serialize  │
│ - or dynamic    │  │ - Simple queues   │
│   Record gen    │  │                   │
└─────────────────┘  └───────────────────┘
```

### Implementation Details

**1. Schema definitions:** Plain dataclasses with type hints
   - `str`, `int`, `bool`, `float` for primitives
   - `list[T]` for arrays
   - `dict[str, T]` for maps
   - Nested dataclasses for complex types

**2. Each backend provides:**
   - Serializer: `dataclass → bytes/wire format`
   - Deserializer: `bytes/wire format → dataclass`
   - Schema registration (if needed, like Pulsar/Kafka)

**3. Consumer/Producer abstraction:**
   - Already exists (consumer.py, producer.py)
   - Update to use backend's serialization
   - Remove direct Pulsar imports

**4. Type mappings:**
   - Pulsar `String()` → Python `str`
   - Pulsar `Integer()` → Python `int`
   - Pulsar `Boolean()` → Python `bool`
   - Pulsar `Array(T)` → Python `list[T]`
   - Pulsar `Map(K, V)` → Python `dict[K, V]`
   - Pulsar `Double()` → Python `float`
   - Pulsar `Bytes()` → Python `bytes`

### Migration Path

1. **Create dataclass versions** of all schemas in `trustgraph/schema/`
2. **Update backend classes** (Consumer, Producer, Publisher, Subscriber) to use backend-provided serialization
3. **Implement PulsarBackend** with JSON schema or dynamic Record generation
4. **Test with Pulsar** to ensure backward compatibility with existing deployments
5. **Add new backends** (MQTT, Kafka, Redis, etc.) as needed
6. **Remove Pulsar imports** from schema files

### Benefits

✅ **No pub/sub dependency** in schema definitions
✅ **Standard Python** - easy to understand, type-check, document
✅ **Modern tooling** - works with mypy, IDE autocomplete, linters
✅ **Backend-optimized** - each backend uses native serialization
✅ **No translation overhead** - direct serialization, no adapters
✅ **Type safety** - real objects with proper types
✅ **Easy validation** - can use Pydantic if needed

### Challenges & Solutions

**Challenge:** Pulsar's `Record` has runtime field validation
**Solution:** Use Pydantic dataclasses for validation if needed, or Python 3.10+ dataclass features with `__post_init__`

**Challenge:** Some Pulsar-specific features (like `Bytes` type)
**Solution:** Map to `bytes` type in dataclass, backend handles encoding appropriately

**Challenge:** Topic naming (`persistent://tenant/namespace/topic`)
**Solution:** Abstract topic names in schema definitions, backend converts to proper format

**Challenge:** Schema evolution and versioning
**Solution:** Each backend handles this according to its capabilities (Pulsar schema versions, Kafka schema registry, etc.)

**Challenge:** Nested complex types
**Solution:** Use nested dataclasses, backends recursively serialize/deserialize

### Design Decisions

1. **Plain dataclasses or Pydantic?**
   - ✅ **Decision: Use plain Python dataclasses**
   - Simpler, no additional dependencies
   - Validation not required in practice
   - Easier to understand and maintain

2. **Schema evolution:**
   - ✅ **Decision: No versioning mechanism needed**
   - Schemas are stable and long-lasting
   - Updates typically add new fields (backward compatible)
   - Backends handle schema evolution according to their capabilities

3. **Backward compatibility:**
   - ✅ **Decision: Major version change, no backward compatibility required**
   - Will be a breaking change with migration instructions
   - Clean break allows for better design
   - Migration guide will be provided for existing deployments

4. **Nested types and complex structures:**
   - ✅ **Decision: Use nested dataclasses naturally**
   - Python dataclasses handle nesting perfectly
   - `list[T]` for arrays, `dict[K, V]` for maps
   - Backends recursively serialize/deserialize
   - Example:
     ```python
     @dataclass
     class Value:
         value: str
         is_uri: bool

     @dataclass
     class Triple:
         s: Value              # Nested dataclass
         p: Value
         o: Value

     @dataclass
     class GraphQuery:
         triples: list[Triple]  # Array of nested dataclasses
         metadata: dict[str, str]
     ```

5. **Default values and optional fields:**
   - ✅ **Decision: Mix of required, defaults, and optional fields**
   - Required fields: No default value
   - Fields with defaults: Always present, have sensible default
   - Truly optional fields: `T | None = None`, omitted from serialization when `None`
   - Example:
     ```python
     @dataclass
     class TextCompletionRequest:
         system: str              # Required, no default
         prompt: str              # Required, no default
         streaming: bool = False  # Optional with default value
         metadata: dict | None = None  # Truly optional, can be absent
     ```

   **Important serialization semantics:**

   When `metadata = None`:
   ```json
   {
       "system": "...",
       "prompt": "...",
       "streaming": false
       // metadata field NOT PRESENT
   }
   ```

   When `metadata = {}` (explicitly empty):
   ```json
   {
       "system": "...",
       "prompt": "...",
       "streaming": false,
       "metadata": {}  // Field PRESENT but empty
   }
   ```

   **Key distinction:**
   - `None` → field absent from JSON (not serialized)
   - Empty value (`{}`, `[]`, `""`) → field present with empty value
   - This matters semantically: "not provided" vs "explicitly empty"
   - Serialization backends must skip `None` fields, not encode as `null`

## Approach Draft 3: Implementation Details

### Generic Queue Naming Format

Replace backend-specific queue names with a generic format that backends can map appropriately.

**Format:** `{qos}/{tenant}/{namespace}/{queue-name}`

Where:
- `qos`: Quality of Service level
  - `q0` = best-effort (fire and forget, no acknowledgment)
  - `q1` = at-least-once (requires acknowledgment)
  - `q2` = exactly-once (two-phase acknowledgment)
- `tenant`: Logical grouping for multi-tenancy
- `namespace`: Sub-grouping within tenant
- `queue-name`: Actual queue/topic name

**Examples:**
```
q1/tg/flow/text-completion-requests
q2/tg/config/config-push
q0/tg/metrics/stats
```

### Backend Topic Mapping

Each backend maps the generic format to its native format:

**Pulsar Backend:**
```python
def map_topic(self, generic_topic: str) -> str:
    # Parse: q1/tg/flow/text-completion-requests
    qos, tenant, namespace, queue = generic_topic.split('/', 3)

    # Map QoS to persistence
    persistence = 'persistent' if qos in ['q1', 'q2'] else 'non-persistent'

    # Return Pulsar URI: persistent://tg/flow/text-completion-requests
    return f"{persistence}://{tenant}/{namespace}/{queue}"
```

**MQTT Backend:**
```python
def map_topic(self, generic_topic: str) -> tuple[str, int]:
    # Parse: q1/tg/flow/text-completion-requests
    qos, tenant, namespace, queue = generic_topic.split('/', 3)

    # Map QoS level
    qos_level = {'q0': 0, 'q1': 1, 'q2': 2}[qos]

    # Build MQTT topic including tenant/namespace for proper namespacing
    mqtt_topic = f"{tenant}/{namespace}/{queue}"

    return mqtt_topic, qos_level
```

### Updated Topic Helper Function

```python
# schema/core/topic.py
def topic(queue_name, qos='q1', tenant='tg', namespace='flow'):
    """
    Create a generic topic identifier that can be mapped by backends.

    Args:
        queue_name: The queue/topic name
        qos: Quality of service
             - 'q0' = best-effort (no ack)
             - 'q1' = at-least-once (ack required)
             - 'q2' = exactly-once (two-phase ack)
        tenant: Tenant identifier for multi-tenancy
        namespace: Namespace within tenant

    Returns:
        Generic topic string: qos/tenant/namespace/queue_name

    Examples:
        topic('my-queue')  # q1/tg/flow/my-queue
        topic('config', qos='q2', namespace='config')  # q2/tg/config/config
    """
    return f"{qos}/{tenant}/{namespace}/{queue_name}"
```

### Configuration and Initialization

**Command-Line Arguments + Environment Variables:**

```python
# In base/async_processor.py - add_args() method
@staticmethod
def add_args(parser):
    # Pub/sub backend selection
    parser.add_argument(
        '--pubsub-backend',
        default=os.getenv('PUBSUB_BACKEND', 'pulsar'),
        choices=['pulsar', 'mqtt'],
        help='Pub/sub backend (default: pulsar, env: PUBSUB_BACKEND)'
    )

    # Pulsar-specific configuration
    parser.add_argument(
        '--pulsar-host',
        default=os.getenv('PULSAR_HOST', 'pulsar://localhost:6650'),
        help='Pulsar host (default: pulsar://localhost:6650, env: PULSAR_HOST)'
    )

    parser.add_argument(
        '--pulsar-api-key',
        default=os.getenv('PULSAR_API_KEY', None),
        help='Pulsar API key (env: PULSAR_API_KEY)'
    )

    parser.add_argument(
        '--pulsar-listener',
        default=os.getenv('PULSAR_LISTENER', None),
        help='Pulsar listener name (env: PULSAR_LISTENER)'
    )

    # MQTT-specific configuration
    parser.add_argument(
        '--mqtt-host',
        default=os.getenv('MQTT_HOST', 'localhost'),
        help='MQTT broker host (default: localhost, env: MQTT_HOST)'
    )

    parser.add_argument(
        '--mqtt-port',
        type=int,
        default=int(os.getenv('MQTT_PORT', '1883')),
        help='MQTT broker port (default: 1883, env: MQTT_PORT)'
    )

    parser.add_argument(
        '--mqtt-username',
        default=os.getenv('MQTT_USERNAME', None),
        help='MQTT username (env: MQTT_USERNAME)'
    )

    parser.add_argument(
        '--mqtt-password',
        default=os.getenv('MQTT_PASSWORD', None),
        help='MQTT password (env: MQTT_PASSWORD)'
    )
```

**Factory Function:**

```python
# In base/pubsub.py or base/pubsub_factory.py
def get_pubsub(**config) -> PubSubBackend:
    """
    Create and return a pub/sub backend based on configuration.

    Args:
        config: Configuration dict from command-line args
                Must include 'pubsub_backend' key

    Returns:
        Backend instance (PulsarBackend, MQTTBackend, etc.)
    """
    backend_type = config.get('pubsub_backend', 'pulsar')

    if backend_type == 'pulsar':
        return PulsarBackend(
            host=config.get('pulsar_host'),
            api_key=config.get('pulsar_api_key'),
            listener=config.get('pulsar_listener'),
        )
    elif backend_type == 'mqtt':
        return MQTTBackend(
            host=config.get('mqtt_host'),
            port=config.get('mqtt_port'),
            username=config.get('mqtt_username'),
            password=config.get('mqtt_password'),
        )
    else:
        raise ValueError(f"Unknown pub/sub backend: {backend_type}")
```

**Usage in AsyncProcessor:**

```python
# In async_processor.py
class AsyncProcessor:
    def __init__(self, **params):
        self.id = params.get("id")

        # Create backend from config (replaces PulsarClient)
        self.pubsub = get_pubsub(**params)

        # Rest of initialization...
```

### Backend Interface

```python
class PubSubBackend(Protocol):
    """Protocol defining the interface all pub/sub backends must implement."""

    def create_producer(self, topic: str, schema: type, **options) -> BackendProducer:
        """
        Create a producer for a topic.

        Args:
            topic: Generic topic format (qos/tenant/namespace/queue)
            schema: Dataclass type for messages
            options: Backend-specific options (e.g., chunking_enabled)

        Returns:
            Backend-specific producer instance
        """
        ...

    def create_consumer(
        self,
        topic: str,
        subscription: str,
        schema: type,
        initial_position: str = 'latest',
        consumer_type: str = 'shared',
        **options
    ) -> BackendConsumer:
        """
        Create a consumer for a topic.

        Args:
            topic: Generic topic format (qos/tenant/namespace/queue)
            subscription: Subscription/consumer group name
            schema: Dataclass type for messages
            initial_position: 'earliest' or 'latest' (MQTT may ignore)
            consumer_type: 'shared', 'exclusive', 'failover' (MQTT may ignore)
            options: Backend-specific options

        Returns:
            Backend-specific consumer instance
        """
        ...

    def close(self) -> None:
        """Close the backend connection."""
        ...
```

```python
class BackendProducer(Protocol):
    """Protocol for backend-specific producer."""

    def send(self, message: Any, properties: dict = {}) -> None:
        """Send a message (dataclass instance) with optional properties."""
        ...

    def flush(self) -> None:
        """Flush any buffered messages."""
        ...

    def close(self) -> None:
        """Close the producer."""
        ...
```

```python
class BackendConsumer(Protocol):
    """Protocol for backend-specific consumer."""

    def receive(self, timeout_millis: int = 2000) -> Message:
        """
        Receive a message from the topic.

        Raises:
            TimeoutError: If no message received within timeout
        """
        ...

    def acknowledge(self, message: Message) -> None:
        """Acknowledge successful processing of a message."""
        ...

    def negative_acknowledge(self, message: Message) -> None:
        """Negative acknowledge - triggers redelivery."""
        ...

    def unsubscribe(self) -> None:
        """Unsubscribe from the topic."""
        ...

    def close(self) -> None:
        """Close the consumer."""
        ...
```

```python
class Message(Protocol):
    """Protocol for a received message."""

    def value(self) -> Any:
        """Get the deserialized message (dataclass instance)."""
        ...

    def properties(self) -> dict:
        """Get message properties/metadata."""
        ...
```

### Existing Classes Refactoring

The existing `Consumer`, `Producer`, `Publisher`, `Subscriber` classes remain largely intact:

**Current responsibilities (keep):**
- Async threading model and taskgroups
- Reconnection logic and retry handling
- Metrics collection
- Rate limiting
- Concurrency management

**Changes needed:**
- Remove direct Pulsar imports (`pulsar.schema`, `pulsar.InitialPosition`, etc.)
- Accept `BackendProducer`/`BackendConsumer` instead of Pulsar client
- Delegate actual pub/sub operations to backend instances
- Map generic concepts to backend calls

**Example refactoring:**

```python
# OLD - consumer.py
class Consumer:
    def __init__(self, client, topic, subscriber, schema, ...):
        self.client = client  # Direct Pulsar client
        # ...

    async def consumer_run(self):
        # Uses pulsar.InitialPosition, pulsar.ConsumerType
        self.consumer = self.client.subscribe(
            topic=self.topic,
            schema=JsonSchema(self.schema),
            initial_position=pulsar.InitialPosition.Earliest,
            consumer_type=pulsar.ConsumerType.Shared,
        )

# NEW - consumer.py
class Consumer:
    def __init__(self, backend_consumer, schema, ...):
        self.backend_consumer = backend_consumer  # Backend-specific consumer
        self.schema = schema
        # ...

    async def consumer_run(self):
        # Backend consumer already created with right settings
        # Just use it directly
        while self.running:
            msg = await asyncio.to_thread(
                self.backend_consumer.receive,
                timeout_millis=2000
            )
            await self.handle_message(msg)
```

### Backend-Specific Behaviors

**Pulsar Backend:**
- Maps `q0` → `non-persistent://`, `q1`/`q2` → `persistent://`
- Supports all consumer types (shared, exclusive, failover)
- Supports initial position (earliest/latest)
- Native message acknowledgment
- Schema registry support

**MQTT Backend:**
- Maps `q0`/`q1`/`q2` → MQTT QoS levels 0/1/2
- Includes tenant/namespace in topic path for namespacing
- Auto-generates client IDs from subscription names
- Ignores initial position (no message history in basic MQTT)
- Ignores consumer type (MQTT uses client IDs, not consumer groups)
- Simple publish/subscribe model

### Design Decisions Summary

1. ✅ **Generic queue naming**: `qos/tenant/namespace/queue-name` format
2. ✅ **QoS in queue ID**: Determined by queue definition, not configuration
3. ✅ **Reconnection**: Handled by Consumer/Producer classes, not backends
4. ✅ **MQTT topics**: Include tenant/namespace for proper namespacing
5. ✅ **Message history**: MQTT ignores `initial_position` parameter (future enhancement)
6. ✅ **Client IDs**: MQTT backend auto-generates from subscription name

### Future Enhancements

**MQTT message history:**
- Could add optional persistence layer (e.g., retained messages, external store)
- Would allow supporting `initial_position='earliest'`
- Not required for initial implementation

