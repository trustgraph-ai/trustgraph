"""
Unit tests for CLI configuration commands.

Tests the business logic of list/get/put/delete config item commands
while mocking the Config API.
"""

import pytest
import json
import sys
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

from trustgraph.cli.list_config_items import list_config_items, main as list_main
from trustgraph.cli.get_config_item import get_config_item, main as get_main
from trustgraph.cli.put_config_item import put_config_item, main as put_main
from trustgraph.cli.delete_config_item import delete_config_item, main as delete_main
from trustgraph.api.types import ConfigKey, ConfigValue


@pytest.fixture
def mock_api():
    """Mock Api instance with config() method."""
    mock_api_instance = Mock()
    mock_config = Mock()
    mock_api_instance.config.return_value = mock_config
    return mock_api_instance, mock_config


@pytest.fixture
def sample_config_keys():
    """Sample configuration keys."""
    return ["template-1", "template-2", "system-prompt"]


@pytest.fixture
def sample_config_value():
    """Sample configuration value."""
    return ConfigValue(
        type="prompt",
        key="template-1", 
        value="You are a helpful assistant. Please respond to: {query}"
    )


class TestListConfigItems:
    """Test the list_config_items function."""

    @patch('trustgraph.cli.list_config_items.Api')
    def test_list_config_items_text_format(self, mock_api_class, mock_api, sample_config_keys, capsys):
        """Test listing config items in text format."""
        mock_api_class.return_value, mock_config = mock_api
        mock_config.list.return_value = sample_config_keys
        
        list_config_items("http://test.com", "prompt", "text")
        
        captured = capsys.readouterr()
        output_lines = captured.out.strip().split('\n')
        
        assert len(output_lines) == 3
        assert "template-1" in output_lines
        assert "template-2" in output_lines
        assert "system-prompt" in output_lines
        
        mock_config.list.assert_called_once_with("prompt")

    @patch('trustgraph.cli.list_config_items.Api')
    def test_list_config_items_json_format(self, mock_api_class, mock_api, sample_config_keys, capsys):
        """Test listing config items in JSON format."""
        mock_api_class.return_value, mock_config = mock_api
        mock_config.list.return_value = sample_config_keys
        
        list_config_items("http://test.com", "prompt", "json")
        
        captured = capsys.readouterr()
        output = json.loads(captured.out.strip())
        
        assert output == sample_config_keys
        mock_config.list.assert_called_once_with("prompt")

    @patch('trustgraph.cli.list_config_items.Api')
    def test_list_config_items_empty_list(self, mock_api_class, mock_api, capsys):
        """Test listing when no config items exist."""
        mock_api_class.return_value, mock_config = mock_api
        mock_config.list.return_value = []
        
        list_config_items("http://test.com", "nonexistent", "text")
        
        captured = capsys.readouterr()
        assert captured.out.strip() == ""
        
        mock_config.list.assert_called_once_with("nonexistent")

    def test_list_main_parses_args_correctly(self):
        """Test that list main() parses arguments correctly."""
        test_args = [
            'tg-list-config-items',
            '--type', 'prompt',
            '--format', 'json',
            '--api-url', 'http://custom.com'
        ]
        
        with patch('sys.argv', test_args), \
             patch('trustgraph.cli.list_config_items.list_config_items') as mock_list:
            
            list_main()
            
            mock_list.assert_called_once_with(
                url='http://custom.com',
                config_type='prompt',
                format_type='json',
                token=None
            )

    def test_list_main_uses_defaults(self):
        """Test that list main() uses default values."""
        test_args = [
            'tg-list-config-items',
            '--type', 'prompt'
        ]
        
        with patch('sys.argv', test_args), \
             patch('trustgraph.cli.list_config_items.list_config_items') as mock_list:
            
            list_main()
            
            mock_list.assert_called_once_with(
                url='http://localhost:8088/',
                config_type='prompt',
                format_type='text',
                token=None
            )


