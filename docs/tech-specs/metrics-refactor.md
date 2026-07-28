---
layout: default
title: "Metrics Refactor Technical Specification"
parent: "Tech Specs"
---

# Metrics Refactor Technical Specification

## Overview

This specification describes a refactor of TrustGraph's Prometheus metrics
to address issues inherited from the sync-to-async pub/sub migration,
reduce cardinality, improve naming consistency, and ensure all
observable behaviour is properly instrumented.

## Current State

### Metric Inventory

TrustGraph defines 19 Prometheus metrics across 8 files.  The tables
below document every metric as of v2.8.

#### Infrastructure metrics (metrics.py, wired via ReceiverPool / SenderPool)

| Metric | Type | Labels | Status | Notes |
|--------|------|--------|--------|-------|
| `consumer_state` | Enum | processor, consumer | Live | Running/stopped lifecycle, set on add/remove consumer |
| `request_latency` | Histogram | processor, consumer | Live | Handler wall-clock time (default buckets, max 10 s) |
| `processing_count` | Counter | processor, consumer, status | Live | Incremented per handler call with status ok/error |
| `rate_limit_count` | Counter | processor, consumer | Registered | Never incremented in the async path |
| `producer_count` | Counter | processor, producer | Live | Incremented on every ProducerHandle.send() |
| `processor` (processor_info) | Info | processor | Live | Emitted once at processor startup with config dict |
| `subscriber_state` | Enum | processor, subscriber | Dead | SubscriberMetrics class exists but nothing instantiates it |
| `received_count` | Counter | processor, subscriber | Dead | Same -- no async wiring |
| `dropped_count` | Counter | processor, subscriber | Dead | Same -- no async wiring |

#### Service-specific metrics

| Metric | Type | Labels | Defined in | Notes |
|--------|------|--------|------------|-------|
| `tool_invocation_count` | Counter | processor, tool | `base/tool_service.py` | Per-tool counter inside ToolService.on_request |
| `dynamic_tool_service_invocation_count` | Counter | processor | `base/dynamic_tool_service.py` | Single counter, no tool-name breakdown |
| `text_completion_duration` | Histogram | processor | `base/llm_service.py` | Custom buckets 0.25 s -- 120 s |
| `text_completion_model` | Info | processor | `base/llm_service.py` | Records model name and temperature |
| `image_to_text_duration` | Histogram | processor | `base/image_to_text_service.py` | Custom buckets 0.25 s -- 120 s |
| `image_to_text_model` | Info | processor | `base/image_to_text_service.py` | Records model name |
| `chunk_size` | Histogram | processor | `chunking/token/chunker.py` | Custom buckets 100 -- 16 000 |
| `chunk_size` | Histogram | processor | `chunking/recursive/chunker.py` | Same metric name, same buckets -- will collide if both chunkers run in one process |

#### Metering metrics

| Metric | Type | Labels | Defined in | Notes |
|--------|------|--------|------------|-------|
| `tokens` | Counter | model, direction | `metering/counter.py` | Cumulative token count, direction = input/output |
| `cost` | Counter | model, direction | `metering/counter.py` | Cumulative cost in USD |

### Known Issues

1. **Dead subscriber metrics.**  `SubscriberMetrics` (`subscriber_state`,
   `received_count`, `dropped_count`) is defined in metrics.py and
   exported from `trustgraph.base`, but nothing in the async path
   instantiates it.  The old sync `Subscriber` class created these; the
   async `ReceiverPool` replaced it but only creates `ConsumerMetrics`.

2. **`rate_limit_count` never incremented.**  The counter is registered
   when a `ConsumerMetrics` is constructed, but nothing in the async
   handler instrumentation calls `metrics.rate_limit()`.  Rate limiting
   is handled at a higher level (inside individual service classes) via
   the `TooManyRequests` exception (`trustgraph.exceptions`).  This
   exception is caught and re-raised in 11 service base classes
   (`llm_service`, `embeddings_service`, `tool_service`,
   `agent_service`, `reranker_service`, `image_to_text_service`,
   `dynamic_tool_service`, `triples_store_service`,
   `graph_embeddings_store_service`, `document_embeddings_store_service`,
   `keyword_index_service`).  The re-raise propagates up to the
   `ReceiverPool` worker, which negative-acknowledges the message, but
   no metric is recorded.  The instrumented handler currently counts
   `TooManyRequests` as `status="error"` in `processing_count` --
   there is no way to distinguish a rate-limit from a real failure.

3. **`request_latency` default buckets are too small.**  The Prometheus
   default Histogram buckets cap at 10 s.  LLM-backed processors
   routinely take 30--120 s per request.  Those observations land in the
   `+Inf` bucket, making p50/p90/p99 calculations meaningless for LLM
   processors.  (`text_completion_duration` has correct custom buckets
   but measures a different scope -- just the LLM call, not the full
   handler.)

