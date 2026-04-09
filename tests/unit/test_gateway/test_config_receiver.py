"""
Tests for Gateway Config Receiver
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, MagicMock, AsyncMock
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
        assert config_receiver.config_version == 0

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
    async def test_on_config_notify_new_version(self):
        """Test on_config_notify triggers fetch for newer version"""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)
        config_receiver.config_version = 1

        # Mock fetch_and_apply
        fetch_calls = []
        async def mock_fetch(**kwargs):
            fetch_calls.append(kwargs)
        config_receiver.fetch_and_apply = mock_fetch

        # Create notify message with newer version
        mock_msg = Mock()
        mock_msg.value.return_value = Mock(version=2, types=["flow"])

        await config_receiver.on_config_notify(mock_msg, None, None)

        assert len(fetch_calls) == 1

    @pytest.mark.asyncio
    async def test_on_config_notify_old_version_ignored(self):
        """Test on_config_notify ignores older versions"""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)
        config_receiver.config_version = 5

        fetch_calls = []
        async def mock_fetch(**kwargs):
            fetch_calls.append(kwargs)
        config_receiver.fetch_and_apply = mock_fetch

        # Create notify message with older version
        mock_msg = Mock()
        mock_msg.value.return_value = Mock(version=3, types=["flow"])

        await config_receiver.on_config_notify(mock_msg, None, None)

        assert len(fetch_calls) == 0

    @pytest.mark.asyncio
    async def test_on_config_notify_irrelevant_types_ignored(self):
        """Test on_config_notify ignores types the gateway doesn't care about"""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)
        config_receiver.config_version = 1

        fetch_calls = []
        async def mock_fetch(**kwargs):
            fetch_calls.append(kwargs)
        config_receiver.fetch_and_apply = mock_fetch

        # Create notify message with non-flow type
        mock_msg = Mock()
        mock_msg.value.return_value = Mock(version=2, types=["prompt"])

        await config_receiver.on_config_notify(mock_msg, None, None)

        # Version should be updated but no fetch
        assert len(fetch_calls) == 0
        assert config_receiver.config_version == 2

    @pytest.mark.asyncio
    async def test_on_config_notify_flow_type_triggers_fetch(self):
        """Test on_config_notify fetches for flow-related types"""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)
        config_receiver.config_version = 1

        fetch_calls = []
        async def mock_fetch(**kwargs):
            fetch_calls.append(kwargs)
        config_receiver.fetch_and_apply = mock_fetch

        for type_name in ["flow", "active-flow"]:
            fetch_calls.clear()
            config_receiver.config_version = 1

            mock_msg = Mock()
            mock_msg.value.return_value = Mock(version=2, types=[type_name])

            await config_receiver.on_config_notify(mock_msg, None, None)

            assert len(fetch_calls) == 1, f"Expected fetch for type {type_name}"

    @pytest.mark.asyncio
    async def test_on_config_notify_exception_handling(self):
        """Test on_config_notify handles exceptions gracefully"""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)

        # Create notify message that causes an exception
        mock_msg = Mock()
        mock_msg.value.side_effect = Exception("Test exception")

        # Should not raise
        await config_receiver.on_config_notify(mock_msg, None, None)

    @pytest.mark.asyncio
    async def test_fetch_and_apply_with_new_flows(self):
        """Test fetch_and_apply starts new flows"""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)

        # Mock config_client
        mock_resp = Mock()
        mock_resp.error = None
        mock_resp.version = 5
        mock_resp.config = {
            "flow": {
                "flow1": '{"name": "test_flow_1"}',
                "flow2": '{"name": "test_flow_2"}'
            }
        }

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_resp
        config_receiver.config_client = mock_client

        start_flow_calls = []
        async def mock_start_flow(id, flow):
            start_flow_calls.append((id, flow))
        config_receiver.start_flow = mock_start_flow

        await config_receiver.fetch_and_apply()

        assert config_receiver.config_version == 5
        assert "flow1" in config_receiver.flows
        assert "flow2" in config_receiver.flows
        assert len(start_flow_calls) == 2

    @pytest.mark.asyncio
    async def test_fetch_and_apply_with_removed_flows(self):
        """Test fetch_and_apply stops removed flows"""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)

        # Pre-populate with existing flows
        config_receiver.flows = {
            "flow1": {"name": "test_flow_1"},
            "flow2": {"name": "test_flow_2"}
        }

        # Config now only has flow1
        mock_resp = Mock()
        mock_resp.error = None
        mock_resp.version = 5
        mock_resp.config = {
            "flow": {
                "flow1": '{"name": "test_flow_1"}'
            }
        }

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_resp
        config_receiver.config_client = mock_client

        stop_flow_calls = []
        async def mock_stop_flow(id, flow):
            stop_flow_calls.append((id, flow))
        config_receiver.stop_flow = mock_stop_flow

        await config_receiver.fetch_and_apply()

        assert "flow1" in config_receiver.flows
        assert "flow2" not in config_receiver.flows
        assert len(stop_flow_calls) == 1
        assert stop_flow_calls[0][0] == "flow2"

    @pytest.mark.asyncio
    async def test_fetch_and_apply_with_no_flows(self):
        """Test fetch_and_apply with empty config"""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)

        mock_resp = Mock()
        mock_resp.error = None
        mock_resp.version = 1
        mock_resp.config = {}

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_resp
        config_receiver.config_client = mock_client

        await config_receiver.fetch_and_apply()

        assert config_receiver.flows == {}
        assert config_receiver.config_version == 1

    @pytest.mark.asyncio
    async def test_start_flow_with_handlers(self):
        """Test start_flow method with multiple handlers"""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)

        handler1 = Mock()
        handler1.start_flow = Mock()
        handler2 = Mock()
        handler2.start_flow = Mock()

        config_receiver.add_handler(handler1)
        config_receiver.add_handler(handler2)

        flow_data = {"name": "test_flow", "steps": []}

        await config_receiver.start_flow("flow1", flow_data)

        handler1.start_flow.assert_called_once_with("flow1", flow_data)
        handler2.start_flow.assert_called_once_with("flow1", flow_data)

    @pytest.mark.asyncio
    async def test_start_flow_with_handler_exception(self):
        """Test start_flow method handles handler exceptions"""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)

        handler = Mock()
        handler.start_flow = Mock(side_effect=Exception("Handler error"))

        config_receiver.add_handler(handler)

        flow_data = {"name": "test_flow", "steps": []}

        # Should not raise
        await config_receiver.start_flow("flow1", flow_data)

        handler.start_flow.assert_called_once_with("flow1", flow_data)

    @pytest.mark.asyncio
    async def test_stop_flow_with_handlers(self):
        """Test stop_flow method with multiple handlers"""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)

        handler1 = Mock()
        handler1.stop_flow = Mock()
        handler2 = Mock()
        handler2.stop_flow = Mock()

        config_receiver.add_handler(handler1)
        config_receiver.add_handler(handler2)

        flow_data = {"name": "test_flow", "steps": []}

        await config_receiver.stop_flow("flow1", flow_data)

        handler1.stop_flow.assert_called_once_with("flow1", flow_data)
        handler2.stop_flow.assert_called_once_with("flow1", flow_data)

    @pytest.mark.asyncio
    async def test_stop_flow_with_handler_exception(self):
        """Test stop_flow method handles handler exceptions"""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)

        handler = Mock()
        handler.stop_flow = Mock(side_effect=Exception("Handler error"))

        config_receiver.add_handler(handler)

        flow_data = {"name": "test_flow", "steps": []}

        # Should not raise
        await config_receiver.stop_flow("flow1", flow_data)

        handler.stop_flow.assert_called_once_with("flow1", flow_data)

    @patch('asyncio.create_task')
    @pytest.mark.asyncio
    async def test_start_creates_config_loader_task(self, mock_create_task):
        """Test start method creates config loader task"""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)

        mock_task = Mock()
        mock_create_task.return_value = mock_task

        await config_receiver.start()

        mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_and_apply_mixed_flow_operations(self):
        """Test fetch_and_apply with mixed add/remove operations"""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)

        # Pre-populate
        config_receiver.flows = {
            "flow1": {"name": "test_flow_1"},
            "flow2": {"name": "test_flow_2"}
        }

        # Config removes flow1, keeps flow2, adds flow3
        mock_resp = Mock()
        mock_resp.error = None
        mock_resp.version = 5
        mock_resp.config = {
            "flow": {
                "flow2": '{"name": "test_flow_2"}',
                "flow3": '{"name": "test_flow_3"}'
            }
        }

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_resp
        config_receiver.config_client = mock_client

        start_calls = []
        stop_calls = []

        async def mock_start_flow(id, flow):
            start_calls.append((id, flow))
        async def mock_stop_flow(id, flow):
            stop_calls.append((id, flow))

        config_receiver.start_flow = mock_start_flow
        config_receiver.stop_flow = mock_stop_flow

        await config_receiver.fetch_and_apply()

        assert "flow1" not in config_receiver.flows
        assert "flow2" in config_receiver.flows
        assert "flow3" in config_receiver.flows
        assert len(start_calls) == 1
        assert start_calls[0][0] == "flow3"
        assert len(stop_calls) == 1
        assert stop_calls[0][0] == "flow1"
