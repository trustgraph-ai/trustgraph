#!/usr/bin/env python3
"""Capture TrustGraph GraphRAG explainability observations into JSONL."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Iterable

from evaluate import DatasetError, read_jsonl, validate_gold


def collect_stream(events: Iterable[Any]) -> dict[str, Any]:
    """Extract RAGChunk content/sources and ProvenanceEvent IDs without inventing text."""
    answer_parts: list[str] = []
    sources: dict[str, dict[str, str]] = {}
    provenance: list[dict[str, Any]] = []
    seen_rag_chunks = 0
    for event in events:
        # ProvenanceEvent has explain_id; RAGChunk carries content/sources.
        if hasattr(event, "explain_id"):
            provenance.append({
                "explain_id": str(event.explain_id),
                "explain_graph": str(getattr(event, "explain_graph", "")),
                "event_type": str(getattr(event, "event_type", "")),
                "triple_count": len(getattr(event, "triples", []) or []),
            })
            continue
        if not hasattr(event, "content"):
            raise DatasetError(f"unknown streaming item: {type(event).__name__}")
        seen_rag_chunks += 1
        if getattr(event, "error", None):
            raise RuntimeError(f"RAG stream error: {event.error}")
        if event.content is not None:
            if not isinstance(event.content, str):
                raise DatasetError("RAGChunk content must be text")
            answer_parts.append(event.content)
        for source in (getattr(event, "sources", None) or []):
            if not isinstance(source, dict) or not isinstance(source.get("uri"), str) or not source["uri"].strip():
                raise DatasetError("RAGChunk returned malformed source URI")
            uri = source["uri"]
            sources[uri] = {"uri": uri, "title": source.get("title", "")}
    if not seen_rag_chunks:
        raise RuntimeError("GraphRAG stream ended without an answer chunk")
    return {"answer": "".join(answer_parts), "sources": [sources[k] for k in sorted(sources)],
            "provenance": provenance}


def record_cases(gold: list[dict[str, Any]], *, url: str, flow_id: str, collection: str,
                 workspace: str, token: str | None, timeout: int, limit: int | None = None) -> list[dict[str, Any]]:
    """Calls the documented synchronous WebSocket graph_rag_explain API."""
    validate_gold(gold)
    try:
        from trustgraph.api import Api
    except ImportError as exc:
        raise RuntimeError("Install TrustGraph first: pip install ./trustgraph-base") from exc
    output = []
    with Api(url=url, timeout=timeout, token=token, workspace=workspace) as api:
        flow = api.socket().flow(flow_id)
        for case in gold[:limit]:
            result = collect_stream(flow.graph_rag_explain(query=case["question"], collection=collection))
            output.append({"id": case["id"], **result})
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--url", default="http://localhost:8888/")
    parser.add_argument("--flow", default="default")
    parser.add_argument("--collection", required=True)
    parser.add_argument("--workspace", default="default")
    parser.add_argument("--token-env", default="TRUSTGRAPH_API_TOKEN", help="Environment variable containing API bearer token")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    if args.timeout < 1 or (args.limit is not None and args.limit < 1):
        parser.error("--timeout and --limit must be positive")
    try:
        results = record_cases(
            read_jsonl(args.gold), url=args.url, flow_id=args.flow,
            collection=args.collection, workspace=args.workspace,
            token=os.environ.get(args.token_env), timeout=args.timeout, limit=args.limit,
        )
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in results), encoding="utf-8")
        print(f"Saved {len(results)} observation(s) to {output}")
    except (DatasetError, OSError, RuntimeError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