4. **`chunk_size` name collision.**  Both `token/chunker.py` and
   `recursive/chunker.py` register a Histogram called `chunk_size` with
   the same label set.  If both chunkers are ever loaded in the same
   process the second registration will raise `ValueError: Duplicated
   timeseries`.  Today this doesn't happen because only one chunker type
   is deployed per container, but it is fragile.

5. **Naming inconsistency.**  Metric names follow no convention --
   `processing_count` vs `producer_count` vs `tool_invocation_count` vs
   `text_completion_duration` vs bare `tokens`.  The Prometheus naming
   best-practice is `<namespace>_<subsystem>_<name>_<unit>`.

6. **`consumer` label contains full topic names.**  The `consumer` label
   value is the raw topic string (e.g.
   `flow:tg:chunk-load:default:default`).  This is functionally correct
   but verbose in dashboards and couples metric queries to the topic
   naming scheme.

7. **No metrics for the gateway / API layer.**  The HTTP gateway
   (FastAPI) has no request-level metrics -- no request count, latency
   histogram, or error rate by endpoint.  Grafana dashboards must rely
   on external load-balancer metrics or have a blind spot.

8. **Singleton registration pattern is brittle.**  Every metric class
   uses `if not hasattr(__class__, "xxx_metric")` to guard
   `Counter(...)` / `Histogram(...)` calls.  This works but is easy to
   get wrong when subclassing or in tests (the `reset_metric_singletons`
   fixture exists solely to work around it).

9. **Config consumers pollute throughput/latency metrics.**  Every
   processor subscribes to `notify:tg:config` for config pushes.
   These are infrastructure housekeeping, not actual work, but they
   share the same `processing_count` and `request_latency` metrics as
   flow consumers.  An operator looking at throughput or p99 latency
   sees config updates mixed in with real request processing.  The
   `consumer` label can be used to filter, but aggregates across
   consumers are misleading by default.

10. **No config version metric.**  Every processor tracks
    `self.config_version` (an incrementing integer), but this is only
    visible in debug logs.  A gauge would let operators confirm that
    all processors are on the same config version, and alert when a
    processor is stuck on a stale version.

11. **No model identity metrics for embeddings or reranker.**
    `LlmService` records `text_completion_model` (Info) with model
    name and temperature.  `ImageToTextService` records
    `image_to_text_model`.  `EmbeddingsService` and `RerankerService`
    have no equivalent -- the active model is invisible to monitoring.

12. **No query-side latency metrics.**  `TriplesQueryService`,
    `GraphEmbeddingsQueryService`, and
    `DocumentEmbeddingsQueryService` have no duration histograms.
    The only latency signal is `request_latency` from the consumer
    instrumentation, which includes message deserialization and
    response serialisation overhead.  There is no metric for the
    actual backend query time (e.g. FalkorDB, Neo4j, Qdrant, Milvus).

### Desired Metrics

The following metrics are missing from the codebase and represent
observable behaviours that operators need for production support.
Organised by subsystem.

#### Pipeline / message bus

| Metric | Type | Labels | What it tracks |
|--------|------|--------|----------------|
| `work_queue_depth` | Gauge | processor | ReceiverPool work queue size -- backpressure indicator |
| `send_queue_depth` | Gauge | processor, producer | SenderPool per-producer queue size |
| `pending_acks` | Gauge | processor, consumer | Outstanding unacknowledged messages in receiver loop |
| `negative_ack_count` | Counter | processor, consumer | Messages nacked (requeued after handler failure) |
| `drain_timeout_count` | Counter | processor | Graceful-shutdown drain exceeded timeout |

#### Rate limiting

Rate-limit events (`TooManyRequests`) are retryable -- the message
gets nacked and redelivered.  They should NOT increment
`processing_count` at all because the work hasn't been done yet.
Instead, rate limits should be tracked as a separate signal that
indicates a resource needs scaling up.

| Metric | Type | Labels | What it tracks |
|--------|------|--------|----------------|
| `rate_limit_count` | Counter | processor, consumer | Already registered but never incremented; should fire when `TooManyRequests` is caught by the instrumented handler |

The instrumented handler in `ReceiverPool._instrumented_handler`
should catch `TooManyRequests` before the generic `Exception` handler
so that it increments `rate_limit_count` instead of
`processing_count{status="error"}`, and re-raises for the nack path.

#### Gateway / API layer

The gateway serves requests over two transports -- HTTP REST and
WebSocket -- but both converge at the `DispatcherManager` for
dispatch.  Auth and authorisation are transport-agnostic (same
`IamAuth` and operation registry).  The audit middleware already
captures per-request timing and metadata for HTTP, but there is no
Prometheus equivalent, and WebSocket has no request-level counting.

Gateway metrics should be transport-agnostic where possible.  A
"request" is a dispatched operation regardless of whether it arrived
as an HTTP POST or a WebSocket frame.

