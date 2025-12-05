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

### Issue #4: Collection Management Architecture
- **Current:** Collections stored in Cassandra librarian keyspace via separate collections table
- **Current:** Librarian uses 4 hardcoded storage management topics to coordinate collection create/delete:
  - `vector_storage_management_topic`
  - `object_storage_management_topic`
  - `triples_storage_management_topic`
  - `storage_management_response_topic`
- **Problems:**
  - Hardcoded topics cannot be customized for multi-tenant deployments
  - Complex async coordination between librarian and 4+ storage services
  - Separate Cassandra table and management infrastructure
  - Non-persistent request/response queues for critical operations
- **Solution:** Migrate collections to config service storage, use config push for distribution

## Solution

This spec addresses Issues #1, #2, #3, and #4.

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

### Part 3: Migrate Collection Management to Config Service

#### Overview
Migrate collections from Cassandra librarian keyspace to config service storage. This eliminates hardcoded storage management topics and simplifies the architecture by using the existing config push mechanism for distribution.

#### Current Architecture
```
API Request → Gateway → Librarian Service
                            ↓
                    CollectionManager
                            ↓
                    Cassandra Collections Table (librarian keyspace)
                            ↓
                    Broadcast to 4 Storage Management Topics (hardcoded)
                            ↓
        Wait for 4+ Storage Service Responses
                            ↓
                    Response to Gateway
```

#### New Architecture
```
API Request → Gateway → Librarian Service
                            ↓
                    CollectionManager
                            ↓
                    Config Service API (put/delete/getvalues)
                            ↓
                    Cassandra Config Table (class='collections', key='user:collection')
                            ↓
                    Config Push (to all subscribers on config-push-queue)
                            ↓
        All Storage Services receive config update independently
```

#### Change 7: Collection Manager - Use Config Service API
**File:** `trustgraph-flow/trustgraph/librarian/collection_manager.py`

**Remove:**
- `LibraryTableStore` usage (Lines 33, 40-41)
- Storage management producers initialization (Lines 86-140)
- `on_storage_response` method (Lines 400-430)
- `pending_deletions` tracking (Lines 57, 90-96, and usage throughout)

**Add:**
- Config service client for API calls

**Modify `list_collections` (Lines 145-180):**
- Replace Cassandra query with config service `getvalues` call
- Request: `ConfigRequest(operation='getvalues', type='collections', user=<user>)`
- Parse returned JSON-serialized CollectionMetadata values
- Apply tag filtering in-memory (as before)

**Modify `update_collection` (Lines 182-312):**
- Replace Cassandra write with config service `put` call
- Request: `ConfigRequest(operation='put', type='collections', key='user:collection', value=<JSON metadata>)`
- Remove all storage broadcast logic (Lines 211-270)
- Remove response waiting logic (Lines 272-310)
- Simplified: config service call triggers automatic config push

**Modify `delete_collection` (Lines 314-398):**
- Replace Cassandra delete with config service `delete` call
- Request: `ConfigRequest(operation='delete', type='collections', key='user:collection')`
- Remove all storage broadcast logic (Lines 325-390)
- Remove pending_deletions tracking (Lines 343-360)
- Simplified: config service call triggers automatic config push

**Collection Metadata Format:**
- Stored in config table as: `class='collections', key='user:collection'`
- Value is JSON-serialized CollectionMetadata (without timestamp fields)
- Fields: `user`, `collection`, `name`, `description`, `tags`
- Example: `class='collections', key='alice:my-docs', value='{"user":"alice","collection":"my-docs","name":"My Documents","description":"...","tags":["work"]}'`

#### Change 8: Librarian Service - Remove Storage Management Infrastructure
**File:** `trustgraph-flow/trustgraph/librarian/service.py`

**Remove:**
- Storage management producers (Lines 173-190):
  - `vector_storage_management_producer`
  - `object_storage_management_producer`
  - `triples_storage_management_producer`
- Storage response consumer (Lines 192-201)
- `on_storage_response` handler (Lines 467-473)

**Modify:**
- CollectionManager initialization (Lines 215-224) - remove storage producer parameters

**Note:** External collection API remains unchanged:
- `list-collections`
- `update-collection`
- `delete-collection`

#### Change 9: Remove Collections Table from LibraryTableStore
**File:** `trustgraph-flow/trustgraph/tables/library.py`

**Delete:**
- Collections table CREATE statement (Lines 114-127)
- Collections prepared statements (Lines 205-240)
- All collection methods (Lines 578-717):
  - `ensure_collection_exists`
  - `list_collections`
  - `update_collection`
  - `delete_collection`
  - `get_collection`
  - `create_collection`

**Rationale:**
- Collections now stored in config table
- Breaking change acceptable - no data migration needed
- Simplifies librarian service significantly

#### Change 10: Storage Services - Config-Based Collection Management
**Status:** Implementation deferred for follow-up discussion

**Pattern Overview:**
Each storage service will:
1. Subscribe to config push queue (like librarian already does)
2. Register config handler to receive updates
3. Parse collections from `config['collections']`
4. Create/delete collections based on config changes
5. Remove storage management request/response consumers/producers

