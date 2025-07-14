"""
Tests for Gateway Config Receiver
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import uuid

from trustgraph.gateway.config.receiver import ConfigReceiver

# Save the real method before patching
_real_config_loader = ConfigReceiver.config_loader

# Patch async methods at module level to prevent coroutine warnings
ConfigReceiver.config_loader = AsyncMock()


class TestConfigReceiver:
    """Test cases for ConfigReceiver class"""

    def test_config_receiver_initialization(self):
        """Test ConfigReceiver initialization"""
        mock_pulsar_client = Mock()
        
        config_receiver = ConfigReceiver(mock_pulsar_client)
        
        assert config_receiver.pulsar_client == mock_pulsar_client
        assert config_receiver.flow_handlers == []
        assert config_receiver.flows == {}

    def test_add_handler(self):
        """Test adding flow handlers"""
        mock_pulsar_client = Mock()
        config_receiver = ConfigReceiver(mock_pulsar_client)
        
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
        mock_pulsar_client = Mock()
        config_receiver = ConfigReceiver(mock_pulsar_client)
        
        # Mock the start_flow method
        config_receiver.start_flow = AsyncMock()
        
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
        assert config_receiver.start_flow.call_count == 2
        config_receiver.start_flow.assert_any_call("flow1", {"name": "test_flow_1", "steps": []})
        config_receiver.start_flow.assert_any_call("flow2", {"name": "test_flow_2", "steps": []})

    @pytest.mark.asyncio
    async def test_on_config_with_removed_flows(self):
        """Test on_config method with removed flows"""
        mock_pulsar_client = Mock()
        config_receiver = ConfigReceiver(mock_pulsar_client)
        
        # Pre-populate with existing flows
        config_receiver.flows = {
            "flow1": {"name": "test_flow_1", "steps": []},
            "flow2": {"name": "test_flow_2", "steps": []}
        }
        
        # Mock the stop_flow method
        config_receiver.stop_flow = AsyncMock()
        
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
        config_receiver.stop_flow.assert_called_once_with("flow2", {"name": "test_flow_2", "steps": []})

    @pytest.mark.asyncio
    async def test_on_config_with_no_flows(self):
        """Test on_config method with no flows in config"""
        mock_pulsar_client = Mock()
        config_receiver = ConfigReceiver(mock_pulsar_client)
        
        # Mock the start_flow and stop_flow methods
        config_receiver.start_flow = AsyncMock()
        config_receiver.stop_flow = AsyncMock()
        
        # Create mock message without flows
        mock_msg = Mock()
        mock_msg.value.return_value = Mock(
            version="1.0",
            config={}
        )
        
        await config_receiver.on_config(mock_msg, None, None)
        
        # Verify no flows were added
        assert config_receiver.flows == {}
        
        # Verify no flow operations were called
        config_receiver.start_flow.assert_not_called()
        config_receiver.stop_flow.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_config_exception_handling(self):
        """Test on_config method handles exceptions gracefully"""
        mock_pulsar_client = Mock()
        config_receiver = ConfigReceiver(mock_pulsar_client)
        
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
        mock_pulsar_client = Mock()
        config_receiver = ConfigReceiver(mock_pulsar_client)
        
        # Add mock handlers
        handler1 = Mock()
        handler1.start_flow = AsyncMock()
        handler2 = Mock()
        handler2.start_flow = AsyncMock()
        
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
        mock_pulsar_client = Mock()
        config_receiver = ConfigReceiver(mock_pulsar_client)
        
        # Add mock handler that raises exception
        handler = Mock()
        handler.start_flow = AsyncMock(side_effect=Exception("Handler error"))
        
        config_receiver.add_handler(handler)
        
        flow_data = {"name": "test_flow", "steps": []}
        
        # This should not raise an exception
        await config_receiver.start_flow("flow1", flow_data)
        
        # Verify handler was called
        handler.start_flow.assert_called_once_with("flow1", flow_data)

    @pytest.mark.asyncio
    async def test_stop_flow_with_handlers(self):
        """Test stop_flow method with multiple handlers"""
        mock_pulsar_client = Mock()
        config_receiver = ConfigReceiver(mock_pulsar_client)
        
        # Add mock handlers
        handler1 = Mock()
        handler1.stop_flow = AsyncMock()
        handler2 = Mock()
        handler2.stop_flow = AsyncMock()
        
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
        mock_pulsar_client = Mock()
        config_receiver = ConfigReceiver(mock_pulsar_client)
        
        # Add mock handler that raises exception
        handler = Mock()
        handler.stop_flow = AsyncMock(side_effect=Exception("Handler error"))
        
        config_receiver.add_handler(handler)
        
        flow_data = {"name": "test_flow", "steps": []}
        
        # This should not raise an exception
        await config_receiver.stop_flow("flow1", flow_data)
        
        # Verify handler was called
        handler.stop_flow.assert_called_once_with("flow1", flow_data)

    @pytest.mark.asyncio
    async def test_config_loader_creates_consumer(self):
        """Test config_loader method creates Pulsar consumer"""
        mock_pulsar_client = Mock()
        
        config_receiver = ConfigReceiver(mock_pulsar_client)
        # Temporarily restore the real config_loader for this test
        config_receiver.config_loader = _real_config_loader.__get__(config_receiver)
        
        # Mock Consumer class
        with patch('trustgraph.gateway.config.receiver.Consumer') as mock_consumer_class, \
             patch('uuid.uuid4') as mock_uuid:
            
            mock_uuid.return_value = "test-uuid"
            mock_consumer = Mock()
            mock_consumer.start = AsyncMock()
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
            
            assert call_args[1]['client'] == mock_pulsar_client
            assert call_args[1]['subscriber'] == "gateway-test-uuid"
            assert call_args[1]['handler'] == config_receiver.on_config
            assert call_args[1]['start_of_messages'] is True

    @patch('asyncio.create_task')
    @pytest.mark.asyncio
    async def test_start_creates_config_loader_task(self, mock_create_task):
        """Test start method creates config loader task"""
        mock_pulsar_client = Mock()
        config_receiver = ConfigReceiver(mock_pulsar_client)
        
        # Mock create_task to avoid actually creating tasks with real coroutines
        mock_task = AsyncMock()
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
        mock_pulsar_client = Mock()
        config_receiver = ConfigReceiver(mock_pulsar_client)
        
        # Pre-populate with existing flows
        config_receiver.flows = {
            "flow1": {"name": "test_flow_1", "steps": []},
            "flow2": {"name": "test_flow_2", "steps": []}
        }
        
        # Mock the flow methods to return awaitables
        async def mock_start_flow(*args):
            pass
        
        async def mock_stop_flow(*args):
            pass
        
        with patch.object(config_receiver, 'start_flow', side_effect=mock_start_flow) as start_flow_mock, \
             patch.object(config_receiver, 'stop_flow', side_effect=mock_stop_flow) as stop_flow_mock:
            
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
            start_flow_mock.assert_called_once_with("flow3", {"name": "test_flow_3", "steps": []})
            stop_flow_mock.assert_called_once_with("flow1", {"name": "test_flow_1", "steps": []})

    @pytest.mark.asyncio
    async def test_on_config_invalid_json_flow_data(self):
        """Test on_config handles invalid JSON in flow data"""
        mock_pulsar_client = Mock()
        config_receiver = ConfigReceiver(mock_pulsar_client)
        
        # Mock the start_flow method
        config_receiver.start_flow = AsyncMock()
        
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