| Metric | Type | Labels | What it tracks |
|--------|------|--------|----------------|
| `gateway_request_count` | Counter | service, operation, status | Dispatched operations (HTTP + WebSocket), status = ok / error / auth-denied |
| `gateway_request_duration` | Histogram | service, operation | End-to-end latency from dispatch to final response (both transports) |
| `gateway_active_connections` | Gauge | transport | Active HTTP requests in flight + active WebSocket connections |
| `gateway_auth_failure_count` | Counter | reason | Malformed Bearer, missing token, expired JWT, invalid signature, unknown API key |

#### Gateway readiness / status

The gateway has startup dependencies that affect its ability to
serve requests.  These should be exposed as metrics so that
alerting can fire when the gateway is running but degraded.

| Metric | Type | Labels | What it tracks |
|--------|------|--------|----------------|
| `gateway_signing_key_state` | Enum | -- | Whether the IAM signing public key has been fetched (states: `absent`, `present`).  Without it, JWT validation fails and the gateway falls back to retry-on-request.  Currently `IamAuth._signing_public_pem` is `None` until fetched, with up to 30 retries at startup. |
| `gateway_known_workspaces` | Gauge | -- | Number of workspaces in `IamAuth.known_workspaces`.  Zero means the gateway will reject all workspace-scoped requests.  Populated by `ConfigReceiver` on config push. |

#### Config state

| Metric | Type | Labels | What it tracks |
|--------|------|--------|----------------|
| `config_version` | Gauge | processor | Current config version known to each processor.  Allows operators to confirm all processors converged to the same version after a config push. |

The config push consumer (`notify:tg:config`) should ideally be
excluded from `processing_count` and `request_latency`, or use a
distinct set of metrics, so that throughput and latency dashboards
reflect actual work rather than infrastructure housekeeping.

#### LLM / model services

| Metric | Type | Labels | What it tracks |
|--------|------|--------|----------------|
| `llm_retry_count` | Counter | processor, model | Retries before a successful LLM response |
| `llm_token_count` | Counter | processor, model, direction | Input/output tokens per call (distinct from metering -- this is per-processor, metering is per-model) |
| `llm_streaming_chunk_count` | Counter | processor | Chunks received in streaming mode |

#### Embeddings

The active model is resolved dynamically per request from the flow
parameter `flow("model")`, so model must be a label rather than an
Info metric.

| Metric | Type | Labels | What it tracks |
|--------|------|--------|----------------|
| `embeddings_request_count` | Counter | processor, model | Requests per model -- capacity signal, shows model mix |
| `embeddings_duration` | Histogram | processor, model | Embedding call latency per model (custom buckets) |
| `embeddings_batch_size` | Histogram | processor, model | Number of texts per embedding request |
| `embeddings_dimension` | Gauge | processor, model | Vector dimension size -- changes with model |

#### Reranker

Same dynamic model resolution as embeddings.

| Metric | Type | Labels | What it tracks |
|--------|------|--------|----------------|
| `reranker_request_count` | Counter | processor, model | Requests per model -- capacity signal |
| `reranker_duration` | Histogram | processor, model | Rerank call latency per model (custom buckets) |
| `reranker_result_count` | Histogram | processor, model | Number of results returned per rerank call |

#### Knowledge transformation pipeline

The extraction pipeline runs: Document → Decoder → Chunker →
Extractors (definitions, relationships, ontology, rows) → Store
writers.  Each stage has observable throughput and yield ratios
that are invisible today.

| Metric | Type | Labels | What it tracks |
|--------|------|--------|----------------|
| `decode_document_count` | Counter | processor, decoder_type | Documents decoded (PDF, OCR, etc.) |
| `decode_page_count` | Counter | processor, decoder_type | Pages produced per document decode |
| `chunk_count` | Counter | processor | Chunks produced (complements existing `chunk_size` histogram) |
| `chunks_per_document` | Histogram | processor | Yield ratio -- how many chunks per input document |
| `extraction_entity_count` | Counter | processor, extractor | Entities / relationships / rows extracted |
| `extraction_triple_count` | Counter | processor, extractor | Triples produced per extractor (definitions, relationships, ontology) |
| `extraction_duration` | Histogram | processor, extractor | Wall-clock time per chunk extraction (includes LLM call + parsing) |
| `extraction_empty_count` | Counter | processor, extractor | Chunks that yielded zero extractions -- signal of low-quality input or prompt issues |

The `extractor` label values would be: `definitions`,
`relationships`, `ontology`, `rows`, `topics`.

#### Ontology-specific extraction

The ontology extractor (`kg-extract-ontology`) selects a subset of
loaded ontology elements per chunk based on similarity.  This
selection process and its yield are invisible to monitoring today.

| Metric | Type | Labels | What it tracks |
|--------|------|--------|----------------|
| `ontology_loaded_count` | Gauge | processor | Number of ontology definitions loaded (from config) |
| `ontology_element_count` | Gauge | processor | Total embedded ontology elements (classes + properties) available for selection |
| `ontology_selection_count` | Histogram | processor | Number of ontology elements selected per chunk (classes + object properties + datatype properties) |
| `ontology_selection_duration` | Histogram | processor | Time for the similarity-based ontology subset selection step |
| `ontology_no_match_count` | Counter | processor | Chunks where no relevant ontology elements were found (early return, zero extraction) |