**Affected Services (11 total):**
- Document embeddings: milvus, pinecone, qdrant
- Graph embeddings: milvus, pinecone, qdrant
- Object storage: cassandra
- Triples storage: cassandra, falkordb, memgraph, neo4j

#### Change 11: Update Collection Schema - Remove Timestamps
**File:** `trustgraph-base/trustgraph/schema/services/collection.py`

**Modify CollectionMetadata (Lines 13-21):**
Remove `created_at` and `updated_at` fields:
```python
class CollectionMetadata(Record):
    user = String()
    collection = String()
    name = String()
    description = String()
    tags = Array(String())
    # Remove: created_at = String()
    # Remove: updated_at = String()
```

**Modify CollectionManagementRequest (Lines 25-47):**
Remove timestamp fields:
```python
class CollectionManagementRequest(Record):
    operation = String()
    user = String()
    collection = String()
    timestamp = String()
    name = String()
    description = String()
    tags = Array(String())
    # Remove: created_at = String()
    # Remove: updated_at = String()
    tag_filter = Array(String())
    limit = Integer()
```

**Rationale:**
- Timestamps don't add value for collections
- Config service maintains its own version tracking
- Simplifies schema and reduces storage

#### Benefits of Config Service Migration

1. ✅ **Eliminates hardcoded storage management topics** - Solves multi-tenant blocker
2. ✅ **Simpler coordination** - No complex async waiting for 4+ storage responses
3. ✅ **Eventual consistency** - Storage services update independently via config push
4. ✅ **Better reliability** - Persistent config push vs non-persistent request/response
5. ✅ **Unified configuration model** - Collections treated as configuration
6. ✅ **Reduces complexity** - Removes ~300 lines of coordination code
7. ✅ **Multi-tenant ready** - Config already supports tenant isolation via keyspace
8. ✅ **Version tracking** - Config service version mechanism provides audit trail

## Implementation Notes

### Backward Compatibility

**Parameter Changes:**
- CLI parameter renames are breaking changes but acceptable (feature currently non-functional)
- Services work without parameters (use defaults)
- Default keyspaces preserved: "config", "knowledge", "librarian"
- Default queue: `persistent://tg/config/config`

**Collection Management:**
- **Breaking change:** Collections table removed from librarian keyspace
- **No data migration provided** - acceptable for this phase
- External collection API unchanged (list/update/delete operations)
- Collection metadata format simplified (timestamps removed)

### Testing Requirements

**Parameter Testing:**
1. Verify `--config-push-queue` parameter works on graph-embeddings service
2. Verify `--config-push-queue` parameter works on text-completion service
3. Verify `--config-push-queue` parameter works on config service
4. Verify `--cassandra-keyspace` parameter works for config service
5. Verify `--cassandra-keyspace` parameter works for cores service
6. Verify `--cassandra-keyspace` parameter works for librarian service
7. Verify services work without parameters (uses defaults)
8. Verify multi-tenant deployment with custom queue names and keyspace

**Collection Management Testing:**
9. Verify `list-collections` operation via config service
10. Verify `update-collection` creates/updates in config table
11. Verify `delete-collection` removes from config table
12. Verify config push is triggered on collection updates
13. Verify tag filtering works with config-based storage
14. Verify collection operations work without timestamp fields

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

### Services Affected by Change 1-2 (CLI Parameter Rename)
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

### Services Affected by Changes 7-11 (Collection Management)

**Immediate Changes:**
- librarian-service (collection_manager.py, service.py)
- tables/library.py (collections table removal)
- schema/services/collection.py (timestamp removal)

**Deferred Changes (Change 10):**
- All storage services (11 total) - will subscribe to config push for collection updates
- Storage management schema (potentially removable if unused elsewhere)

## Implementation Phases

### Phase 1: Parameter Fixes (Changes 1-6)
- Fix `--config-push-queue` parameter naming
- Add `--cassandra-keyspace` parameter support
- **Outcome:** Multi-tenant queue and keyspace configuration enabled

### Phase 2: Collection Management Migration (Changes 7-9, 11)
- Migrate collection storage to config service
- Remove collections table from librarian
- Update collection schema (remove timestamps)
- **Outcome:** Eliminates hardcoded storage management topics, simplifies librarian

### Phase 3: Storage Service Updates (Change 10) - Deferred
- Update all storage services to use config push for collections
- Remove storage management request/response infrastructure
- **Outcome:** Complete config-based collection management

## References
- GitHub Issue: https://github.com/trustgraph-ai/trustgraph/issues/582
- Related Files:
  - `trustgraph-base/trustgraph/base/async_processor.py`
  - `trustgraph-base/trustgraph/base/cassandra_config.py`
  - `trustgraph-base/trustgraph/schema/core/topic.py`
  - `trustgraph-base/trustgraph/schema/services/collection.py`
  - `trustgraph-flow/trustgraph/config/service/service.py`
  - `trustgraph-flow/trustgraph/cores/service.py`
  - `trustgraph-flow/trustgraph/librarian/service.py`
  - `trustgraph-flow/trustgraph/librarian/collection_manager.py`
  - `trustgraph-flow/trustgraph/tables/library.py`
