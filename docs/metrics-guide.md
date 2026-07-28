# TrustGraph Metrics Guide

TrustGraph exposes Prometheus metrics on a per-process `/metrics` HTTP
endpoint.  All metric names use the `tg_` prefix to avoid collisions
with library or infrastructure metrics.

Metrics are organised in three layers:

- **Layer 1 — Infrastructure** (automatic): message consumption,
  production, rate limiting, processor identity.  Emitted by
  `ReceiverPool` / `SenderPool` with no application code required.
- **Layer 2 — Service base classes** (semi-automatic): downstream call
  duration, embeddings / reranker / query / store service metrics.
  Instrumented in the base class; implementations inherit them.
- **Layer 3 — Application** (manual): agent orchestration, gateway,
  knowledge extraction, IAM, metering.  Added per-processor where
  domain-specific signals matter.


## Histogram bucket presets

Three centrally defined presets are available in
`trustgraph.base.metrics` for consistent histogram boundaries:

| Preset | Values | Use case |
|---|---|---|
| `BUCKETS_STANDARD` | 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0 | Internal RPCs, store operations, short-lived calls |
| `BUCKETS_LLM` | 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0 | LLM completions, embeddings, extraction |
| `BUCKETS_SESSION` | 1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0 | End-to-end user-facing requests, agent sessions |


## Metric reference

### Infrastructure (Layer 1)

These are emitted automatically for every consumer and producer
registered through the pool APIs.  Config-internal consumers
(registered with `instrument=False`) are excluded.

| Metric | Type | Labels | Description |
|---|---|---|---|
| `tg_consumer_state` | Enum | processor, consumer | Consumer lifecycle state (starting, running, stopped, error) |
| `tg_consumer_processing_total` | Counter | processor, consumer, status | Messages processed (status: ok, error) |
| `tg_consumer_rate_limit_total` | Counter | processor, consumer | TooManyRequests rate-limit events (not counted as errors) |
| `tg_consumer_request_duration_seconds` | Histogram | processor, consumer | Per-message processing latency |
| `tg_producer_messages_total` | Counter | processor, producer | Messages sent to output topics |
| `tg_config_version` | Gauge | processor | Current config version known to this processor |
| `tg_processor_info` | Info | processor | Static processor metadata (version, backend, etc.) |

### Downstream calls (Layer 2)

Instrumented automatically when `RequestResponseClient` is created
with `processor_id` and `target_service` parameters (wired by
`RequestResponseSpec` for flow processors, and by
`ServiceRequestor.start()` for the gateway).

| Metric | Type | Labels | Description |
|---|---|---|---|
| `tg_downstream_call_duration_seconds` | Histogram | processor, target_service | Round-trip latency for request/response calls |
| `tg_downstream_timeout_total` | Counter | processor, target_service | Calls that hit the timeout deadline |
| `tg_downstream_error_total` | Counter | processor, target_service, error_type | Downstream call errors by type |

### Embeddings service (Layer 2)

| Metric | Type | Labels | Description |
|---|---|---|---|
| `tg_embeddings_request_total` | Counter | processor, model | Embedding requests processed |
| `tg_embeddings_duration_seconds` | Histogram | processor, model | Embedding call latency |
| `tg_embeddings_batch_size` | Histogram | processor, model | Number of texts per request |

### Reranker service (Layer 2)

| Metric | Type | Labels | Description |
|---|---|---|---|
| `tg_reranker_request_total` | Counter | processor, model | Rerank requests processed |
| `tg_reranker_duration_seconds` | Histogram | processor, model | Rerank call latency |
| `tg_reranker_result_count` | Histogram | processor, model | Results returned per call |

### Query services (Layer 2)

| Metric | Type | Labels | Description |
|---|---|---|---|
| `tg_triples_query_duration_seconds` | Histogram | processor | Triples query backend latency |
| `tg_triples_query_result_count` | Histogram | processor | Triples returned per query |
| `tg_graph_embeddings_query_duration_seconds` | Histogram | processor | Graph embeddings query latency |
| `tg_graph_embeddings_query_result_count` | Histogram | processor | Entities returned per query |
| `tg_document_embeddings_query_duration_seconds` | Histogram | processor | Document embeddings query latency |
| `tg_document_embeddings_query_result_count` | Histogram | processor | Chunks returned per query |

### Store services (Layer 2)

Write metrics are defined in the base classes and inherited by all
backend implementations (Neo4j, Cassandra, Memgraph, FalkorDB, Qdrant,
Milvus, Pinecone).

| Metric | Type | Labels | Description |
|---|---|---|---|
| `tg_triples_store_write_duration_seconds` | Histogram | processor | Write latency per batch |
| `tg_triples_store_write_batch_size` | Histogram | processor | Triples per write batch |
| `tg_triples_store_write_error_total` | Counter | processor | Write errors |
| `tg_graph_embeddings_store_write_duration_seconds` | Histogram | processor | Write latency per batch |
| `tg_graph_embeddings_store_write_batch_size` | Histogram | processor | Embeddings per write batch |
| `tg_graph_embeddings_store_write_error_total` | Counter | processor | Write errors |
| `tg_document_embeddings_store_write_duration_seconds` | Histogram | processor | Write latency per batch |
| `tg_document_embeddings_store_write_batch_size` | Histogram | processor | Embeddings per write batch |
| `tg_document_embeddings_store_write_error_total` | Counter | processor | Write errors |

### LLM and vision services (Layer 2)