Per-chunk processing should also emit counts broken down by
workspace and ontology.  Both are operator-controlled bounded sets,
so the cardinality is safe.

| Metric | Type | Labels | What it tracks |
|--------|------|--------|----------------|
| `ontology_extraction_triple_count` | Counter | processor, workspace, ontology | Triples produced per workspace × ontology combination |
| `ontology_extraction_entity_count` | Counter | processor, workspace, ontology | Entities / entity-contexts produced per workspace × ontology |
| `ontology_chunk_count` | Counter | processor, workspace, ontology | Chunks processed per workspace × ontology |

These answer: which ontology is producing results?  Is one workspace
getting all the extractions while another yields nothing?  Which
ontology should be tuned or retired?

The broader metrics above (`ontology_selection_count`, etc.) answer
whether the ontology is well-fitted.  These per-workspace counters
answer whether the deployment is balanced.

#### Knowledge transformation summary

These metrics collectively answer operational questions like:
- What is the extraction yield per document?
- Which extractor is the bottleneck?
- What fraction of chunks produce nothing?
- How does extraction throughput scale with document volume?

#### Storage backends (write path)

| Metric | Type | Labels | What it tracks |
|--------|------|--------|----------------|
| `store_write_duration` | Histogram | processor, store_type | Write latency for triples / graph-embeddings / doc-embeddings stores |
| `store_write_count` | Counter | processor, store_type | Successful writes |
| `store_error_count` | Counter | processor, store_type, error_type | Write failures by category |
| `cassandra_query_duration` | Histogram | keyspace, operation | CQL query latency (select / insert / delete) |

#### Storage backends (query path)

| Metric | Type | Labels | What it tracks |
|--------|------|--------|----------------|
| `query_duration` | Histogram | processor, store_type | Backend query time for triples / graph-embeddings / doc-embeddings queries (the actual DB/vector-store call, not the full handler) |
| `query_result_count` | Histogram | processor, store_type | Number of results returned per query -- useful for tuning limits and detecting empty-result patterns |

#### IAM / auth

| Metric | Type | Labels | What it tracks |
|--------|------|--------|----------------|
| `iam_login_count` | Counter | outcome | Successful / failed login attempts |
| `iam_auth_decision_count` | Counter | outcome | Allow / deny authorisation decisions |
| `iam_api_key_resolution_count` | Counter | outcome | API key lookups (valid / invalid / expired) |
| `auth_cache_hit_count` | Counter | cache_type | JWT validation / authorisation cache hits vs misses |
| `signing_key_fetch_count` | Counter | outcome | Signing key retrieval successes / failures / retries |

#### Knowledge cores

| Metric | Type | Labels | What it tracks |
|--------|------|--------|----------------|
| `core_operation_duration` | Histogram | processor, operation | Load / save / delete / list latency |
| `core_loader_queue_depth` | Gauge | processor | Background loader queue saturation (maxsize=20) |

#### Librarian / document management

| Metric | Type | Labels | What it tracks |
|--------|------|--------|----------------|
| `librarian_operation_duration` | Histogram | operation | add-document / remove-document / update latency |
| `blob_store_bytes` | Counter | operation | Bytes uploaded / downloaded to blob store |

#### System inventory

High-level gauges that give operators and dashboards a snapshot of
the deployment's scale.  These are slow-moving values, suitable for
scrape intervals of 30--60 s.

| Metric | Type | Labels | What it tracks | Source |
|--------|------|--------|----------------|--------|
| `iam_user_count` | Gauge | -- | Total registered users | IAM service (Cassandra users table) |
| `iam_workspace_count` | Gauge | -- | Total workspaces | IAM service or config service (`__workspaces__` registry) |
| `active_flow_count` | Gauge | processor | Number of running flow instances per processor | `FlowProcessor.flows` dict size |
| `librarian_document_count` | Gauge | -- | Total documents in the librarian | Librarian service |

These answer at-a-glance questions: how big is the deployment, is
it growing, did a workspace or flow disappear unexpectedly?

#### Agent orchestration

The ReAct agent loop (`agent/react/agent_manager.py`) is the
highest-value user-facing path and currently has zero metrics.
Each agent session runs up to `max_iterations` (default 10) cycles
of think → act → observe.  Tools are invoked via
request/response messaging; MCP tools make HTTP calls to external
servers.

