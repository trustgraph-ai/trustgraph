"""
Tests that the socket clients propagate the sources field from the
wire format to RAGChunk, and that graph_rag results carry it.
"""

import pytest

from trustgraph.api.socket_client import SocketClient
from trustgraph.api.async_socket_client import AsyncSocketClient
from trustgraph.api.types import RAGChunk

WIRE_SOURCES = [
    {"uri": "urn:document:alpha", "title": "Quantum Mechanics Primer"},
    {"uri": "urn:document:beta", "title": ""},
]


@pytest.fixture
def client():
    # We only need _parse_chunk — don't connect
    c = object.__new__(SocketClient)
    return c


@pytest.fixture
def async_client():
    c = object.__new__(AsyncSocketClient)
    return c


class TestParseChunkSources:

    def test_final_chunk_carries_sources(self, client):
        resp = {
            "message_type": "chunk",
            "response": "",
            "end_of_stream": False,
            "end_of_session": True,
            "sources": WIRE_SOURCES,
        }
        chunk = client._parse_chunk(resp)
        assert isinstance(chunk, RAGChunk)
        assert chunk.sources == WIRE_SOURCES

    def test_intermediate_chunk_has_empty_sources(self, client):
        resp = {
            "message_type": "chunk",
            "response": "partial text",
            "end_of_stream": False,
        }
        chunk = client._parse_chunk(resp)
        assert isinstance(chunk, RAGChunk)
        assert chunk.sources == []

    def test_async_final_chunk_carries_sources(self, async_client):
        resp = {
            "message_type": "chunk",
            "response": "",
            "end_of_session": True,
            "sources": WIRE_SOURCES,
        }
        chunk = async_client._parse_chunk(resp)
        assert isinstance(chunk, RAGChunk)
        assert chunk.sources == WIRE_SOURCES

    def test_async_intermediate_chunk_has_empty_sources(self, async_client):
        resp = {
            "message_type": "chunk",
            "response": "partial text",
        }
        chunk = async_client._parse_chunk(resp)
        assert isinstance(chunk, RAGChunk)
        assert chunk.sources == []


class TestRestGraphRagSources:

    def test_graph_rag_result_carries_sources(self):
        from trustgraph.api.flow import FlowInstance

        instance = object.__new__(FlowInstance)
        instance.request = lambda path, request: {
            "response": "The answer.",
            "sources": WIRE_SOURCES,
        }

        result = instance.graph_rag(query="What is quantum computing?")
        assert result.text == "The answer."
        assert result.sources == WIRE_SOURCES

    def test_graph_rag_result_defaults_to_empty_sources(self):
        from trustgraph.api.flow import FlowInstance

        instance = object.__new__(FlowInstance)
        instance.request = lambda path, request: {
            "response": "The answer.",
        }

        result = instance.graph_rag(query="What is quantum computing?")
        assert result.sources == []
