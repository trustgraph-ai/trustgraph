"""
Tests that _parse_chunk propagates message_id from wire format
to AgentThought, AgentObservation, and AgentAnswer.
"""

import pytest

from trustgraph.api.socket_client import SocketClient
from trustgraph.api.types import AgentThought, AgentObservation, AgentAnswer


@pytest.fixture
def client():
    # We only need _parse_chunk — don't connect
    c = object.__new__(SocketClient)
    return c


class TestParseChunkMessageId:

    def test_thought_message_id(self, client):
        resp = {
            "message_type": "thought",
            "content": "thinking...",
            "end_of_message": False,
            "message_id": "urn:trustgraph:agent:sess/i1/thought",
        }
        chunk = client._parse_chunk(resp)
        assert isinstance(chunk, AgentThought)
        assert chunk.message_id == "urn:trustgraph:agent:sess/i1/thought"

    def test_observation_message_id(self, client):
        resp = {
            "message_type": "observation",
            "content": "result",
            "end_of_message": True,
            "message_id": "urn:trustgraph:agent:sess/i1/observation",
        }
        chunk = client._parse_chunk(resp)
        assert isinstance(chunk, AgentObservation)
        assert chunk.message_id == "urn:trustgraph:agent:sess/i1/observation"

    def test_answer_message_id(self, client):
        resp = {
            "message_type": "answer",
            "content": "the answer",
            "end_of_message": False,
            "end_of_dialog": False,
            "message_id": "urn:trustgraph:agent:sess/final",
        }
        chunk = client._parse_chunk(resp)
        assert isinstance(chunk, AgentAnswer)
        assert chunk.message_id == "urn:trustgraph:agent:sess/final"

    def test_thought_missing_message_id(self, client):
        resp = {
            "message_type": "thought",
            "content": "thinking...",
            "end_of_message": False,
        }
        chunk = client._parse_chunk(resp)
        assert isinstance(chunk, AgentThought)
        assert chunk.message_id == ""

    def test_answer_missing_message_id(self, client):
        resp = {
            "message_type": "answer",
            "content": "answer",
            "end_of_message": True,
            "end_of_dialog": True,
        }
        chunk = client._parse_chunk(resp)
        assert isinstance(chunk, AgentAnswer)
        assert chunk.message_id == ""
