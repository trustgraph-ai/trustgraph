"""
Unit tests for Generator class.
"""

import pytest
import json
from trustgraph_configurator.generator import Generator


@pytest.mark.unit
class TestGenerator:
    """Tests for the Generator class."""

    def test_simple_jsonnet(self):
        """Test processing simple jsonnet."""
        def mock_fetch(base, rel):
            return "", ""

        generator = Generator(mock_fetch)
        result = generator.process('{ foo: "bar" }')

        assert isinstance(result, dict)
        assert result["foo"] == "bar"

    def test_jsonnet_with_variables(self):
        """Test processing jsonnet with variables."""
        def mock_fetch(base, rel):
            return "", ""

        generator = Generator(mock_fetch)
        jsonnet_code = '''
        local name = "test";
        {
            name: name,
            value: 42
        }
        '''
        result = generator.process(jsonnet_code)

        assert result["name"] == "test"
        assert result["value"] == 42

    def test_jsonnet_with_array(self):
        """Test processing jsonnet that returns array."""
        def mock_fetch(base, rel):
            return "", ""

        generator = Generator(mock_fetch)
        jsonnet_code = '[1, 2, 3, { foo: "bar" }]'
        result = generator.process(jsonnet_code)

        assert isinstance(result, list)
        assert len(result) == 4
        assert result[0] == 1
        assert result[3]["foo"] == "bar"

    def test_invalid_jsonnet(self):
        """Test that invalid jsonnet raises exception."""
        def mock_fetch(base, rel):
            return "", ""

        generator = Generator(mock_fetch)

        with pytest.raises(Exception):
            generator.process('{ invalid jsonnet')

    def test_jsonnet_with_functions(self):
        """Test processing jsonnet with functions."""
        def mock_fetch(base, rel):
            return "", ""

        generator = Generator(mock_fetch)
        jsonnet_code = '''
        local double(x) = x * 2;
        {
            value: double(21)
        }
        '''
        result = generator.process(jsonnet_code)

        assert result["value"] == 42

    def test_fetch_callback_is_used(self):
        """Test that fetch callback is called for imports."""
        fetch_called = []

        def mock_fetch(base, rel):
            fetch_called.append((base, rel))
            # Return simple jsonnet that defines a variable (as bytes)
            return "config", b'{ imported: true }'

        generator = Generator(mock_fetch)
        jsonnet_code = '''
        local config = import "config.jsonnet";
        config
        '''

        result = generator.process(jsonnet_code)

        assert len(fetch_called) > 0
        assert result["imported"] is True
