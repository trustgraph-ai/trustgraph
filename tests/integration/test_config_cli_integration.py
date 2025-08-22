"""
Integration tests for CLI configuration commands.

Tests the full command execution flow with mocked API responses
to verify end-to-end functionality.
"""

import pytest
import json
import sys
from unittest.mock import patch, Mock, MagicMock
from io import StringIO

# Import the CLI modules directly for integration testing
from trustgraph.cli.list_config_items import main as list_main
from trustgraph.cli.get_config_item import main as get_main
from trustgraph.cli.put_config_item import main as put_main
from trustgraph.cli.delete_config_item import main as delete_main


class TestConfigCLIIntegration:
    """Test CLI commands with mocked API responses."""

    @patch('trustgraph.cli.list_config_items.Api')
    def test_list_config_items_integration(self, mock_api_class, capsys):
        """Test tg-list-config-items with mocked API response."""
        # Mock the API and config objects
        mock_api = MagicMock()
        mock_config = MagicMock()
        mock_api.config.return_value = mock_config
        mock_api_class.return_value = mock_api
        
        # Mock the list response
        mock_config.list.return_value = ["template-1", "template-2", "system-prompt"]
        
        # Run the command with test args
        test_args = [
            'tg-list-config-items',
            '--type', 'prompt',
            '--format', 'json'
        ]
        
        with patch('sys.argv', test_args):
            list_main()
        
        captured = capsys.readouterr()
        output = json.loads(captured.out.strip())
        assert output == ["template-1", "template-2", "system-prompt"]

    @patch('trustgraph.cli.get_config_item.Api')
    def test_get_config_item_integration(self, mock_api_class, capsys):
        """Test tg-get-config-item with mocked API response."""
        from trustgraph.api.types import ConfigValue
        
        # Mock the API and config objects
        mock_api = MagicMock()
        mock_config = MagicMock()
        mock_api.config.return_value = mock_config
        mock_api_class.return_value = mock_api
        
        # Mock the get response
        mock_config_value = ConfigValue(
            type="prompt",
            key="template-1",
            value="You are a helpful assistant. Please respond to: {query}"
        )
        mock_config.get.return_value = [mock_config_value]
        
        # Run the command with test args
        test_args = [
            'tg-get-config-item',
            '--type', 'prompt',
            '--key', 'template-1',
            '--format', 'text'
        ]
        
        with patch('sys.argv', test_args):
            get_main()
        
        captured = capsys.readouterr()
        assert captured.out.strip() == "You are a helpful assistant. Please respond to: {query}"

    @patch('trustgraph.cli.put_config_item.Api')
    def test_put_config_item_integration(self, mock_api_class, capsys):
        """Test tg-put-config-item with mocked API response."""
        # Mock the API and config objects
        mock_api = MagicMock()
        mock_config = MagicMock()
        mock_api.config.return_value = mock_config
        mock_api_class.return_value = mock_api
        
        # Run the command with test args
        test_args = [
            'tg-put-config-item',
            '--type', 'prompt',
            '--key', 'new-template',
            '--value', 'Custom prompt: {input}'
        ]
        
        with patch('sys.argv', test_args):
            put_main()
        
        captured = capsys.readouterr()
        assert "Configuration item set: prompt/new-template" in captured.out

    @patch('trustgraph.cli.delete_config_item.Api')
    def test_delete_config_item_integration(self, mock_api_class, capsys):
        """Test tg-delete-config-item with mocked API response."""
        # Mock the API and config objects
        mock_api = MagicMock()
        mock_config = MagicMock()
        mock_api.config.return_value = mock_config
        mock_api_class.return_value = mock_api
        
        # Run the command with test args
        test_args = [
            'tg-delete-config-item',
            '--type', 'prompt',
            '--key', 'old-template'
        ]
        
        with patch('sys.argv', test_args):
            delete_main()
        
        captured = capsys.readouterr()
        assert "Configuration item deleted: prompt/old-template" in captured.out

    @patch('trustgraph.cli.put_config_item.Api')
    def test_put_config_item_stdin_integration(self, mock_api_class, capsys):
        """Test tg-put-config-item with stdin input."""
        # Mock the API and config objects
        mock_api = MagicMock()
        mock_config = MagicMock()
        mock_api.config.return_value = mock_config
        mock_api_class.return_value = mock_api
        
        stdin_content = "Multi-line template:\nLine 1\nLine 2"
        
        # Run the command with test args and mocked stdin
        test_args = [
            'tg-put-config-item',
            '--type', 'prompt',
            '--key', 'multiline-template',
            '--stdin'
        ]
        
        with patch('sys.argv', test_args), \
             patch('sys.stdin', StringIO(stdin_content)):
            put_main()
        
        captured = capsys.readouterr()
        assert "Configuration item set: prompt/multiline-template" in captured.out

    @patch('trustgraph.cli.list_config_items.Api')
    def test_api_error_handling_integration(self, mock_api_class, capsys):
        """Test CLI commands handle API errors gracefully."""
        # Mock API to raise an exception
        mock_api_class.side_effect = Exception("Configuration type not found")
        
        test_args = [
            'tg-list-config-items',
            '--type', 'nonexistent'
        ]
        
        with patch('sys.argv', test_args):
            list_main()
        
        captured = capsys.readouterr()
        assert "Exception:" in captured.out
        assert "Configuration type not found" in captured.out

    def test_list_help_message(self):
        """Test that help message is displayed correctly."""
        test_args = ['tg-list-config-items', '--help']
        
        with patch('sys.argv', test_args):
            with pytest.raises(SystemExit) as exc_info:
                list_main()
            # Help command exits with code 0
            assert exc_info.value.code == 0

    def test_missing_required_args(self):
        """Test that missing required arguments are handled."""
        # Test list without --type
        test_args = ['tg-list-config-items']
        
        with patch('sys.argv', test_args):
            with pytest.raises(SystemExit) as exc_info:
                list_main()
            # Missing required args exit with non-zero code
            assert exc_info.value.code != 0

        # Test get without --key
        test_args = ['tg-get-config-item', '--type', 'prompt']
        
        with patch('sys.argv', test_args):
            with pytest.raises(SystemExit) as exc_info:
                get_main()
            assert exc_info.value.code != 0

    def test_mutually_exclusive_put_args(self):
        """Test that --value and --stdin are mutually exclusive."""
        test_args = [
            'tg-put-config-item',
            '--type', 'prompt',
            '--key', 'test',
            '--value', 'test',
            '--stdin'
        ]
        
        with patch('sys.argv', test_args):
            with pytest.raises(SystemExit) as exc_info:
                put_main()
            assert exc_info.value.code != 0


