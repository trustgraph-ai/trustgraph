# Technical Specification: Multi-Tenant Support

## Overview

Enable multi-tenant deployments by fixing parameter name mismatches that prevent queue customization and adding Cassandra keyspace parameterization.

## Architecture Context

### Flow-Based Queue Resolution

The TrustGraph system uses a **flow-based architecture** for dynamic queue resolution, which inherently supports multi-tenancy:

- **Flow Definitions** are stored in Cassandra and specify queue names via interface definitions
- **Queue names use templates** with `{id}` variables that are replaced with flow instance IDs
- **Services dynamically resolve queues** by looking up flow configurations at request time
- **Each tenant can have unique flows** with different queue names, providing isolation

Example flow interface definition:
```json
{
  "interfaces": {
    "triples-store": "persistent://tg/flow/triples-store:{id}",
    "graph-embeddings-store": "persistent://tg/flow/graph-embeddings-store:{id}"
  }
}
```

When tenant A starts flow `tenant-a-prod` and tenant B starts flow `tenant-b-prod`, they automatically get isolated queues:
- `persistent://tg/flow/triples-store:tenant-a-prod`
- `persistent://tg/flow/triples-store:tenant-b-prod`

**Services correctly designed for multi-tenancy:**
- ✅ **Knowledge Management (cores)** - Dynamically resolves queues from flow configuration passed in requests

**Services needing fixes:**
- 🔴 **Config Service** - Parameter name mismatch prevents queue customization
- 🔴 **Librarian Service** - Hardcoded storage management topics (discussed below)
- 🔴 **All Services** - Cannot customize Cassandra keyspace

## Problem Statement

### Issue #1: Parameter Name Mismatch in AsyncProcessor
- **CLI defines:** `--config-queue` (unclear naming)
- **Argparse converts to:** `config_queue` (in params dict)
- **Code looks for:** `config_push_queue`
- **Result:** Parameter is ignored, defaults to `persistent://tg/config/config`
- **Impact:** Affects all 32+ services inheriting from AsyncProcessor
- **Blocks:** Multi-tenant deployments cannot use tenant-specific config queues
- **Solution:** Rename CLI parameter to `--config-push-queue` for clarity (breaking change acceptable since feature is currently broken)

### Issue #2: Parameter Name Mismatch in Config Service
- **CLI defines:** `--push-queue` (ambiguous naming)
- **Argparse converts to:** `push_queue` (in params dict)
- **Code looks for:** `config_push_queue`
- **Result:** Parameter is ignored
- **Impact:** Config service cannot use custom push queue
- **Solution:** Rename CLI parameter to `--config-push-queue` for consistency and clarity (breaking change acceptable)

### Issue #3: Hardcoded Cassandra Keyspace
- **Current:** Keyspace hardcoded as `"config"`, `"knowledge"`, `"librarian"` in various services
- **Result:** Cannot customize keyspace for multi-tenant deployments
- **Impact:** Config, cores, and librarian services
- **Blocks:** Multiple tenants cannot use separate Cassandra keyspaces

### Issue #4: Hardcoded Storage Management Topics in Librarian
- **Current:** Librarian service uses 4 hardcoded storage management topics:
  - `vector_storage_management_topic`
  - `object_storage_management_topic`
  - `triples_storage_management_topic`
  - `storage_management_response_topic`
- **Location:** Imported from schema definitions, not exposed as CLI parameters
- **Result:** Cannot customize these topics for multi-tenant deployments
- **Impact:** Librarian service cannot route storage management requests to tenant-specific queues
- **Status:** Requires design discussion - these topics need careful consideration for multi-tenant architecture

## Solution

**Note:** Issue #4 (Librarian storage management topics) is **deferred** pending design discussion. This spec addresses Issues #1, #2, and #3.

### Part 1: Fix Parameter Name Mismatches

#### Change 1: AsyncProcessor Base Class - Rename CLI Parameter
**File:** `trustgraph-base/trustgraph/base/async_processor.py`
**Line:** 260-264

**Current:**
```python
parser.add_argument(
    '--config-queue',
    default=default_config_queue,
    help=f'Config push queue {default_config_queue}',
)
```

**Fixed:**
```python
parser.add_argument(
    '--config-push-queue',
    default=default_config_queue,
    help=f'Config push queue (default: {default_config_queue})',
)
```

**Rationale:**
- Clearer, more explicit naming
- Matches the internal variable name `config_push_queue`
- Breaking change acceptable since feature is currently non-functional
- No code change needed in params.get() - it already looks for the correct name

#### Change 2: Config Service - Rename CLI Parameter
**File:** `trustgraph-flow/trustgraph/config/service/service.py`
**Line:** 276-279

**Current:**
```python
parser.add_argument(
    '--push-queue',
    default=default_config_push_queue,
    help=f'Config push queue (default: {default_config_push_queue})'
)
```

**Fixed:**
```python
parser.add_argument(
    '--config-push-queue',
    default=default_config_push_queue,
    help=f'Config push queue (default: {default_config_push_queue})'
)
```