| Metric | Type | Labels | Description |
|---|---|---|---|
| `tg_text_completion_duration_seconds` | Histogram | processor | Text completion latency |
| `tg_text_completion_model` | Info | processor | Active LLM model metadata |
| `tg_image_to_text_duration_seconds` | Histogram | processor | Image-to-text latency |
| `tg_image_to_text_model` | Info | processor | Active vision model metadata |

### Tool services (Layer 2)

| Metric | Type | Labels | Description |
|---|---|---|---|
| `tg_tool_invocation_total` | Counter | processor, tool | Tool invocations |
| `tg_dynamic_tool_service_invocation_total` | Counter | processor | Dynamic tool service invocations |

### Agent orchestration (Layer 3)

Emitted by the ReAct agent processor.

| Metric | Type | Labels | Description |
|---|---|---|---|
| `tg_agent_session_total` | Counter | processor, outcome | Agent sessions (outcome: completed, max-iterations, error) |
| `tg_agent_iteration_count` | Histogram | processor | ReAct iterations per session |
| `tg_agent_tool_invocation_total` | Counter | processor, tool | Tool calls by tool name |
| `tg_agent_tool_duration_seconds` | Histogram | processor, tool | Per-tool invocation latency |
| `tg_agent_tool_error_total` | Counter | processor, tool | Tool invocation failures |
| `tg_agent_llm_duration_seconds` | Histogram | processor | LLM reasoning step latency |

### Gateway (Layer 3)

#### Request dispatch

| Metric | Type | Labels | Description |
|---|---|---|---|
| `tg_gateway_request_total` | Counter | service, status | Dispatched operations (status: ok, error) |
| `tg_gateway_request_duration_seconds` | Histogram | service | End-to-end request latency |

#### Authentication and authorisation

| Metric | Type | Labels | Description |
|---|---|---|---|
| `tg_gateway_signing_key_state` | Enum | — | IAM signing key fetch state (absent, present) |
| `tg_gateway_auth_failure_total` | Counter | reason | Authentication failures (reason: no-signing-key, invalid-jwt, jwt-missing-claims, anonymous-rejected, invalid-api-key) |
| `tg_gateway_authz_decision_total` | Counter | outcome | Authorisation decisions (outcome: allow, deny, error) |

#### Inventory

| Metric | Type | Labels | Description |
|---|---|---|---|
| `tg_gateway_known_workspaces` | Gauge | — | Workspaces known to the gateway |
| `tg_gateway_active_flow_count` | Gauge | — | Active flows tracked by the gateway |

### Knowledge extraction (Layer 3)

Shared metric names across all three extractors, distinguished by the
`extractor` label (`definitions`, `relationships`, `ontology`).

| Metric | Type | Labels | Description |
|---|---|---|---|
| `tg_extraction_duration_seconds` | Histogram | processor, extractor | Wall-clock time per chunk extraction |
| `tg_extraction_triple_total` | Counter | processor, extractor | Content triples produced |
| `tg_extraction_entity_total` | Counter | processor, extractor | Entities extracted (definitions extractor only) |
| `tg_extraction_empty_total` | Counter | processor, extractor | Chunks that yielded zero extractions |

#### Ontology-specific

| Metric | Type | Labels | Description |
|---|---|---|---|
| `tg_ontology_loaded_count` | Gauge | processor, workspace | Ontology definitions loaded from config |
| `tg_ontology_element_count` | Gauge | processor | Embedded ontology elements |
| `tg_ontology_selection_count` | Histogram | processor | Elements selected per chunk |
| `tg_ontology_selection_duration_seconds` | Histogram | processor | Similarity selection time per chunk |
| `tg_ontology_no_match_total` | Counter | processor | Chunks with no ontology match |

### IAM service (Layer 3)

| Metric | Type | Labels | Description |
|---|---|---|---|
| `tg_iam_request_total` | Counter | operation, outcome | Per-operation request count (outcome: ok, error, exception) |
| `tg_iam_request_duration_seconds` | Histogram | operation | Per-operation latency |
| `tg_iam_user_count` | Gauge | — | Total IAM users |
| `tg_iam_workspace_count` | Gauge | — | Total IAM workspaces |
| `tg_iam_api_key_created_total` | Counter | — | Lifetime API keys created |
| `tg_iam_api_key_revoked_total` | Counter | — | Lifetime API keys revoked |

### Chunking (Layer 3)

| Metric | Type | Labels | Description |
|---|---|---|---|
| `tg_chunk_size` | Histogram | processor | Size of produced text chunks |

### Metering (Layer 3)

| Metric | Type | Labels | Description |
|---|---|---|---|
| `tg_metering_tokens_total` | Counter | model, direction | Token count by model and direction (input/output) |
| `tg_metering_cost_usd_total` | Counter | model, direction | Estimated cost in USD |


## Adding new metrics

Follow these conventions when adding metrics:

1. **Prefix**: always use `tg_`.
2. **Naming**: `tg_{domain}_{noun}_{unit}` for histograms/gauges,
   `tg_{domain}_{noun}_total` for counters.
3. **Singleton pattern**: use `if not hasattr(__class__, "metric_name"):`
   to create metrics once per class, not per instance.
4. **Labels**: include `processor` where applicable. Use human-readable
   names for discriminating labels (e.g. `extractor="definitions"`),
   not topic names or internal IDs.
5. **Buckets**: use one of the three preset tuples from
   `trustgraph.base.metrics` rather than defining custom boundaries.
6. **TooManyRequests**: never count rate-limit retries as errors.
   They are tracked separately via `tg_consumer_rate_limit_total`.
7. **Config consumers**: register with `instrument=False` so internal
   config subscriptions don't pollute work metrics.
