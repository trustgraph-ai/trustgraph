"""
Unit tests for CLI tool management commands.

Tests the business logic of set-tool and show-tools commands
while mocking the Config API, specifically focused on structured-query
tool type support.
"""

import pytest
import json
import sys
from unittest.mock import Mock, patch
from io import StringIO

from trustgraph.cli.set_tool import set_tool, main as set_main, Argument
from trustgraph.cli.show_tools import show_config, main as show_main
from trustgraph.api.types import ConfigKey, ConfigValue


@pytest.fixture
def mock_api():
    """Mock Api instance with config() method."""
    mock_api_instance = Mock()
    mock_config = Mock()
    mock_api_instance.config.return_value = mock_config
    return mock_api_instance, mock_config


@pytest.fixture
def sample_structured_query_tool():
    """Sample structured-query tool configuration."""
    return {
        "name": "query_data",
        "description": "Query structured data using natural language",
        "type": "structured-query", 
        "collection": "sales_data"
    }


class TestSetToolStructuredQuery:
    """Test the set_tool function with structured-query type."""

    @patch('trustgraph.cli.set_tool.Api')
    def test_set_structured_query_tool(self, mock_api_class, mock_api, sample_structured_query_tool, capsys):
        """Test setting a structured-query tool."""
        mock_api_class.return_value, mock_config = mock_api
        mock_config.get.return_value = []  # Empty tool index
        
        set_tool(
            url="http://test.com",
            id="data_query_tool",
            name="query_data",
            description="Query structured data using natural language",
            type="structured-query",
            mcp_tool=None,
            collection="sales_data",
            template=None,
            arguments=[],
            group=None,
            state=None,
            applicable_states=None
        )
        
        captured = capsys.readouterr()
        assert "Tool set." in captured.out
        
        # Verify the tool was stored correctly
        call_args = mock_config.put.call_args[0][0]
        assert len(call_args) == 1
        config_value = call_args[0]
        assert config_value.type == "tool"
        assert config_value.key == "data_query_tool"
        
        stored_tool = json.loads(config_value.value)
        assert stored_tool["name"] == "query_data"
        assert stored_tool["type"] == "structured-query"
        assert stored_tool["collection"] == "sales_data"
        assert stored_tool["description"] == "Query structured data using natural language"

    @patch('trustgraph.cli.set_tool.Api') 
    def test_set_structured_query_tool_without_collection(self, mock_api_class, mock_api, capsys):
        """Test setting structured-query tool without collection (should work)."""
        mock_api_class.return_value, mock_config = mock_api
        mock_config.get.return_value = []
        
        set_tool(
            url="http://test.com",
            id="generic_query_tool",
            name="query_generic",
            description="Query any structured data",
            type="structured-query",
            mcp_tool=None,
            collection=None,  # No collection specified
            template=None,
            arguments=[],
            group=None,
            state=None,
            applicable_states=None
        )
        
        captured = capsys.readouterr()
        assert "Tool set." in captured.out
        
        call_args = mock_config.put.call_args[0][0]
        stored_tool = json.loads(call_args[0].value)
        assert stored_tool["type"] == "structured-query"
        assert "collection" not in stored_tool  # Should not be included if None

    def test_set_main_structured_query_with_collection(self):
        """Test set main() with structured-query tool type and collection."""
        test_args = [
            'tg-set-tool',
            '--id', 'sales_query',
            '--name', 'query_sales',
            '--type', 'structured-query',
            '--description', 'Query sales data using natural language',
            '--collection', 'sales_data',
            '--api-url', 'http://custom.com'
        ]
        
        with patch('sys.argv', test_args), \
             patch('trustgraph.cli.set_tool.set_tool') as mock_set:
            
            set_main()
            
            mock_set.assert_called_once_with(
                url='http://custom.com',
                id='sales_query',
                name='query_sales',
                description='Query sales data using natural language',
                type='structured-query',
                mcp_tool=None,
                collection='sales_data',
                template=None,
                arguments=[],
                group=None,
                state=None,
                applicable_states=None,
                token=None
            )

    def test_set_main_structured_query_no_arguments_needed(self):
        """Test that structured-query tools don't require --argument specification."""
        test_args = [
            'tg-set-tool',
            '--id', 'data_query',
            '--name', 'query_data',
            '--type', 'structured-query',
            '--description', 'Query structured data',
            '--collection', 'test_data'
            # Note: No --argument specified, which is correct for structured-query
        ]
        
        with patch('sys.argv', test_args), \
             patch('trustgraph.cli.set_tool.set_tool') as mock_set:
            
            set_main()
            
            # Should succeed without requiring arguments
            args = mock_set.call_args[1]
            assert args['arguments'] == []  # Empty arguments list
            assert args['type'] == 'structured-query'

    def test_valid_types_includes_structured_query(self):
        """Test that 'structured-query' is included in valid tool types."""
        test_args = [
            'tg-set-tool',
            '--id', 'test_tool',
            '--name', 'test_tool',
            '--type', 'structured-query',
            '--description', 'Test tool'
        ]
        
        with patch('sys.argv', test_args), \
             patch('trustgraph.cli.set_tool.set_tool') as mock_set:
            
            # Should not raise an exception about invalid type
            set_main()
            mock_set.assert_called_once()

    def test_invalid_type_rejection(self):
        """Test that invalid tool types are rejected."""
        test_args = [
            'tg-set-tool', 
            '--id', 'test_tool',
            '--name', 'test_tool',
            '--type', 'invalid-type',
            '--description', 'Test tool'
        ]
        
        with patch('sys.argv', test_args), \
             patch('builtins.print') as mock_print:
            
            try:
                set_main()
            except SystemExit:
                pass  # Expected due to argument parsing error
            
            # Should print an exception about invalid type
            printed_output = ' '.join([str(call) for call in mock_print.call_args_list])
            assert 'Exception:' in printed_output or 'invalid choice:' in printed_output.lower()