| Metric | Type | Labels | What it tracks |
|--------|------|--------|----------------|
| `agent_session_count` | Counter | processor, outcome | Agent sessions started; outcome = completed / max-iterations / error / timeout |
| `agent_session_duration` | Histogram | processor | Total wall-clock time per agent session |
| `agent_iteration_count` | Histogram | processor | Number of ReAct iterations per session (distribution tells you if agents are solving in 2 steps or grinding to 10) |
| `agent_tool_invocation_count` | Counter | processor, tool | Tool calls per tool name -- shows which tools the agent uses most |
| `agent_tool_duration` | Histogram | processor, tool | Per-tool invocation latency (helps identify slow tools) |
| `agent_tool_error_count` | Counter | processor, tool, error_type | Tool invocation failures by type (timeout, service-error, parse-error) |
| `agent_llm_duration` | Histogram | processor | LLM reasoning step latency per iteration (separate from tool time) |
| `agent_mcp_invocation_count` | Counter | processor, mcp_tool | MCP tool calls specifically -- external service dependency |
| `agent_mcp_duration` | Histogram | processor, mcp_tool | MCP tool latency (includes HTTP round-trip to external server) |
| `agent_mcp_error_count` | Counter | processor, mcp_tool, error_type | MCP failures: connection refused, timeout, protocol error, auth failure |

These answer: how often do agents solve on first try vs grind?
Which tools are hot?  Are MCP tools reliable?  Where is the agent
spending its time -- thinking or acting?

#### Timeouts and downstream failures

Timeouts are a critical operational signal across Graph RAG,
Document RAG, and agent orchestration.  Each service makes
cascading downstream calls with different timeout budgets:

| Service | Downstream call | Default timeout |
|---------|----------------|-----------------|
| Agent (ReAct) | Prompt/LLM | 600 s |
| Agent (ReAct) | Tool service | 600 s |
| Agent (ReAct) | MCP tool (HTTP) | no explicit timeout |
| Graph RAG | Prompt (concept extraction) | 600 s |
| Graph RAG | Embeddings | 300 s |
| Graph RAG | Graph embeddings query | 30 s (× N entities) |
| Graph RAG | Triples query | 300 s |
| Graph RAG | Reranker | 300 s |
| Document RAG | Document embeddings query | 30 s |
| Document RAG | Chunk fetch | 120 s |
| All services | Config fetch | 60 s |
| All services | Librarian | 120 s |

Cascading timeouts are a problem: Graph RAG can accumulate
600 s + 300 s + (30 s × N entities) + 300 s = 1000 s+ without
any single call exceeding its budget.  No deadline propagation
exists.

Today, all timeouts surface as `asyncio.TimeoutError` and are
indistinguishable from other exceptions in metrics.  The proposed
metrics:

| Metric | Type | Labels | What it tracks |
|--------|------|--------|----------------|
| `timeout_count` | Counter | processor, target_service | Timeout events by which downstream service timed out (prompt, embeddings, triples-query, graph-embeddings-query, reranker, librarian, mcp-tool) |
| `downstream_call_duration` | Histogram | processor, target_service | Latency of downstream request/response calls -- shows how close calls are to their timeout budget |
| `downstream_error_count` | Counter | processor, target_service, error_type | Non-timeout errors by downstream service and type (service-error, connection-refused, parse-error) |

The `error_type` label should distinguish at minimum:
- `timeout` -- asyncio.TimeoutError
- `rate-limited` -- TooManyRequests
- `service-error` -- error response from downstream
- `connection-error` -- broker / network failure

This replaces the current undifferentiated `processing_count{status="error"}`
with structured error attribution.

#### Config service

| Metric | Type | Labels | What it tracks |
|--------|------|--------|----------------|
| `config_push_count` | Counter | -- | Config version push events (global, not per-workspace to avoid cardinality) |
| `config_provision_duration` | Histogram | -- | Time to provision a workspace from template |

## Goals

1. Every operationally significant behaviour emits a metric without
   requiring service-specific code where possible.
2. Metrics are correctly categorised: infrastructure housekeeping
   (config pushes) does not pollute work throughput/latency.
3. Histogram buckets match the expected latency range of each
   operation.
4. Cardinality is bounded by operator-controlled dimensions only.
5. Existing dead metrics are removed rather than carried forward.
6. New dashboards can be designed from a clean, consistent metric
   schema.

## Technical Design

### Metric Layers

Metrics are organised into three layers.  Each layer has a clear
owner and instrumentation strategy.

**Layer 1 — Infrastructure (automatic).**
Instrumented by `ReceiverPool` and `SenderPool`.  Every consumer
and producer gets throughput, latency, state, and error metrics
without any service code.  This is the current `ConsumerMetrics` /
`ProducerMetrics` mechanism.

**Layer 2 — Service base class (semi-automatic).**
Instrumented by service base classes (`LlmService`,
`EmbeddingsService`, `RerankerService`, `TriplesQueryService`,
etc.).  Each base class defines metrics appropriate to its domain
(LLM duration, embedding batch size, query result count, etc.).
Service implementations inherit these without additional code.

**Layer 3 — Application (manual).**
Instrumented by individual processors where domain-specific
metrics are needed (ontology selection counts, chunk size
distribution, agent iteration counts, etc.).  These are opt-in
and defined in the processor code.

### Consumer vs Subscriber: Unify and Simplify