**Rationale:**
- Clearer naming - "config-push-queue" is more explicit than just "push-queue"
- Matches the internal variable name `config_push_queue`
- Consistent with AsyncProcessor's `--config-push-queue` parameter
- Breaking change acceptable since feature is currently non-functional
- No code change needed in params.get() - it already looks for the correct name

### Part 2: Add Cassandra Keyspace Parameterization

#### Change 3: Add Keyspace Parameter to cassandra_config Module
**File:** `trustgraph-base/trustgraph/base/cassandra_config.py`

**Add CLI argument** (in `add_cassandra_args()` function):
```python
parser.add_argument(
    '--cassandra-keyspace',
    default=None,
    help='Cassandra keyspace (default: service-specific)'
)
```

**Add environment variable support** (in `resolve_cassandra_config()` function):
```python
keyspace = params.get(
    "cassandra_keyspace",
    os.environ.get("CASSANDRA_KEYSPACE")
)
```

**Update return value** of `resolve_cassandra_config()`:
- Currently returns: `(hosts, username, password)`
- Change to return: `(hosts, username, password, keyspace)`

**Rationale:**
- Consistent with existing Cassandra configuration pattern
- Available to all services via `add_cassandra_args()`
- Supports both CLI and environment variable configuration

#### Change 4: Config Service - Use Parameterized Keyspace
**File:** `trustgraph-flow/trustgraph/config/service/service.py`

**Line 30** - Remove hardcoded keyspace:
```python
# DELETE THIS LINE:
keyspace = "config"
```

**Lines 69-73** - Update cassandra config resolution:

**Current:**
```python
cassandra_host, cassandra_username, cassandra_password = \
    resolve_cassandra_config(params)
```

**Fixed:**
```python
cassandra_host, cassandra_username, cassandra_password, keyspace = \
    resolve_cassandra_config(params, default_keyspace="config")
```

**Rationale:**
- Maintains backward compatibility with "config" as default
- Allows override via `--cassandra-keyspace` or `CASSANDRA_KEYSPACE`

#### Change 5: Cores/Knowledge Service - Use Parameterized Keyspace
**File:** `trustgraph-flow/trustgraph/cores/service.py`

**Line 37** - Remove hardcoded keyspace:
```python
# DELETE THIS LINE:
keyspace = "knowledge"
```

**Update cassandra config resolution** (similar location as config service):
```python
cassandra_host, cassandra_username, cassandra_password, keyspace = \
    resolve_cassandra_config(params, default_keyspace="knowledge")
```

#### Change 6: Librarian Service - Use Parameterized Keyspace
**File:** `trustgraph-flow/trustgraph/librarian/service.py`

**Line 51** - Remove hardcoded keyspace:
```python
# DELETE THIS LINE:
keyspace = "librarian"
```

**Update cassandra config resolution** (similar location as config service):
```python
cassandra_host, cassandra_username, cassandra_password, keyspace = \
    resolve_cassandra_config(params, default_keyspace="librarian")
```

## Implementation Notes

### Backward Compatibility
- All changes maintain backward compatibility
- Services work without parameters (use defaults)
- Default keyspaces preserved: "config", "knowledge", "librarian"
- Default queue: `persistent://tg/config/config`

### Testing Requirements
1. Verify `--config-push-queue` parameter works on graph-embeddings service
2. Verify `--config-push-queue` parameter works on text-completion service
3. Verify `--config-push-queue` parameter works on config service
4. Verify `--cassandra-keyspace` parameter works for config service
5. Verify `--cassandra-keyspace` parameter works for cores service
6. Verify `--cassandra-keyspace` parameter works for librarian service
7. Verify services work without parameters (uses defaults)
8. Verify multi-tenant deployment with custom queue names and keyspace

### Multi-Tenant Deployment Example
```bash
# Tenant: tg-dev
graph-embeddings \
  -p pulsar+ssl://broker:6651 \
  --pulsar-api-key <KEY> \
  --config-push-queue persistent://tg-dev/config/config

config-service \
  -p pulsar+ssl://broker:6651 \
  --pulsar-api-key <KEY> \
  --config-push-queue persistent://tg-dev/config/config \
  --cassandra-keyspace tg_dev_config
```

## Impact Analysis

### Services Affected by Change 1 (AsyncProcessor)
All services inheriting from AsyncProcessor or FlowProcessor:
- config-service
- cores-service
- librarian-service
- graph-embeddings
- document-embeddings
- text-completion-* (all providers)
- extract-* (all extractors)
- query-* (all query services)
- retrieval-* (all RAG services)
- storage-* (all storage services)
- And 20+ more services

### Services Affected by Changes 3-6 (Cassandra Keyspace)
- config-service
- cores-service
- librarian-service

## References
- GitHub Issue: https://github.com/trustgraph-ai/trustgraph/issues/582
- Related Files:
  - `trustgraph-base/trustgraph/base/async_processor.py`
  - `trustgraph-base/trustgraph/base/cassandra_config.py`
  - `trustgraph-base/trustgraph/schema/core/topic.py`
  - `trustgraph-flow/trustgraph/config/service/service.py`
  - `trustgraph-flow/trustgraph/cores/service.py`
  - `trustgraph-flow/trustgraph/librarian/service.py`