class TestGetConfigItem:
    """Test the get_config_item function."""

    @patch('trustgraph.cli.get_config_item.Api')
    def test_get_config_item_text_format(self, mock_api_class, mock_api, sample_config_value, capsys):
        """Test getting config item in text format."""
        mock_api_class.return_value, mock_config = mock_api
        mock_config.get.return_value = [sample_config_value]
        
        get_config_item("http://test.com", "prompt", "template-1", "text")
        
        captured = capsys.readouterr()
        assert captured.out.strip() == sample_config_value.value
        
        # Verify ConfigKey was constructed correctly
        call_args = mock_config.get.call_args[0][0]
        assert len(call_args) == 1
        config_key = call_args[0]
        assert config_key.type == "prompt"
        assert config_key.key == "template-1"

    @patch('trustgraph.cli.get_config_item.Api')
    def test_get_config_item_json_format(self, mock_api_class, mock_api, sample_config_value, capsys):
        """Test getting config item in JSON format."""
        mock_api_class.return_value, mock_config = mock_api
        mock_config.get.return_value = [sample_config_value]
        
        get_config_item("http://test.com", "prompt", "template-1", "json")
        
        captured = capsys.readouterr()
        output = json.loads(captured.out.strip())
        
        assert output == sample_config_value.value
        mock_config.get.assert_called_once()

    @patch('trustgraph.cli.get_config_item.Api')
    def test_get_config_item_not_found(self, mock_api_class, mock_api):
        """Test getting non-existent config item raises exception."""
        mock_api_class.return_value, mock_config = mock_api
        mock_config.get.return_value = []
        
        with pytest.raises(Exception, match="Configuration item not found"):
            get_config_item("http://test.com", "prompt", "nonexistent", "text")

    def test_get_main_parses_args_correctly(self):
        """Test that get main() parses arguments correctly."""
        test_args = [
            'tg-get-config-item',
            '--type', 'prompt',
            '--key', 'template-1',
            '--format', 'json',
            '--api-url', 'http://custom.com'
        ]
        
        with patch('sys.argv', test_args), \
             patch('trustgraph.cli.get_config_item.get_config_item') as mock_get:
            
            get_main()
            
            mock_get.assert_called_once_with(
                url='http://custom.com',
                config_type='prompt',
                key='template-1',
                format_type='json',
                token=None
            )


class TestPutConfigItem:
    """Test the put_config_item function."""

    @patch('trustgraph.cli.put_config_item.Api')
    def test_put_config_item_with_value(self, mock_api_class, mock_api, capsys):
        """Test putting config item with command line value."""
        mock_api_class.return_value, mock_config = mock_api
        
        put_config_item("http://test.com", "prompt", "new-template", "Custom prompt: {input}")
        
        captured = capsys.readouterr()
        assert "Configuration item set: prompt/new-template" in captured.out
        
        # Verify ConfigValue was constructed correctly
        call_args = mock_config.put.call_args[0][0]
        assert len(call_args) == 1
        config_value = call_args[0]
        assert config_value.type == "prompt"
        assert config_value.key == "new-template"
        assert config_value.value == "Custom prompt: {input}"

    @patch('trustgraph.cli.put_config_item.Api')
    def test_put_config_item_multiline_value(self, mock_api_class, mock_api):
        """Test putting config item with multiline value."""
        mock_api_class.return_value, mock_config = mock_api
        
        multiline_value = "Line 1\nLine 2\nLine 3"
        put_config_item("http://test.com", "prompt", "multiline-template", multiline_value)
        
        call_args = mock_config.put.call_args[0][0]
        config_value = call_args[0]
        assert config_value.value == multiline_value

    def test_put_main_with_value_arg(self):
        """Test put main() with --value argument."""
        test_args = [
            'tg-put-config-item',
            '--type', 'prompt',
            '--key', 'new-template',
            '--value', 'Custom prompt: {input}',
            '--api-url', 'http://custom.com'
        ]
        
        with patch('sys.argv', test_args), \
             patch('trustgraph.cli.put_config_item.put_config_item') as mock_put:
            
            put_main()
            
            mock_put.assert_called_once_with(
                url='http://custom.com',
                config_type='prompt',
                key='new-template',
                value='Custom prompt: {input}',
                token=None
            )

    def test_put_main_with_stdin_arg(self):
        """Test put main() with --stdin argument."""
        test_args = [
            'tg-put-config-item',
            '--type', 'prompt',
            '--key', 'stdin-template',
            '--stdin'
        ]
        
        stdin_content = "Content from stdin\nMultiple lines"
        
        with patch('sys.argv', test_args), \
             patch('sys.stdin', StringIO(stdin_content)), \
             patch('trustgraph.cli.put_config_item.put_config_item') as mock_put:
            
            put_main()
            
            mock_put.assert_called_once_with(
                url='http://localhost:8088/',
                config_type='prompt',
                key='stdin-template',
                value=stdin_content,
                token=None
            )

    def test_put_main_mutually_exclusive_args(self):
        """Test that --value and --stdin are mutually exclusive."""
        test_args = [
            'tg-put-config-item',
            '--type', 'prompt',
            '--key', 'template',
            '--value', 'test',
            '--stdin'
        ]
        
        with patch('sys.argv', test_args):
            with pytest.raises(SystemExit):
                put_main()