**Decision: remove `SubscriberMetrics` entirely.**

The consumer/subscriber distinction was a sync-era artefact.  The
old sync codebase had separate `Consumer` (request/response pattern)
and `Subscriber` (pub/sub, fire-and-forget) classes, each with their
own metrics.  In the async architecture, `ReceiverPool` handles both
patterns identically — receive message, dispatch to handler, ack or
nack.  There is no behavioural difference that warrants separate
metric classes.

`ConsumerMetrics` already captures everything needed:
- `consumer_state` — lifecycle (running/stopped)
- `processing_count` — throughput with ok/error status
- `request_latency` — handler duration
- `rate_limit_count` — backpressure signal

The subscriber-specific metrics (`received_count`, `dropped_count`)
mapped to concepts that no longer exist in the async model:
- `received_count` was incremented before processing — in the pool
  model, receiving and processing are decoupled (receiver loop vs
  worker pool), so a pre-processing count is just a noisier version
  of `processing_count`.
- `dropped_count` tracked messages that couldn't be processed — in
  the pool model, these surface as nacks and
  `processing_count{status="error"}`.

**Action:** delete `SubscriberMetrics` from `metrics.py`, remove
the export from `__init__.py`, and remove the two remaining call
sites in `trustgraph-flow` (`agent/react/tools.py`).

### Config Consumer: Exclude from Work Metrics

**Decision: config consumers should not be instrumented.**

The `notify:tg:config` consumer is infrastructure housekeeping.
It processes config push notifications (a few per deployment
lifetime), not user-driven work.  Including it in
`processing_count` and `request_latency` pollutes aggregates and
makes dashboards misleading.

`ReceiverPool.add_consumer()` gains an `instrument` parameter
(default `True`).  When `False`, no `ConsumerMetrics` is created
and the handler is not wrapped.

```python
# AsyncProcessor.start() — config consumer, no metrics
self._config_consumer_reg = \
    await self.receiver_pool.add_consumer(
        topic=self.config_push_queue,
        subscription=config_subscriber_id,
        schema=ConfigPush,
        handler=config_notify_handler,
        initial_position='latest',
        instrument=False,
    )
```

Config version tracking is handled separately via a
`config_version` gauge (see desired metrics above), set in
`on_config_notify` when the version advances.

**The principle:** Layer 1 consumer metrics (`processing_count`,
`request_latency`, `consumer_state`, `rate_limit_count`) exist to
measure the main processing queues — the actual work a processor
was deployed to do.  The prompt processor's metrics should reflect
prompt requests.  The chunker's metrics should reflect documents
chunked.  Infrastructure housekeeping like config pushes, which
every processor subscribes to, must not appear in these metrics.
Otherwise aggregates are inflated and latency percentiles are
skewed by fast, low-value config operations mixed in with real
work.

Before (current state, prompt processor):
```
processing_count_total{processor="prompt", consumer="notify:tg:config", status="ok"} 10
processing_count_total{processor="prompt", consumer="request:tg:prompt:default:default", status="ok"} 30
# sum = 40, but only 30 are real prompt requests
```

After (config consumer uninstrumented):
```
processing_count_total{processor="prompt", consumer="request:tg:prompt:default:default", status="ok"} 30
# sum = 30, reflects actual work done
```

### Rate Limiting: Separate from Errors

**Decision: `TooManyRequests` gets its own path in the
instrumented handler.**

The instrumented handler in `ReceiverPool._instrumented_handler`
currently catches `Exception` and records `status="error"`.
`TooManyRequests` is a retryable signal, not a failure.  It should:

1. Increment `rate_limit_count` (already registered, never used).
2. NOT increment `processing_count` (work was not done).
3. NOT record in `request_latency` (no meaningful duration).
4. Re-raise for the nack/redelivery path.

```python
async def wrapper(message):
    with metrics.record_time():
        try:
            await handler(message)
            metrics.process("ok")
        except TooManyRequests:
            metrics.rate_limit()
            raise
        except Exception:
            metrics.process("error")
            raise
```

Note: `record_time()` is a context manager that always records
on exit.  For rate-limited requests, we should skip the timing
entirely since the duration is meaningless.  This requires
restructuring to separate the timing from the try/except:

```python
async def wrapper(message):
    try:
        t0 = time.monotonic()
        await handler(message)
        metrics.observe_latency(time.monotonic() - t0)
        metrics.process("ok")
    except TooManyRequests:
        metrics.rate_limit()
        raise
    except Exception:
        metrics.observe_latency(time.monotonic() - t0)
        metrics.process("error")
        raise
```

### request_latency: Custom Buckets

**Decision: `request_latency` gets medium-ops buckets globally.**

The current default buckets (max 10 s) are wrong for most
processors.  Replacing with medium-ops buckets
(0.05 -- 30 s) covers the majority of handler durations.

