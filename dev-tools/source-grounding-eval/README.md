# GraphRAG source-grounding evaluation (experimental)

A small, reproducible **document-source coverage** benchmark for TrustGraph's
explainable GraphRAG stream. Designed to identify when GraphRAG returns the
wrong source documents, misses required evidence sources, or returns sources
for questions the corpus cannot answer.

**This is not an automatic factual-faithfulness metric.** A correct source URI
does not prove that the answer's claims are supported by the passage. Passage
tracing, contradiction resolution, and appropriate abstention need **manual
review labels** and are reported separately when supplied.

## Why this integration

TrustGraph's `Api.socket().flow(flow_id).graph_rag_explain(query, collection)`
returns a stream of `RAGChunk` (answer content plus a final `sources` field) and
`ProvenanceEvent` instances (explainability event IDs, graphs, inline triples).
This harness observes those existing interfaces and **does not modify** the
retrieval or ingestion pipeline.

## Files

- `record.py` — captures actual streaming answers, source `uri`/`title` pairs,
  and provenance event IDs/counts from a live TrustGraph instance
- `evaluate.py` — validates gold/observations, scores exact source-URI coverage,
  emits case-level errors and an aggregate JSON report
- `fixtures/corpus.synthetic.jsonl` — tiny *fictional* document corpus for
  illustrating the intended benchmark
- `fixtures/gold.synthetic.jsonl` — 12 *fictional* questions covering single
  source, multi-source, conflicting versions, and unanswerable cases
- `fixtures/observations.synthetic.jsonl` — artificial predictions designed to
  show both correct matches and failures (**not TrustGraph output**)
- `tests/` — offline deterministic tests; no database, LLM, or TrustGraph
  installation required for unit tests

## Run the offline, synthetic demonstration

Run from this directory:

```bash
python3 evaluate.py \
  --gold fixtures/gold.synthetic.jsonl \
  --observations fixtures/observations.synthetic.jsonl \
  --output report.synthetic.json \
  --require-complete
```

This demonstrates scoring logic only. **Never cite `report.synthetic.json` as a
measured TrustGraph benchmark.**

## Run against a real TrustGraph instance

1. Start TrustGraph and a running flow with a populated collection. Install
   the Python API package from the repository root as documented in
   `tests/RUNNING-TESTS.md`, for example `pip install ./trustgraph-base` in a
   dedicated virtual environment.
2. Ingest a small corpus you control. Verify each document's **actual**
   source URI emitted by GraphRAG; URI values must be copied exactly, rather
   than inferred from filenames or titles.
3. Create `gold.local.jsonl` with ground-truth questions and expected *actual*
   source URIs. Start by copying `fixtures/gold.synthetic.jsonl`, but replace
   its sample IDs/evidence with your own. The example corpus is **not**
   automatically ingested or mapped by this tool.
4. Record live answers and score them:

```bash
# Set TRUSTGRAPH_API_TOKEN in your environment only if authentication is used.
python3 record.py \
  --gold gold.local.jsonl \
  --collection my-collection \
  --flow default \
  --url http://localhost:8888/ \
  --output observations.local.jsonl

python3 evaluate.py \
  --gold gold.local.jsonl \
  --observations observations.local.jsonl \
  --output report.local.json \
  --require-complete
```

Use `--workspace`, `--timeout`, `--token-env` and `--limit` as appropriate.
`record.py` fails on stream errors instead of silently scoring an empty answer.
If any query fails, it does **not** write a partial report; retry after fixing
the service. Do not publish private source text, credentials, or answers.

## Gold format (`.jsonl`)

One JSON object per line:

```json
{"id":"case-1","question":"What changed between policy versions?","answerability":"conflicting","expected_source_uris":["urn:doc:policy-v1","urn:doc:policy-v2"],"evidence":[{"source_uri":"urn:doc:policy-v1","passage":"Policy v1 says 10 days."},{"source_uri":"urn:doc:policy-v2","passage":"Policy v2 says 15 days."}]}
```

`answerability` is one of `answerable`, `conflicting`, `unanswerable`.
Unanswerable cases must have an empty expected source list; the other two
require at least one. `evidence` contains manually checked gold excerpts and
is **not** treated as automatically validated against an indexed document.

## Observation format (`.jsonl`)

`record.py` creates `id`, `answer`, `sources: [{uri, title}]`, and
`provenance: [{explain_id, explain_graph, event_type, triple_count}]`.
The `sources` field is document-level; it is **not** a ranked list of
retrieved passages. In particular **Recall@k is not calculated**: calling
these final response citations "top-k retrieval recall" would be misleading.

Reviewers can add an optional `review` object to each observation manually:

```json
{"id":"case-1","answer":"Version 1 was 10 days, version 2 was 15 days.","sources":[{"uri":"urn:doc:policy-v1"},{"uri":"urn:doc:policy-v2"}],"review":{"answer_supported":true,"passage_trace_verified":true,"conflict_handled":true}}
```

The optional review booleans are:

- `answer_supported`: every factual answer claim is actually entailed by the
  cited original passages (human judgment)
- `passage_trace_verified`: a reviewer traced the provenance to source text
  (not merely a matching document URI)
- `abstained_appropriately`: a reviewer judged the abstention on an
  unanswerable query (there is no simple phrase-matching abstention heuristic)
- `conflict_handled`: both versions/claims were treated appropriately

Unset labels are omitted from both numerator and denominator, so review
coverage is transparent. Reviewers should manually read the original
passages and document their criteria before using these fields.

## Metrics and interpretation

- **Micro source precision**: true-positive source URIs / all returned source
  URIs across evaluated questions.
- **Micro source recall**: true-positive source URIs / all expected source
  URIs across evaluated questions.
- **Macro source recall**: unweighted mean of per-case recall on cases with
  expected source URIs.
- **Exact source-set rate**: fraction of answerable/conflicting cases where
  returned document IDs exactly equal expected document IDs.
- **Unanswerable-without-sources rate**: fraction of unanswerable cases where
  the system returned zero source URIs. This is **not an abstention metric**.
- **Human-reviewed positive rates**: per-label positives / reviewed cases;
  `null` means there are no adjudications (or the denominator is empty).

All source matching uses *exact* URI comparison. Renaming, canonicalization,
passage ranking, semantic entailment, and extraction-provenance graph walking
are out of scope for this focused first iteration. A false negative may also
mean that the result emitted a different but valid source URI; inspect the
case details and gold labels before filing a product bug.

## Unit tests

```bash
python3 -m pip install pytest
python3 -m pytest tests -q
```

The tests use shaped fake stream events to check the known
`RAGChunk`/`ProvenanceEvent` data contract. They are **not** end-to-end
integration tests. A genuine TrustGraph server and real ingested documents are
required to validate actual source tracing.

## Suggested follow-up

Once the source-URI benchmark is accepted, add an integration fixture with
stable actual document IDs, and a source-chain resolver that walks selected
edges through chunk/page/document provenance with verifiable passage text.
That should be a separate PR with integration tests, not a claim implied by
this harness.