class TestShowToolsStructuredQuery:
    """Test the show_tools function with structured-query tools."""

    @patch('trustgraph.cli.show_tools.Api')
    def test_show_structured_query_tool_with_collection(self, mock_api_class, mock_api, sample_structured_query_tool, capsys):
        """Test displaying a structured-query tool with collection."""
        mock_api_class.return_value, mock_config = mock_api
        
        config_value = ConfigValue(
            type="tool",
            key="data_query_tool",
            value=json.dumps(sample_structured_query_tool)
        )
        mock_config.get_values.return_value = [config_value]
        
        show_config("http://test.com")
        
        captured = capsys.readouterr()
        output = captured.out
        
        # Check that tool information is displayed
        assert "data_query_tool" in output
        assert "query_data" in output
        assert "structured-query" in output
        assert "sales_data" in output  # Collection should be shown
        assert "Query structured data using natural language" in output

    @patch('trustgraph.cli.show_tools.Api')
    def test_show_structured_query_tool_without_collection(self, mock_api_class, mock_api, capsys):
        """Test displaying structured-query tool without collection."""
        mock_api_class.return_value, mock_config = mock_api
        
        tool_config = {
            "name": "generic_query",
            "description": "Generic structured query tool",
            "type": "structured-query"
            # No collection specified
        }
        
        config_value = ConfigValue(
            type="tool",
            key="generic_tool",
            value=json.dumps(tool_config)
        )
        mock_config.get_values.return_value = [config_value]
        
        show_config("http://test.com")
        
        captured = capsys.readouterr()
        output = captured.out
        
        # Should display the tool without showing collection
        assert "generic_tool" in output
        assert "structured-query" in output
        assert "Generic structured query tool" in output

    @patch('trustgraph.cli.show_tools.Api')
    def test_show_mixed_tool_types(self, mock_api_class, mock_api, capsys):
        """Test displaying multiple tool types including structured-query."""
        mock_api_class.return_value, mock_config = mock_api
        
        tools = [
            {
                "name": "ask_knowledge",
                "description": "Query knowledge base",
                "type": "knowledge-query",
                "collection": "docs"
            },
            {
                "name": "query_data", 
                "description": "Query structured data",
                "type": "structured-query",
                "collection": "sales"
            },
            {
                "name": "complete_text",
                "description": "Generate text",
                "type": "text-completion"
            }
        ]
        
        config_values = [
            ConfigValue(type="tool", key=f"tool_{i}", value=json.dumps(tool))
            for i, tool in enumerate(tools)
        ]
        mock_config.get_values.return_value = config_values
        
        show_config("http://test.com")
        
        captured = capsys.readouterr()
        output = captured.out
        
        # All tool types should be displayed
        assert "knowledge-query" in output
        assert "structured-query" in output  
        assert "text-completion" in output
        
        # Collections should be shown for appropriate tools
        assert "docs" in output  # knowledge-query collection
        assert "sales" in output  # structured-query collection

    def test_show_main_parses_args_correctly(self):
        """Test that show main() parses arguments correctly."""
        test_args = [
            'tg-show-tools',
            '--api-url', 'http://custom.com'
        ]
        
        with patch('sys.argv', test_args), \
             patch('trustgraph.cli.show_tools.show_config') as mock_show:
            
            show_main()
            
            mock_show.assert_called_once_with(url='http://custom.com', token=None)