class TestDeleteConfigItem:
    """Test the delete_config_item function."""

    @patch('trustgraph.cli.delete_config_item.Api')
    def test_delete_config_item(self, mock_api_class, mock_api, capsys):
        """Test deleting config item."""
        mock_api_class.return_value, mock_config = mock_api
        
        delete_config_item("http://test.com", "prompt", "old-template")
        
        captured = capsys.readouterr()
        assert "Configuration item deleted: prompt/old-template" in captured.out
        
        # Verify ConfigKey was constructed correctly
        call_args = mock_config.delete.call_args[0][0]
        assert len(call_args) == 1
        config_key = call_args[0]
        assert config_key.type == "prompt"
        assert config_key.key == "old-template"

    def test_delete_main_parses_args_correctly(self):
        """Test that delete main() parses arguments correctly."""
        test_args = [
            'tg-delete-config-item',
            '--type', 'prompt',
            '--key', 'old-template',
            '--api-url', 'http://custom.com'
        ]
        
        with patch('sys.argv', test_args), \
             patch('trustgraph.cli.delete_config_item.delete_config_item') as mock_delete:
            
            delete_main()
            
            mock_delete.assert_called_once_with(
                url='http://custom.com',
                config_type='prompt',
                key='old-template',
                token=None
            )


class TestErrorHandling:
    """Test error handling scenarios."""

    @patch('trustgraph.cli.list_config_items.Api')
    def test_list_handles_api_exception(self, mock_api_class, capsys):
        """Test that list command handles API exceptions."""
        mock_api_class.side_effect = Exception("API connection failed")
        
        list_main_with_args(['--type', 'prompt'])
        
        captured = capsys.readouterr()
        assert "Exception: API connection failed" in captured.out

    @patch('trustgraph.cli.get_config_item.Api')
    def test_get_handles_api_exception(self, mock_api_class, capsys):
        """Test that get command handles API exceptions."""
        mock_api_class.side_effect = Exception("API connection failed")
        
        get_main_with_args(['--type', 'prompt', '--key', 'test'])
        
        captured = capsys.readouterr()
        assert "Exception: API connection failed" in captured.out

    @patch('trustgraph.cli.put_config_item.Api')
    def test_put_handles_api_exception(self, mock_api_class, capsys):
        """Test that put command handles API exceptions."""
        mock_api_class.side_effect = Exception("API connection failed")
        
        put_main_with_args(['--type', 'prompt', '--key', 'test', '--value', 'test'])
        
        captured = capsys.readouterr()
        assert "Exception: API connection failed" in captured.out

    @patch('trustgraph.cli.delete_config_item.Api')
    def test_delete_handles_api_exception(self, mock_api_class, capsys):
        """Test that delete command handles API exceptions."""
        mock_api_class.side_effect = Exception("API connection failed")
        
        delete_main_with_args(['--type', 'prompt', '--key', 'test'])
        
        captured = capsys.readouterr()
        assert "Exception: API connection failed" in captured.out


class TestDataValidation:
    """Test data validation and edge cases."""

    @patch('trustgraph.cli.get_config_item.Api')
    def test_get_empty_string_value(self, mock_api_class, mock_api, capsys):
        """Test getting config item with empty string value."""
        mock_api_class.return_value, mock_config = mock_api
        empty_value = ConfigValue(type="prompt", key="empty", value="")
        mock_config.get.return_value = [empty_value]
        
        get_config_item("http://test.com", "prompt", "empty", "text")
        
        captured = capsys.readouterr()
        assert captured.out == "\n"  # Just a newline from print()

    @patch('trustgraph.cli.put_config_item.Api')
    def test_put_empty_string_value(self, mock_api_class, mock_api):
        """Test putting config item with empty string value."""
        mock_api_class.return_value, mock_config = mock_api
        
        put_config_item("http://test.com", "prompt", "empty", "")
        
        call_args = mock_config.put.call_args[0][0]
        config_value = call_args[0]
        assert config_value.value == ""

    @patch('trustgraph.cli.get_config_item.Api')
    def test_get_special_characters_value(self, mock_api_class, mock_api, capsys):
        """Test getting config item with special characters."""
        mock_api_class.return_value, mock_config = mock_api
        special_value = ConfigValue(
            type="prompt", 
            key="special", 
            value="Special chars: äöü 中文 🌟 \"quotes\" 'apostrophes'"
        )
        mock_config.get.return_value = [special_value]
        
        get_config_item("http://test.com", "prompt", "special", "text")
        
        captured = capsys.readouterr()
        assert "äöü 中文 🌟" in captured.out
        assert '"quotes"' in captured.out


# Helper functions for testing main() with custom args
def list_main_with_args(args):
    """Helper to test list_main with custom arguments."""
    test_args = ['tg-list-config-items'] + args
    with patch('sys.argv', test_args):
        try:
            list_main()
        except SystemExit:
            pass

def get_main_with_args(args):
    """Helper to test get_main with custom arguments."""
    test_args = ['tg-get-config-item'] + args
    with patch('sys.argv', test_args):
        try:
            get_main()
        except SystemExit:
            pass

def put_main_with_args(args):
    """Helper to test put_main with custom arguments."""
    test_args = ['tg-put-config-item'] + args
    with patch('sys.argv', test_args):
        try:
            put_main()
        except SystemExit:
            pass

def delete_main_with_args(args):
    """Helper to test delete_main with custom arguments."""
    test_args = ['tg-delete-config-item'] + args
    with patch('sys.argv', test_args):
        try:
            delete_main()
        except SystemExit:
            pass