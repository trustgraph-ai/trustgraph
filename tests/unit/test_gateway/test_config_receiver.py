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


def _notify(version, changes):
    msg = Mock()
    msg.value.return_value = Mock(version=version, changes=changes)
    return msg


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
    async def test_on_config_notify_new_version_fetches_per_workspace(self):
        """Notify with newer version fetches each affected workspace."""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)
        config_receiver.config_version = 1

        fetch_calls = []

        async def mock_fetch(workspace, retry=False):
            fetch_calls.append(workspace)

        config_receiver.fetch_and_apply_workspace = mock_fetch

        msg = _notify(2, {"flow": ["ws1", "ws2"]})
        await config_receiver.on_config_notify(msg, None, None)

        assert set(fetch_calls) == {"ws1", "ws2"}
        assert config_receiver.config_version == 2

    @pytest.mark.asyncio
    async def test_on_config_notify_old_version_ignored(self):
        """Older-version notifies are ignored."""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)
        config_receiver.config_version = 5

        fetch_calls = []

        async def mock_fetch(workspace, retry=False):
            fetch_calls.append(workspace)

        config_receiver.fetch_and_apply_workspace = mock_fetch

        msg = _notify(3, {"flow": ["ws1"]})
        await config_receiver.on_config_notify(msg, None, None)

        assert fetch_calls == []

    @pytest.mark.asyncio
    async def test_on_config_notify_irrelevant_types_ignored(self):
        """Notifies without flow changes advance version but skip fetch."""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)
        config_receiver.config_version = 1

        fetch_calls = []

        async def mock_fetch(workspace, retry=False):
            fetch_calls.append(workspace)

        config_receiver.fetch_and_apply_workspace = mock_fetch

        msg = _notify(2, {"prompt": ["ws1"]})
        await config_receiver.on_config_notify(msg, None, None)

        assert fetch_calls == []
        assert config_receiver.config_version == 2

    @pytest.mark.asyncio
    async def test_on_config_notify_exception_handling(self):
        """on_config_notify swallows exceptions from message decode."""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)

        mock_msg = Mock()
        mock_msg.value.side_effect = Exception("Test exception")

        # Should not raise
        await config_receiver.on_config_notify(mock_msg, None, None)

    @pytest.mark.asyncio
    async def test_fetch_and_apply_workspace_starts_new_flows(self):
        """fetch_and_apply_workspace starts newly-configured flows."""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)

        mock_resp = Mock()
        mock_resp.error = None
        mock_resp.version = 5
        mock_resp.config = {
            "flow": {
                "flow1": '{"name": "test_flow_1"}',
                "flow2": '{"name": "test_flow_2"}',
            }
        }

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_resp
        config_receiver._create_config_client = Mock(return_value=mock_client)

        start_flow_calls = []

        async def mock_start_flow(workspace, id, flow):
            start_flow_calls.append((workspace, id, flow))

        config_receiver.start_flow = mock_start_flow

        await config_receiver.fetch_and_apply_workspace("default")

        assert config_receiver.config_version == 5
        assert "flow1" in config_receiver.flows["default"]
        assert "flow2" in config_receiver.flows["default"]
        assert len(start_flow_calls) == 2
        assert all(c[0] == "default" for c in start_flow_calls)

    @pytest.mark.asyncio
    async def test_fetch_and_apply_workspace_stops_removed_flows(self):
        """fetch_and_apply_workspace stops flows no longer configured."""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)

        config_receiver.flows = {
            "default": {
                "flow1": {"name": "test_flow_1"},
                "flow2": {"name": "test_flow_2"},
            }
        }

        mock_resp = Mock()
        mock_resp.error = None
        mock_resp.version = 5
        mock_resp.config = {
            "flow": {
                "flow1": '{"name": "test_flow_1"}',
            }
        }

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_resp
        config_receiver._create_config_client = Mock(return_value=mock_client)

        stop_flow_calls = []

        async def mock_stop_flow(workspace, id, flow):
            stop_flow_calls.append((workspace, id, flow))

        config_receiver.stop_flow = mock_stop_flow

        await config_receiver.fetch_and_apply_workspace("default")

        assert "flow1" in config_receiver.flows["default"]
        assert "flow2" not in config_receiver.flows["default"]
        assert len(stop_flow_calls) == 1
        assert stop_flow_calls[0][:2] == ("default", "flow2")

    @pytest.mark.asyncio
    async def test_fetch_and_apply_workspace_with_no_flows(self):
        """Empty workspace config clears any local flow state."""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)

        mock_resp = Mock()
        mock_resp.error = None
        mock_resp.version = 1
        mock_resp.config = {}

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_resp
        config_receiver._create_config_client = Mock(return_value=mock_client)

        await config_receiver.fetch_and_apply_workspace("default")

        assert config_receiver.flows.get("default", {}) == {}
        assert config_receiver.config_version == 1

    @pytest.mark.asyncio
    async def test_start_flow_with_handlers(self):
        """start_flow fans out to every registered flow handler."""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)

        handler1 = Mock()
        handler1.start_flow = AsyncMock()
        handler2 = Mock()
        handler2.start_flow = AsyncMock()

        config_receiver.add_handler(handler1)
        config_receiver.add_handler(handler2)

        flow_data = {"name": "test_flow", "steps": []}

        await config_receiver.start_flow("default", "flow1", flow_data)

        handler1.start_flow.assert_awaited_once_with(
            "default", "flow1", flow_data
        )
        handler2.start_flow.assert_awaited_once_with(
            "default", "flow1", flow_data
        )

    @pytest.mark.asyncio
    async def test_start_flow_with_handler_exception(self):
        """Handler exceptions in start_flow do not propagate."""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)

        handler = Mock()
        handler.start_flow = AsyncMock(side_effect=Exception("Handler error"))

        config_receiver.add_handler(handler)

        flow_data = {"name": "test_flow", "steps": []}

        # Should not raise
        await config_receiver.start_flow("default", "flow1", flow_data)

        handler.start_flow.assert_awaited_once_with(
            "default", "flow1", flow_data
        )

    @pytest.mark.asyncio
    async def test_stop_flow_with_handlers(self):
        """stop_flow fans out to every registered flow handler."""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)

        handler1 = Mock()
        handler1.stop_flow = AsyncMock()
        handler2 = Mock()
        handler2.stop_flow = AsyncMock()

        config_receiver.add_handler(handler1)
        config_receiver.add_handler(handler2)

        flow_data = {"name": "test_flow", "steps": []}

        await config_receiver.stop_flow("default", "flow1", flow_data)

        handler1.stop_flow.assert_awaited_once_with(
            "default", "flow1", flow_data
        )
        handler2.stop_flow.assert_awaited_once_with(
            "default", "flow1", flow_data
        )

    @pytest.mark.asyncio
    async def test_stop_flow_with_handler_exception(self):
        """Handler exceptions in stop_flow do not propagate."""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)

        handler = Mock()
        handler.stop_flow = AsyncMock(side_effect=Exception("Handler error"))

        config_receiver.add_handler(handler)

        flow_data = {"name": "test_flow", "steps": []}

        # Should not raise
        await config_receiver.stop_flow("default", "flow1", flow_data)

        handler.stop_flow.assert_awaited_once_with(
            "default", "flow1", flow_data
        )

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
    async def test_fetch_and_apply_workspace_mixed_flow_operations(self):
        """fetch_and_apply_workspace adds, keeps and removes flows in one pass."""
        mock_backend = Mock()
        config_receiver = ConfigReceiver(mock_backend)

        config_receiver.flows = {
            "default": {
                "flow1": {"name": "test_flow_1"},
                "flow2": {"name": "test_flow_2"},
            }
        }

        mock_resp = Mock()
        mock_resp.error = None
        mock_resp.version = 5
        mock_resp.config = {
            "flow": {
                "flow2": '{"name": "test_flow_2"}',
                "flow3": '{"name": "test_flow_3"}',
            }
        }

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_resp
        config_receiver._create_config_client = Mock(return_value=mock_client)

        start_calls = []
        stop_calls = []

        async def mock_start_flow(workspace, id, flow):
            start_calls.append((workspace, id, flow))

        async def mock_stop_flow(workspace, id, flow):
            stop_calls.append((workspace, id, flow))

        config_receiver.start_flow = mock_start_flow
        config_receiver.stop_flow = mock_stop_flow

        await config_receiver.fetch_and_apply_workspace("default")

        ws_flows = config_receiver.flows["default"]
        assert "flow1" not in ws_flows
        assert "flow2" in ws_flows
        assert "flow3" in ws_flows
        assert len(start_calls) == 1
        assert start_calls[0][:2] == ("default", "flow3")
        assert len(stop_calls) == 1
        assert stop_calls[0][:2] == ("default", "flow1")
