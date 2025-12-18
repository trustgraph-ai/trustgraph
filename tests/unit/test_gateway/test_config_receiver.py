"""
Tests for Gateway Config Receiver
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, Mock, MagicMock
import uuid

from trustgraph.gateway.config.receiver import ConfigReceiver

# Save the real method before patching
_real_config_loader = ConfigReceiver.config_loader

# Patch async methods at module level to prevent coroutine warnings
ConfigReceiver.config_loader = Mock()


class TestConfigReceiver:
    """Test cases for ConfigReceiver class"""

    def test_config_receiver_initialization(self):
        """Test ConfigReceiver initialization"""
        mock_backend = Mock()
        
        config_receiver = ConfigReceiver(mock_backend)
        
        assert config_receiver.backend == mock_backend
        assert config_receiver.flow_handlers == []
        assert config_receiver.flows == {}

    def test_add_handler(self):
        """Test adding flow handlers"""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)
        
        handler1 = Mock()
        handler2 = Mock()
        
        config_receiver.add_handler(handler1)
        config_receiver.add_handler(handler2)
        
        assert len(config_receiver.flow_handlers) == 2
        assert handler1 in config_receiver.flow_handlers
        assert handler2 in config_receiver.flow_handlers

    @pytest.mark.asyncio
    async def test_on_config_with_new_flows(self):
        """Test on_config method with new flows"""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)
        
        # Track calls manually instead of using AsyncMock
        start_flow_calls = []
        
        async def mock_start_flow(*args):
            start_flow_calls.append(args)
        
        config_receiver.start_flow = mock_start_flow
        
        # Create mock message with flows
        mock_msg = Mock()
        mock_msg.value.return_value = Mock(
            version="1.0",
            config={
                "flows": {
                    "flow1": '{"name": "test_flow_1", "steps": []}',
                    "flow2": '{"name": "test_flow_2", "steps": []}'
                }
            }
        )
        
        await config_receiver.on_config(mock_msg, None, None)
        
        # Verify flows were added
        assert "flow1" in config_receiver.flows
        assert "flow2" in config_receiver.flows
        assert config_receiver.flows["flow1"] == {"name": "test_flow_1", "steps": []}
        assert config_receiver.flows["flow2"] == {"name": "test_flow_2", "steps": []}
        
        # Verify start_flow was called for each new flow
        assert len(start_flow_calls) == 2
        assert ("flow1", {"name": "test_flow_1", "steps": []}) in start_flow_calls
        assert ("flow2", {"name": "test_flow_2", "steps": []}) in start_flow_calls

    @pytest.mark.asyncio
    async def test_on_config_with_removed_flows(self):
        """Test on_config method with removed flows"""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)
        
        # Pre-populate with existing flows
        config_receiver.flows = {
            "flow1": {"name": "test_flow_1", "steps": []},
            "flow2": {"name": "test_flow_2", "steps": []}
        }
        
        # Track calls manually instead of using AsyncMock
        stop_flow_calls = []
        
        async def mock_stop_flow(*args):
            stop_flow_calls.append(args)
        
        config_receiver.stop_flow = mock_stop_flow
        
        # Create mock message with only flow1 (flow2 removed)
        mock_msg = Mock()
        mock_msg.value.return_value = Mock(
            version="1.0",
            config={
                "flows": {
                    "flow1": '{"name": "test_flow_1", "steps": []}'
                }
            }
        )
        
        await config_receiver.on_config(mock_msg, None, None)
        
        # Verify flow2 was removed
        assert "flow1" in config_receiver.flows
        assert "flow2" not in config_receiver.flows
        
        # Verify stop_flow was called for removed flow
        assert len(stop_flow_calls) == 1
        assert stop_flow_calls[0] == ("flow2", {"name": "test_flow_2", "steps": []})

    @pytest.mark.asyncio
    async def test_on_config_with_no_flows(self):
        """Test on_config method with no flows in config"""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)
        
        # Mock the start_flow and stop_flow methods with async functions
        async def mock_start_flow(*args):
            pass
        async def mock_stop_flow(*args):
            pass
        config_receiver.start_flow = mock_start_flow
        config_receiver.stop_flow = mock_stop_flow
        
        # Create mock message without flows
        mock_msg = Mock()
        mock_msg.value.return_value = Mock(
            version="1.0",
            config={}
        )
        
        await config_receiver.on_config(mock_msg, None, None)
        
        # Verify no flows were added
        assert config_receiver.flows == {}
        
        # Since no flows were in the config, the flow methods shouldn't be called
        # (We can't easily assert this with simple async functions, but the test
        # passes if no exceptions are thrown)

    @pytest.mark.asyncio
    async def test_on_config_exception_handling(self):
        """Test on_config method handles exceptions gracefully"""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)
        
        # Create mock message that will cause an exception
        mock_msg = Mock()
        mock_msg.value.side_effect = Exception("Test exception")
        
        # This should not raise an exception
        await config_receiver.on_config(mock_msg, None, None)
        
        # Verify flows remain empty
        assert config_receiver.flows == {}

    @pytest.mark.asyncio
    async def test_start_flow_with_handlers(self):
        """Test start_flow method with multiple handlers"""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)
        
        # Add mock handlers
        handler1 = Mock()
        handler1.start_flow = Mock()
        handler2 = Mock()
        handler2.start_flow = Mock()
        
        config_receiver.add_handler(handler1)
        config_receiver.add_handler(handler2)
        
        flow_data = {"name": "test_flow", "steps": []}
        
        await config_receiver.start_flow("flow1", flow_data)
        
        # Verify all handlers were called
        handler1.start_flow.assert_called_once_with("flow1", flow_data)
        handler2.start_flow.assert_called_once_with("flow1", flow_data)

    @pytest.mark.asyncio
    async def test_start_flow_with_handler_exception(self):
        """Test start_flow method handles handler exceptions"""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)
        
        # Add mock handler that raises exception
        handler = Mock()
        handler.start_flow = Mock(side_effect=Exception("Handler error"))
        
        config_receiver.add_handler(handler)
        
        flow_data = {"name": "test_flow", "steps": []}
        
        # This should not raise an exception
        await config_receiver.start_flow("flow1", flow_data)
        
        # Verify handler was called
        handler.start_flow.assert_called_once_with("flow1", flow_data)

    @pytest.mark.asyncio
    async def test_stop_flow_with_handlers(self):
        """Test stop_flow method with multiple handlers"""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)
        
        # Add mock handlers
        handler1 = Mock()
        handler1.stop_flow = Mock()
        handler2 = Mock()
        handler2.stop_flow = Mock()
        
        config_receiver.add_handler(handler1)
        config_receiver.add_handler(handler2)
        
        flow_data = {"name": "test_flow", "steps": []}
        
        await config_receiver.stop_flow("flow1", flow_data)
        
        # Verify all handlers were called
        handler1.stop_flow.assert_called_once_with("flow1", flow_data)
        handler2.stop_flow.assert_called_once_with("flow1", flow_data)

    @pytest.mark.asyncio
    async def test_stop_flow_with_handler_exception(self):
        """Test stop_flow method handles handler exceptions"""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)
        
        # Add mock handler that raises exception
        handler = Mock()
        handler.stop_flow = Mock(side_effect=Exception("Handler error"))
        
        config_receiver.add_handler(handler)
        
        flow_data = {"name": "test_flow", "steps": []}
        
        # This should not raise an exception
        await config_receiver.stop_flow("flow1", flow_data)
        
        # Verify handler was called
        handler.stop_flow.assert_called_once_with("flow1", flow_data)

    @pytest.mark.asyncio
    async def test_config_loader_creates_consumer(self):
        """Test config_loader method creates Pulsar consumer"""
        mock_backend = Mock()
        
        config_receiver = ConfigReceiver(mock_backend)
        # Temporarily restore the real config_loader for this test
        config_receiver.config_loader = _real_config_loader.__get__(config_receiver)
        
        # Mock Consumer class
        with patch('trustgraph.gateway.config.receiver.Consumer') as mock_consumer_class, \
             patch('uuid.uuid4') as mock_uuid:
            
            mock_uuid.return_value = "test-uuid"
            mock_consumer = Mock()
            async def mock_start():
                pass
            mock_consumer.start = mock_start
            mock_consumer_class.return_value = mock_consumer
            
            # Create a task that will complete quickly
            async def quick_task():
                await config_receiver.config_loader()
            
            # Run the task with a timeout to prevent hanging
            try:
                await asyncio.wait_for(quick_task(), timeout=0.1)
            except asyncio.TimeoutError:
                # This is expected since the method runs indefinitely
                pass
            
            # Verify Consumer was created with correct parameters
            mock_consumer_class.assert_called_once()
            call_args = mock_consumer_class.call_args
            
            assert call_args[1]['client'] == mock_backend
            assert call_args[1]['subscriber'] == "gateway-test-uuid"
            assert call_args[1]['handler'] == config_receiver.on_config
            assert call_args[1]['start_of_messages'] is True

    @patch('asyncio.create_task')
    @pytest.mark.asyncio
    async def test_start_creates_config_loader_task(self, mock_create_task):
        """Test start method creates config loader task"""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)
        
        # Mock create_task to avoid actually creating tasks with real coroutines
        mock_task = Mock()
        mock_create_task.return_value = mock_task
        
        await config_receiver.start()
        
        # Verify task was created
        mock_create_task.assert_called_once()
        
        # Verify the argument passed to create_task is a coroutine
        call_args = mock_create_task.call_args[0]
        assert len(call_args) == 1  # Should have one argument (the coroutine)

    @pytest.mark.asyncio
    async def test_on_config_mixed_flow_operations(self):
        """Test on_config with mixed add/remove operations"""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)
        
        # Pre-populate with existing flows
        config_receiver.flows = {
            "flow1": {"name": "test_flow_1", "steps": []},
            "flow2": {"name": "test_flow_2", "steps": []}
        }
        
        # Track calls manually instead of using Mock
        start_flow_calls = []
        stop_flow_calls = []
        
        async def mock_start_flow(*args):
            start_flow_calls.append(args)
        
        async def mock_stop_flow(*args):
            stop_flow_calls.append(args)
        
        # Directly assign to avoid patch.object detecting async methods  
        original_start_flow = config_receiver.start_flow
        original_stop_flow = config_receiver.stop_flow
        config_receiver.start_flow = mock_start_flow
        config_receiver.stop_flow = mock_stop_flow
        
        try:
            
            # Create mock message with flow1 removed and flow3 added
            mock_msg = Mock()
            mock_msg.value.return_value = Mock(
                version="1.0",
                config={
                    "flows": {
                        "flow2": '{"name": "test_flow_2", "steps": []}',
                        "flow3": '{"name": "test_flow_3", "steps": []}'
                    }
                }
            )
            
            await config_receiver.on_config(mock_msg, None, None)
            
            # Verify final state
            assert "flow1" not in config_receiver.flows
            assert "flow2" in config_receiver.flows
            assert "flow3" in config_receiver.flows
            
            # Verify operations
            assert len(start_flow_calls) == 1
            assert start_flow_calls[0] == ("flow3", {"name": "test_flow_3", "steps": []})
            assert len(stop_flow_calls) == 1
            assert stop_flow_calls[0] == ("flow1", {"name": "test_flow_1", "steps": []})
        
        finally:
            # Restore original methods
            config_receiver.start_flow = original_start_flow
            config_receiver.stop_flow = original_stop_flow

    @pytest.mark.asyncio
    async def test_on_config_invalid_json_flow_data(self):
        """Test on_config handles invalid JSON in flow data"""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)
        
        # Mock the start_flow method with an async function
        async def mock_start_flow(*args):
            pass
        config_receiver.start_flow = mock_start_flow
        
        # Create mock message with invalid JSON
        mock_msg = Mock()
        mock_msg.value.return_value = Mock(
            version="1.0",
            config={
                "flows": {
                    "flow1": '{"invalid": json}',  # Invalid JSON
                    "flow2": '{"name": "valid_flow", "steps": []}'  # Valid JSON
                }
            }
        )
        
        # This should handle the exception gracefully
        await config_receiver.on_config(mock_msg, None, None)
        
        # The entire operation should fail due to JSON parsing error
        # So no flows should be added
        assert config_receiver.flows == {}