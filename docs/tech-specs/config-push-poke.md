# Config Push "Notify" Pattern Technical Specification

## Overview

Replace the current config push mechanism — which broadcasts the full config
blob on a `state` class queue — with a lightweight "notify" notification
containing only the version number and affected types. Processors that care
about those types fetch the full config via the existing request/response
interface.

This solves the RabbitMQ late-subscriber problem: when a process restarts,
its fresh queue has no historical messages, so it never receives the current
config state. With the notify pattern, the push queue is only a signal — the
source of truth is the config service's request/response API, which is
always available.

## Problem

On Pulsar, `state` class queues are persistent topics. A new subscriber
with `InitialPosition.Earliest` reads from message 0 and receives the
last config push. On RabbitMQ, each subscriber gets a fresh per-subscriber
queue (named with a new UUID). Messages published before the queue existed
are gone. A restarting processor never gets the current config.

## Design

### The Notify Message

The `ConfigPush` schema changes from carrying the full config to carrying
just a version number and the list of affected config types:

```python
@dataclass
class ConfigPush:
    version: int = 0
    types: list[str] = field(default_factory=list)
```

When the config service handles a `put` or `delete`, it knows which types
were affected (from the request's `values[].type` or `keys[].type`). It
includes those in the notify. On startup, the config service sends a notify
with an empty types list (meaning "everything").

### Subscribe-then-Fetch Startup (No Race Condition)

The critical ordering to avoid missing an update:

1. **Subscribe** to the config push queue. Buffer incoming notify messages.
2. **Fetch** the full config via request/response (`operation: "config"`).
   This returns the config dict and a version number.
3. **Apply** the fetched config to all registered handlers.
4. **Process** buffered notifys. For any notify with `version > fetched_version`,
   re-fetch and re-apply. Discard notifys with `version <= fetched_version`.
5. **Enter steady state**. Process future notifys as they arrive.

This is safe because:
- If an update happens before the subscription, the fetch picks it up.
- If an update happens between subscribe and fetch, it's in the buffer.
- If an update happens after the fetch, it arrives on the queue normally.
- Version comparison ensures no duplicate processing.

### Processor API

The current API requires processors to understand the full config dict
structure. The new API should be cleaner — processors declare which config
types they care about and provide a handler that receives only the relevant
config subset.

#### Current API

```python
# In processor __init__:
self.register_config_handler(self.on_configure_flows)

# Handler receives the entire config dict:
async def on_configure_flows(self, config, version):
    if "active-flow" not in config:
        return
    if self.id in config["active-flow"]:
        flow_config = json.loads(config["active-flow"][self.id])
    # ...
```

#### New API

```python
# In processor __init__:
self.register_config_handler(
    handler=self.on_configure_flows,
    types=["active-flow"],
)

# Handler receives only the relevant config subset, same signature:
async def on_configure_flows(self, config, version):
    # config still contains the full dict, but handler is only called
    # when "active-flow" type changes (or on startup)
    if "active-flow" not in config:
        return
    # ...
```

The `types` parameter is optional. If omitted, the handler is called for
every config change (backward compatible). If specified, the handler is
only invoked when the notify's `types` list intersects with the handler's
types, or on startup (empty types list = everything).

#### Internal Registration Structure

```python
# In AsyncProcessor:
def register_config_handler(self, handler, types=None):
    self.config_handlers.append({
        "handler": handler,
        "types": set(types) if types else None,  # None = all types
    })
```

#### Notify Processing Logic

```python
async def on_config_notify(self, message, consumer, flow):
    notify_version = message.value().version
    notify_types = set(message.value().types)

    # Skip if we already have this version or newer
    if notify_version <= self.config_version:
        return

    # Fetch full config from config service
    config, version = await self.config_client.config()
    self.config_version = version

    # Determine which handlers to invoke
    for entry in self.config_handlers:
        handler_types = entry["types"]
        if handler_types is None:
            # Handler cares about everything
            await entry["handler"](config, version)
        elif not notify_types or notify_types & handler_types:
            # notify_types empty = startup (invoke all),
            # or intersection with handler's types
            await entry["handler"](config, version)
```

### Config Service Changes

#### Push Method

The `push()` method changes to send only version + types:

```python
async def push(self, types=None):
    version = await self.config.get_version()
    resp = ConfigPush(
        version=version,
        types=types or [],
    )
    await self.config_push_producer.send(resp)
```

#### Put/Delete Handlers

Extract affected types and pass to push:

```python
async def handle_put(self, v):
    types = list(set(k.type for k in v.values))
    for k in v.values:
        await self.table_store.put_config(k.type, k.key, k.value)
    await self.inc_version()
    await self.push(types=types)

async def handle_delete(self, v):
    types = list(set(k.type for k in v.keys))
    for k in v.keys:
        await self.table_store.delete_key(k.type, k.key)
    await self.inc_version()
    await self.push(types=types)
```

#### Queue Class Change

The config push queue changes from `state` class to `flow` class. The push
is now a transient signal — the source of truth is the config service's
request/response API, not the queue. `flow` class is persistent (survives
broker restarts) but doesn't require last-message retention, which was the
root cause of the RabbitMQ problem.

```python
config_push_queue = queue('config', cls='flow')  # was cls='state'
```

#### Startup Push

On startup, the config service sends a notify with empty types list
(signalling "everything changed"):

```python
async def start(self):
    await self.push(types=[])  # Empty = all types
    await self.config_request_consumer.start()
```

### AsyncProcessor Changes

The `AsyncProcessor` needs a config request/response client alongside the
push consumer. The startup sequence becomes:

```python
async def start(self):
    # 1. Start the push consumer (begins buffering notifys)
    await self.config_sub_task.start()

    # 2. Fetch current config via request/response
    config, version = await self.config_client.config()
    self.config_version = version

    # 3. Apply to all handlers (startup = all handlers invoked)
    for entry in self.config_handlers:
        await entry["handler"](config, version)

    # 4. Buffered notifys are now processed by on_config_notify,
    #    which skips versions <= self.config_version
```

The config client needs to be created in `__init__` using the existing
request/response queue infrastructure. The `ConfigClient` from
`trustgraph.clients.config_client` already exists but uses a synchronous
blocking pattern. An async variant or integration with the processor's
pub/sub backend is needed.

### Existing Config Handler Types

For reference, the config types currently used by handlers:

| Handler | Type(s) | Used By |
|---------|---------|---------|
| `on_configure_flows` | `active-flow` | All FlowProcessor subclasses |
| `on_collection_config` | `collection` | Storage services (triples, embeddings, rows) |
| `on_prompt_config` | `prompt` | Prompt template service, agent extract |
| `on_schema_config` | `schema` | Rows storage, row embeddings, NLP query, structured diag |
| `on_cost_config` | `token-costs` | Metering service |
| `on_ontology_config` | `ontology` | Ontology extraction |
| `on_librarian_config` | `librarian` | Librarian service |
| `on_mcp_config` | `mcp-tool` | MCP tool service |
| `on_knowledge_config` | `kg-core` | Cores service |

## Implementation Order

1. **Update ConfigPush schema** — change `config` field to `types` field.

2. **Update config service** — modify `push()` to send version + types.
   Modify `handle_put`/`handle_delete` to extract affected types.

3. **Add async config query to AsyncProcessor** — create a
   request/response client for config queries within the processor's
   event loop.

4. **Implement subscribe-then-fetch startup** — reorder
   `AsyncProcessor.start()` to subscribe first, then fetch, then
   process buffered notifys with version comparison.

5. **Update register_config_handler** — add optional `types` parameter.
   Update `on_config_notify` to filter by type intersection.

6. **Update existing handlers** — add `types` parameter to all
   `register_config_handler` calls across the codebase.

7. **Backward compatibility** — handlers without `types` parameter
   continue to work (invoked for all changes).

## Risks

- **Thundering herd**: if many processors restart simultaneously, they
  all hit the config service API at once. Mitigated by the config service
  already being designed for request/response load, and the number of
  processors being small (tens, not thousands).

- **Config service availability**: processors now depend on the config
  service being up at startup, not just having received a push. This is
  already the case in practice — without config, processors can't do
  anything useful.