class TestStructuredQueryToolValidation:
    """Test validation specific to structured-query tools."""

    def test_structured_query_requires_name_and_description(self):
        """Test that structured-query tools require name and description."""
        test_args = [
            'tg-set-tool',
            '--id', 'test_tool',
            '--type', 'structured-query'
            # Missing --name and --description
        ]
        
        with patch('sys.argv', test_args), \
             patch('builtins.print') as mock_print:
            
            try:
                set_main()
            except SystemExit:
                pass  # Expected due to validation error
            
            # Should print validation error
            printed_calls = [str(call) for call in mock_print.call_args_list]
            error_output = ' '.join(printed_calls)
            assert 'Exception:' in error_output

    def test_structured_query_accepts_optional_collection(self):
        """Test that structured-query tools can have optional collection."""
        # Test with collection
        with patch('trustgraph.cli.set_tool.set_tool') as mock_set:
            test_args = [
                'tg-set-tool',
                '--id', 'test1',
                '--name', 'test_tool',
                '--type', 'structured-query',
                '--description', 'Test tool',
                '--collection', 'test_data'
            ]
            
            with patch('sys.argv', test_args):
                set_main()
            
            args = mock_set.call_args[1]
            assert args['collection'] == 'test_data'
        
        # Test without collection
        with patch('trustgraph.cli.set_tool.set_tool') as mock_set:
            test_args = [
                'tg-set-tool',
                '--id', 'test2',
                '--name', 'test_tool2',
                '--type', 'structured-query',
                '--description', 'Test tool 2'
                # No --collection specified
            ]
            
            with patch('sys.argv', test_args):
                set_main()
            
            args = mock_set.call_args[1]
            assert args['collection'] is None


class TestErrorHandling:
    """Test error handling for tool commands."""

    @patch('trustgraph.cli.set_tool.Api')
    def test_set_tool_handles_api_exception(self, mock_api_class, capsys):
        """Test that set-tool command handles API exceptions."""
        mock_api_class.side_effect = Exception("API connection failed")
        
        test_args = [
            'tg-set-tool',
            '--id', 'test_tool',
            '--name', 'test_tool',
            '--type', 'structured-query',
            '--description', 'Test tool'
        ]
        
        with patch('sys.argv', test_args):
            try:
                set_main()
            except SystemExit:
                pass
        
        captured = capsys.readouterr()
        assert "Exception: API connection failed" in captured.out

    @patch('trustgraph.cli.show_tools.Api')
    def test_show_tools_handles_api_exception(self, mock_api_class, capsys):
        """Test that show-tools command handles API exceptions."""
        mock_api_class.side_effect = Exception("API connection failed")
        
        test_args = ['tg-show-tools']
        
        with patch('sys.argv', test_args):
            try:
                show_main()
            except SystemExit:
                pass
        
        captured = capsys.readouterr()
        assert "Exception: API connection failed" in captured.out