class TestConfigCLIWorkflow:
    """Test complete workflows using multiple commands."""

    @patch('trustgraph.cli.put_config_item.Api')
    @patch('trustgraph.cli.get_config_item.Api')
    def test_put_then_get_workflow(self, mock_get_api, mock_put_api, capsys):
        """Test putting a config item then retrieving it."""
        from trustgraph.api.types import ConfigValue
        
        # Mock put API
        mock_put_config = MagicMock()
        mock_put_api.return_value.config.return_value = mock_put_config
        
        # Mock get API
        mock_get_config = MagicMock()
        mock_get_api.return_value.config.return_value = mock_get_config
        mock_config_value = ConfigValue(
            type="prompt",
            key="workflow-test", 
            value="Workflow test value"
        )
        mock_get_config.get.return_value = [mock_config_value]
        
        # Put config item
        put_args = [
            'tg-put-config-item',
            '--type', 'prompt',
            '--key', 'workflow-test',
            '--value', 'Workflow test value'
        ]
        
        with patch('sys.argv', put_args):
            put_main()
        
        put_output = capsys.readouterr()
        assert "Configuration item set" in put_output.out
        
        # Get config item
        get_args = [
            'tg-get-config-item',
            '--type', 'prompt',
            '--key', 'workflow-test'
        ]
        
        with patch('sys.argv', get_args):
            get_main()
        
        get_output = capsys.readouterr()
        assert get_output.out.strip() == "Workflow test value"

    @patch('trustgraph.cli.list_config_items.Api')
    @patch('trustgraph.cli.put_config_item.Api')  
    @patch('trustgraph.cli.delete_config_item.Api')
    def test_list_put_delete_workflow(self, mock_delete_api, mock_put_api, mock_list_api, capsys):
        """Test list, put, then delete workflow."""
        # Mock list API (empty initially, then with item)
        mock_list_config = MagicMock()
        mock_list_api.return_value.config.return_value = mock_list_config
        mock_list_config.list.side_effect = [[], ["new-item"]]  # Empty first, then has item
        
        # Mock put API
        mock_put_config = MagicMock()
        mock_put_api.return_value.config.return_value = mock_put_config
        
        # Mock delete API
        mock_delete_config = MagicMock()
        mock_delete_api.return_value.config.return_value = mock_delete_config
        
        # List (should be empty)
        list_args1 = [
            'tg-list-config-items',
            '--type', 'prompt',
            '--format', 'json'
        ]
        
        with patch('sys.argv', list_args1):
            list_main()
        
        list_output1 = capsys.readouterr()
        assert json.loads(list_output1.out.strip()) == []
        
        # Put item
        put_args = [
            'tg-put-config-item',
            '--type', 'prompt',
            '--key', 'new-item',
            '--value', 'New item value'
        ]
        
        with patch('sys.argv', put_args):
            put_main()
        
        put_output = capsys.readouterr()
        assert "Configuration item set" in put_output.out
        
        # List (should contain new item)
        list_args2 = [
            'tg-list-config-items',
            '--type', 'prompt',
            '--format', 'json'
        ]
        
        with patch('sys.argv', list_args2):
            list_main()
        
        list_output2 = capsys.readouterr()
        assert json.loads(list_output2.out.strip()) == ["new-item"]
        
        # Delete item
        delete_args = [
            'tg-delete-config-item',
            '--type', 'prompt',
            '--key', 'new-item'
        ]
        
        with patch('sys.argv', delete_args):
            delete_main()
        
        delete_output = capsys.readouterr()
        assert "Configuration item deleted" in delete_output.out