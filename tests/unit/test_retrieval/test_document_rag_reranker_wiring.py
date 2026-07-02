"""
Cross-layer wiring contract for the Document-RAG reranker (issue #878).

The Document-RAG processor registers a ``RerankerClientSpec`` for the
``reranker-request`` / ``reranker-response`` roles (see
``retrieval/document_rag/rag.py``). At flow construction every spec runs
``spec.add(flow, processor, definition)``, and ``RequestResponseSpec.add``
resolves its topics via ``definition["topics"][name]`` - which raises
``KeyError`` if the flow blueprint does not provide those topics.

This means the monorepo code change is only safe to deploy together with the
companion ``trustgraph-templates`` change that wires ``reranker-request`` /
``reranker-response`` into the Document-RAG flow (mirroring what templates
PR #279 did for GraphRAG via ``graph-store.jsonnet``). These tests pin that
contract from the monorepo side:

  * with the reranker topics present (as the updated templates compile them),
    the spec binds cleanly and registers the client;
  * without them (the pre-companion blueprint), construction fails fast with a
    KeyError naming the missing role - documenting exactly why the templates
    change is required.

No broker/network: the pub/sub backend is mocked (topics are bound at add()
time, connections happen later at start()).
"""

import pytest
from unittest.mock import MagicMock

from trustgraph.base import RerankerClientSpec


def _flow():
    f = MagicMock()
    f.workspace = "ws"
    f.name = "document-rag"
    f.id = "proc1"
    f.consumer = {}
    return f


def _processor():
    p = MagicMock()
    p.pubsub = MagicMock()
    p.id = "proc1"
    p.taskgroup = MagicMock()
    return p


def _spec():
    return RerankerClientSpec(
        request_name="reranker-request",
        response_name="reranker-response",
    )


# Topics dict as the UPDATED document-store.jsonnet compiles them
# (verified by compiling the template: reranker-request -> request:tg:reranker:{workspace}:{id}).
DEFINITION_WITH_RERANKER = {
    "topics": {
        "request": "request:tg:document-rag:ws:id",
        "response": "response:tg:document-rag:ws:id",
        "reranker-request": "request:tg:reranker:ws:id",
        "reranker-response": "response:tg:reranker:ws:id",
    }
}

# Pre-companion blueprint: no reranker topics (document-rag before the templates change).
DEFINITION_WITHOUT_RERANKER = {
    "topics": {
        "request": "request:tg:document-rag:ws:id",
        "response": "response:tg:document-rag:ws:id",
    }
}


def test_reranker_client_binds_when_flow_provides_topics():
    flow = _flow()
    _spec().add(flow, _processor(), DEFINITION_WITH_RERANKER)
    # The client consumer is registered against the reranker role.
    assert "reranker-request" in flow.consumer


def test_reranker_client_keyerrors_without_companion_template_topics():
    with pytest.raises(KeyError) as exc:
        _spec().add(_flow(), _processor(), DEFINITION_WITHOUT_RERANKER)
    # Fails fast naming the missing role -> the trustgraph-templates companion
    # change (wire reranker-request/response into the document-rag flow) is required.
    assert "reranker-request" in str(exc.value)