Processors with genuinely different profiles (LLM services,
agent orchestration) already define their own histograms
(`text_completion_duration`, `agent_session_duration`) with
appropriate buckets.  `request_latency` captures the full
handler duration including message deserialisation and response
send — it is a coarse-grained signal, not the primary latency
metric for specialised services.

### Namespace Prefix

**Decision: adopt `tg_` prefix for all new metrics.**

Prometheus best practice is `<namespace>_<subsystem>_<name>`.
A short `tg_` prefix avoids collisions with other exporters
(Python runtime, process metrics) without excessive verbosity.

Existing metrics will be renamed in the refactor (no deprecation
period — dashboards are being redesigned).

Examples:
- `processing_count` → `tg_consumer_processing_total`
- `producer_count` → `tg_producer_messages_total`
- `request_latency` → `tg_consumer_request_duration_seconds`
- `text_completion_duration` → `tg_llm_request_duration_seconds`
- `tokens` → `tg_metering_tokens_total`

### Downstream Call Instrumentation

**Decision: instrument at the `RequestResponseClient` level.**

Most downstream calls (embeddings, triples query, graph embeddings
query, reranker, prompt, librarian) flow through
`RequestResponseClient.request()`.  This is the natural
instrumentation point for `downstream_call_duration` and
`timeout_count` — a single code change covers all downstream
services.

The `target_service` label can be derived from the request topic
name, which the client already knows.

```python
# In RequestResponseClient.request():
t0 = time.monotonic()
try:
    result = await asyncio.wait_for(future, timeout=timeout)
    DownstreamMetrics.observe(self.request_topic, time.monotonic() - t0)
    return result
except asyncio.TimeoutError:
    DownstreamMetrics.timeout(self.request_topic)
    raise
```

### Singleton Pattern: Keep but Standardise

The `hasattr(__class__, ...)` singleton pattern works correctly in
the multi-processor container model.  Each metric name is registered
once per process, with label values providing per-processor
discrimination.  The pattern is well-understood and the
`reset_metric_singletons` test fixture handles the test-isolation
concern.

Replacing it with a registry abstraction would add complexity
without solving a real problem.  Standardise the pattern (consistent
naming, always use `__class__`, always guard with `hasattr`) but
do not replace it.

### Architectural Constraints

1. **Multi-processor containers.**  Containers like `ingest`,
   `control`, `rag` each bundle multiple processors sharing a single
   metrics port (8000) and a single Prometheus registry.  The
   `hasattr(__class__, ...)` singleton pattern ensures each metric
   name is registered once per process, with the `processor` label
   distinguishing instances.  This means per-processor isolation is
   not possible without splitting containers or running separate
   registries.  All proposed metrics must work within this shared-
   registry model.

2. **Stale time series.**  When a flow is stopped or a consumer
   removed, Prometheus retains the last-scraped value until
   retention expires.  A deleted workspace's
   `consumer_state{..., consumer_state="running"}=1` will linger as
   a phantom.  There is no application-side mechanism to remove stale
   series.  Dashboards must account for this (e.g. filtering on
   recent `up` or using `absent()` / recording rules).

### Histogram Bucket Strategy

Each histogram should define buckets appropriate to its expected
latency range.  Using Prometheus defaults (max 10 s) for all
histograms is the root cause of issue 3 (`request_latency` overflow).

| Latency class | Bucket range | Applies to |
|---------------|-------------|------------|
| Fast ops | 0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5 s | `query_duration`, `store_write_duration`, `ontology_selection_duration`, `config_provision_duration` |
| Medium ops | 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0 s | `request_latency` (refactored), `embeddings_duration`, `reranker_duration`, `downstream_call_duration`, `gateway_request_duration` |
| LLM-scale ops | 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0 s | `text_completion_duration` (existing), `extraction_duration`, `agent_llm_duration`, `agent_tool_duration`, `agent_mcp_duration` |
| Session-scale ops | 1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0 s | `agent_session_duration`, `core_operation_duration`, `librarian_operation_duration` |

Count-based histograms (not time):

| Distribution | Bucket range | Applies to |
|-------------|-------------|------------|
| Small counts | 1, 2, 5, 10, 20, 50, 100 | `agent_iteration_count`, `chunks_per_document`, `reranker_result_count`, `ontology_selection_count` |
| Medium counts | 1, 5, 10, 25, 50, 100, 250, 500, 1000 | `embeddings_batch_size`, `extraction_entity_count`, `extraction_triple_count`, `query_result_count` |

### Cardinality Policy

Cardinality is allowed where it adds operational value, subject to
these constraints:

- **Operator-controlled dimensions only.**  Labels like `workspace`,
  `ontology`, `model`, `tool` are bounded by operator configuration,
  not by user activity or data volume.  These are acceptable.
- **No user-derived or data-derived labels.**  User IDs, document
  IDs, request IDs, topic content must never appear as label values.
- **Review histograms × labels carefully.**  Each histogram bucket
  is a separate time series.  A histogram with 15 buckets and a
  label with 10 values = 150 series per processor.  Histograms with
  high-cardinality labels are the most expensive combination and
  must be justified.
