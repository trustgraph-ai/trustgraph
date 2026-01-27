"""
Tests for Gateway Dispatch Serialization
"""

import pytest
from unittest.mock import MagicMock

from trustgraph.gateway.dispatch.serialize import to_value, to_subgraph, serialize_value
from trustgraph.schema import Term, Triple, IRI, LITERAL


class TestDispatchSerialize:
    """Test cases for dispatch serialization functions"""

    def test_to_value_with_uri(self):
        """Test to_value function with URI"""
        input_data = {"t": "i", "i": "http://example.com/resource"}

        result = to_value(input_data)

        assert isinstance(result, Term)
        assert result.iri == "http://example.com/resource"
        assert result.type == IRI

    def test_to_value_with_literal(self):
        """Test to_value function with literal value"""
        input_data = {"t": "l", "v": "literal string"}

        result = to_value(input_data)

        assert isinstance(result, Term)
        assert result.value == "literal string"
        assert result.type == LITERAL

    def test_to_subgraph_with_multiple_triples(self):
        """Test to_subgraph function with multiple triples"""
        input_data = [
            {
                "s": {"t": "i", "i": "subject1"},
                "p": {"t": "i", "i": "predicate1"},
                "o": {"t": "l", "v": "object1"}
            },
            {
                "s": {"t": "l", "v": "subject2"},
                "p": {"t": "i", "i": "predicate2"},
                "o": {"t": "i", "i": "object2"}
            }
        ]

        result = to_subgraph(input_data)

        assert len(result) == 2
        assert all(isinstance(triple, Triple) for triple in result)

        # Check first triple
        assert result[0].s.iri == "subject1"
        assert result[0].s.type == IRI
        assert result[0].p.iri == "predicate1"
        assert result[0].p.type == IRI
        assert result[0].o.value == "object1"
        assert result[0].o.type == LITERAL

        # Check second triple
        assert result[1].s.value == "subject2"
        assert result[1].s.type == LITERAL

    def test_to_subgraph_with_empty_list(self):
        """Test to_subgraph function with empty input"""
        input_data = []
        
        result = to_subgraph(input_data)
        
        assert result == []

    def test_serialize_value_with_uri(self):
        """Test serialize_value function with URI value"""
        term = Term(type=IRI, iri="http://example.com/test")

        result = serialize_value(term)

        assert result == {"t": "i", "i": "http://example.com/test"}

    def test_serialize_value_with_literal(self):
        """Test serialize_value function with literal value"""
        term = Term(type=LITERAL, value="test literal")

        result = serialize_value(term)

        assert result == {"t": "l", "v": "test literal"}