- **Prefer counters for high-cardinality breakdowns.**  If you need
  per-model, per-tool, or per-workspace breakdowns, counters are
  cheap (1 series per combination).  Histograms should only carry
  those labels if the latency distribution genuinely varies by that
  dimension.

### Dashboard Strategy

Existing Grafana dashboards are of limited use and will not
constrain the metric refactor.  New dashboards will be designed
alongside the new metric schema.  This avoids a migration /
backwards-compatibility tax -- metric names can be renamed freely
without a deprecation period.

### Decisions

- **Gateway instrumentation**: custom instrumentation at the
  dispatcher level, not transport-layer middleware.  Both HTTP and
  WebSocket dispatch to the same `DispatcherManager` and represent
  the same logical operations.  HTTP-centric libraries like
  `prometheus_fastapi_instrumentator` would miss WebSocket requests
  entirely.

## Open Questions

_None remaining — all resolved.  See Decisions below._

## Future Design Goal: Document Pipeline Progress

A key gap today is the inability to answer "how much work is
left?" for a document flowing through the ingest pipeline.  A
document enters as a single blob, fans out through decode →
chunk → N extractors → store writes, and there is no way to
tell from metrics whether processing is complete, stalled, or
partially done.

### The problem

The pipeline is a DAG with fan-out:

```
Document (1)
  → Decoder (1 → N pages)
    → Chunker (N pages → M chunks)
      → Definitions extractor (M chunks → ? triples)
      → Relationships extractor (M chunks → ? triples)
      → Ontology extractor (M chunks → ? triples)
      → Row extractor (M chunks → ? rows)
        → Triples store writer
        → Graph embeddings store writer
        → Document embeddings store writer
```

No single processor sees the full picture.  The chunker knows how
many chunks it emitted but not how many have been fully extracted.
The store writers know what they received but not what's still in
flight upstream.

### Approach: emit/complete counters per document

Each stage emits a count of items it produced and a count of items
it completed.  By comparing these across stages, the outstanding
work for a document can be derived.

| Metric | Type | Labels | What it tracks |
|--------|------|--------|----------------|
| `tg_pipeline_emitted_total` | Counter | processor, stage | Items emitted to the next stage (chunks produced, triples sent, etc.) |
| `tg_pipeline_completed_total` | Counter | processor, stage | Items whose processing completed at this stage |

Outstanding work at any stage =
`sum(tg_pipeline_emitted_total{stage="chunker"})` −
`sum(tg_pipeline_completed_total{stage="triples-store"})`.

This requires a correlation mechanism — each item must carry a
document ID through all stages so that per-document progress can
be calculated.  The `metadata.id` field on chunks and triples
already serves this purpose, but it is not currently exposed as a
metric dimension (and should not be — document IDs are unbounded
cardinality).

### Practical options

1. **Aggregate counters only (no per-document breakdown).**
   Track total emitted vs total completed across the pipeline.
   Gives a global "work outstanding" gauge but cannot distinguish
   a stuck document from normal processing lag.  Cheapest to
   implement.

2. **Per-document state in an external store.**
   Write document lifecycle events (entered-pipeline,
   chunking-complete, extraction-complete, store-complete) to
   Cassandra or a dedicated state table.  Query the table for
   per-document progress.  More expensive but gives per-document
   visibility.  Could power a UI progress bar.

3. **Pipeline depth gauge.**
   Each stage increments a gauge on entry and decrements on exit.
   `tg_pipeline_in_flight{stage="definitions-extractor"}` gives a
   real-time count of items being processed at each stage.
   Combined with throughput rates, this gives estimated time to
   completion.  Does not give per-document breakdown but is cheap
   and immediately useful.

Option 3 is the likely starting point — it answers "is the
pipeline draining or backing up?" without per-document cardinality.
Options 1 and 2 can be layered on top in subsequent phases.

This is a phase 2 goal and is out of scope for the initial metrics
refactor.

## Resolved Questions

- **Histogram bucket parameterisation.**  Define centrally named
  bucket presets that services can invoke.  Three standard profiles:
  - `BUCKETS_STANDARD` — fast/medium ops (default for most
    consumers and downstream calls)
  - `BUCKETS_LLM` — LLM-scale latencies (0.25 -- 120 s)
  - `BUCKETS_SESSION` — agent/session-scale (1 -- 600 s)

  Service base classes select the appropriate preset.  Individual
  processors should not need to define custom buckets.

- **`tg_` prefix scope.**  Applies to everything, including metering
  metrics (`tokens` → `tg_metering_tokens_total`, `cost` →
  `tg_metering_cost_total`).  One namespace, no exceptions.

- **`target_service` label derivation.**  Callers pass an explicit
  human-readable service name (e.g. `embeddings`, `triples-query`,
  `prompt`, `reranker`, `librarian`).  Topic names are communication
  wiring details and should not leak into metric labels — they are
  opaque, verbose, and couple dashboards to the pub/sub topology.
