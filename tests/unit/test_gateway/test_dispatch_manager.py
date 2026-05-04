"""
Tests for Gateway Dispatcher Manager
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import uuid

from trustgraph.gateway.dispatch.manager import DispatcherManager, DispatcherWrapper

# Keep the real methods intact for proper testing


class TestDispatcherWrapper:
    """Test cases for DispatcherWrapper class"""

    def test_dispatcher_wrapper_initialization(self):
        """Test DispatcherWrapper initialization"""
        mock_handler = Mock()
        wrapper = DispatcherWrapper(mock_handler)
        
        assert wrapper.handler == mock_handler

    @pytest.mark.asyncio
    async def test_dispatcher_wrapper_process(self):
        """Test DispatcherWrapper process method"""
        mock_handler = AsyncMock()
        wrapper = DispatcherWrapper(mock_handler)
        
        result = await wrapper.process("arg1", "arg2")
        
        mock_handler.assert_called_once_with("arg1", "arg2")
        assert result == mock_handler.return_value


class TestDispatcherManager:
    """Test cases for DispatcherManager class"""

    def test_dispatcher_manager_initialization(self):
        """Test DispatcherManager initialization"""
        mock_backend = Mock()
        mock_config_receiver = Mock()
        
        manager = DispatcherManager(mock_backend, mock_config_receiver, auth=Mock())
        
        assert manager.backend == mock_backend
        assert manager.config_receiver == mock_config_receiver
        assert manager.prefix == "api-gateway"  # default prefix
        assert manager.flows == {}
        assert manager.dispatchers == {}
        assert isinstance(manager.dispatcher_lock, asyncio.Lock)

        # Verify manager was added as handler to config receiver
        mock_config_receiver.add_handler.assert_called_once_with(manager)

    def test_dispatcher_manager_initialization_with_custom_prefix(self):
        """Test DispatcherManager initialization with custom prefix"""
        mock_backend = Mock()
        mock_config_receiver = Mock()
        
        manager = DispatcherManager(
            mock_backend, mock_config_receiver,
            auth=Mock(), prefix="custom-prefix",
        )
        
        assert manager.prefix == "custom-prefix"

    @pytest.mark.asyncio
    async def test_start_flow(self):
        """Test start_flow method"""
        mock_backend = Mock()
        mock_config_receiver = Mock()
        manager = DispatcherManager(mock_backend, mock_config_receiver, auth=Mock())
        
        flow_data = {"name": "test_flow", "steps": []}
        
        await manager.start_flow("default", "flow1", flow_data)

        assert ("default", "flow1") in manager.flows
        assert manager.flows[("default", "flow1")] == flow_data

    @pytest.mark.asyncio
    async def test_stop_flow(self):
        """Test stop_flow method"""
        mock_backend = Mock()
        mock_config_receiver = Mock()
        manager = DispatcherManager(mock_backend, mock_config_receiver, auth=Mock())
        
        # Pre-populate with a flow
        flow_data = {"name": "test_flow", "steps": []}
        manager.flows[("default", "flow1")] = flow_data

        await manager.stop_flow("default", "flow1", flow_data)

        assert ("default", "flow1") not in manager.flows

    def test_dispatch_global_service_returns_wrapper(self):
        """Test dispatch_global_service returns DispatcherWrapper"""
        mock_backend = Mock()
        mock_config_receiver = Mock()
        manager = DispatcherManager(mock_backend, mock_config_receiver, auth=Mock())
        
        wrapper = manager.dispatch_global_service()
        
        assert isinstance(wrapper, DispatcherWrapper)
        assert wrapper.handler == manager.process_global_service

    def test_dispatch_core_export_returns_wrapper(self):
        """Test dispatch_core_export returns DispatcherWrapper"""
        mock_backend = Mock()
        mock_config_receiver = Mock()
        manager = DispatcherManager(mock_backend, mock_config_receiver, auth=Mock())
        
        wrapper = manager.dispatch_core_export()
        
        assert isinstance(wrapper, DispatcherWrapper)
        assert wrapper.handler == manager.process_core_export

    def test_dispatch_core_import_returns_wrapper(self):
        """Test dispatch_core_import returns DispatcherWrapper"""
        mock_backend = Mock()
        mock_config_receiver = Mock()
        manager = DispatcherManager(mock_backend, mock_config_receiver, auth=Mock())
        
        wrapper = manager.dispatch_core_import()
        
        assert isinstance(wrapper, DispatcherWrapper)
        assert wrapper.handler == manager.process_core_import

    @pytest.mark.asyncio
    async def test_process_core_import(self):
        """Test process_core_import method"""
        mock_backend = Mock()
        mock_config_receiver = Mock()
        manager = DispatcherManager(mock_backend, mock_config_receiver, auth=Mock())
        
        with patch('trustgraph.gateway.dispatch.manager.CoreImport') as mock_core_import:
            mock_importer = Mock()
            mock_importer.process = AsyncMock(return_value="import_result")
            mock_core_import.return_value = mock_importer
            
            result = await manager.process_core_import("data", "error", "ok", "request")
            
            mock_core_import.assert_called_once_with(mock_backend)
            mock_importer.process.assert_called_once_with("data", "error", "ok", "request")
            assert result == "import_result"

    @pytest.mark.asyncio
    async def test_process_core_export(self):
        """Test process_core_export method"""
        mock_backend = Mock()
        mock_config_receiver = Mock()
        manager = DispatcherManager(mock_backend, mock_config_receiver, auth=Mock())
        
        with patch('trustgraph.gateway.dispatch.manager.CoreExport') as mock_core_export:
            mock_exporter = Mock()
            mock_exporter.process = AsyncMock(return_value="export_result")
            mock_core_export.return_value = mock_exporter
            
            result = await manager.process_core_export("data", "error", "ok", "request")
            
            mock_core_export.assert_called_once_with(mock_backend)
            mock_exporter.process.assert_called_once_with("data", "error", "ok", "request")
            assert result == "export_result"

    @pytest.mark.asyncio
    async def test_process_global_service(self):
        """Test process_global_service method"""
        mock_backend = Mock()
        mock_config_receiver = Mock()
        manager = DispatcherManager(mock_backend, mock_config_receiver, auth=Mock())
        
        manager.invoke_global_service = AsyncMock(return_value="global_result")
        
        params = {"kind": "test_kind"}
        result = await manager.process_global_service("data", "responder", params)
        
        manager.invoke_global_service.assert_called_once_with("data", "responder", "test_kind", workspace=None)
        assert result == "global_result"

    @pytest.mark.asyncio
    async def test_invoke_global_service_with_existing_dispatcher(self):
        """Test invoke_global_service with existing dispatcher"""
        mock_backend = Mock()
        mock_config_receiver = Mock()
        manager = DispatcherManager(mock_backend, mock_config_receiver, auth=Mock())

        # Pre-populate with existing dispatcher
        mock_dispatcher = Mock()
        mock_dispatcher.process = AsyncMock(return_value="cached_result")
        manager.dispatchers[(None, "iam")] = mock_dispatcher

        result = await manager.invoke_global_service("data", "responder", "iam")

        mock_dispatcher.process.assert_called_once_with("data", "responder")
        assert result == "cached_result"

    @pytest.mark.asyncio
    async def test_invoke_global_service_creates_new_dispatcher(self):
        """Test invoke_global_service creates new dispatcher for system service"""
        mock_backend = Mock()
        mock_config_receiver = Mock()
        manager = DispatcherManager(mock_backend, mock_config_receiver, auth=Mock())

        with patch('trustgraph.gateway.dispatch.manager.global_dispatchers') as mock_dispatchers:
            mock_dispatcher_class = Mock()
            mock_dispatcher = Mock()
            mock_dispatcher.start = AsyncMock()
            mock_dispatcher.process = AsyncMock(return_value="new_result")
            mock_dispatcher_class.return_value = mock_dispatcher
            mock_dispatchers.__getitem__.return_value = mock_dispatcher_class

            result = await manager.invoke_global_service("data", "responder", "iam")

            mock_dispatcher_class.assert_called_once_with(
                backend=mock_backend,
                timeout=120,
                consumer="api-gateway-iam-request",
                subscriber="api-gateway-iam-request",
                request_queue=None,
                response_queue=None
            )
            mock_dispatcher.start.assert_called_once()
            mock_dispatcher.process.assert_called_once_with("data", "responder")

            assert manager.dispatchers[(None, "iam")] == mock_dispatcher
            assert result == "new_result"

    @pytest.mark.asyncio
    async def test_invoke_global_service_workspace_required_for_workspace_dispatchers(self):
        """Workspace dispatchers (config, flow, etc.) require a workspace"""
        mock_backend = Mock()
        mock_config_receiver = Mock()
        manager = DispatcherManager(mock_backend, mock_config_receiver, auth=Mock())

        with pytest.raises(RuntimeError, match="Workspace is required for config"):
            await manager.invoke_global_service("data", "responder", "config")

    @pytest.mark.asyncio
    async def test_invoke_global_service_workspace_dispatcher_with_workspace(self):
        """Workspace dispatchers work when workspace is provided"""
        mock_backend = Mock()
        mock_config_receiver = Mock()
        manager = DispatcherManager(mock_backend, mock_config_receiver, auth=Mock())

        mock_dispatcher = Mock()
        mock_dispatcher.process = AsyncMock(return_value="ws_result")
        manager.dispatchers[("alice", "config")] = mock_dispatcher

        result = await manager.invoke_global_service(
            "data", "responder", "config", workspace="alice",
        )

        mock_dispatcher.process.assert_called_once_with("data", "responder")
        assert result == "ws_result"

    def test_dispatch_flow_import_returns_method(self):
        """Test dispatch_flow_import returns correct method"""
        mock_backend = Mock()
        mock_config_receiver = Mock()
        manager = DispatcherManager(mock_backend, mock_config_receiver, auth=Mock())
        
        result = manager.dispatch_flow_import()
        
        assert result == manager.process_flow_import

    def test_dispatch_flow_export_returns_method(self):
        """Test dispatch_flow_export returns correct method"""
        mock_backend = Mock()
        mock_config_receiver = Mock()
        manager = DispatcherManager(mock_backend, mock_config_receiver, auth=Mock())
        
        result = manager.dispatch_flow_export()
        
        assert result == manager.process_flow_export

    def test_dispatch_socket_returns_method(self):
        """Test dispatch_socket returns correct method"""
        mock_backend = Mock()
        mock_config_receiver = Mock()
        manager = DispatcherManager(mock_backend, mock_config_receiver, auth=Mock())
        
        result = manager.dispatch_socket()
        
        assert result == manager.process_socket

    def test_dispatch_flow_service_returns_wrapper(self):
        """Test dispatch_flow_service returns DispatcherWrapper"""
        mock_backend = Mock()
        mock_config_receiver = Mock()
        manager = DispatcherManager(mock_backend, mock_config_receiver, auth=Mock())
        
        wrapper = manager.dispatch_flow_service()
        
        assert isinstance(wrapper, DispatcherWrapper)
        assert wrapper.handler == manager.process_flow_service

    @pytest.mark.asyncio
    async def test_process_flow_import_with_valid_flow_and_kind(self):
        """Test process_flow_import with valid flow and kind"""
        mock_backend = Mock()
        mock_config_receiver = Mock()
        manager = DispatcherManager(mock_backend, mock_config_receiver, auth=Mock())
        
        # Setup test flow
        manager.flows[("default", "test_flow")] = {
            "interfaces": {
                "triples-store": {"flow": "test_queue"}
            }
        }

        with patch('trustgraph.gateway.dispatch.manager.import_dispatchers') as mock_dispatchers, \
             patch('uuid.uuid4') as mock_uuid:
            mock_uuid.return_value = "test-uuid"
            mock_dispatcher_class = Mock()
            mock_dispatcher = Mock()
            mock_dispatcher.start = AsyncMock()
            mock_dispatcher_class.return_value = mock_dispatcher
            mock_dispatchers.__getitem__.return_value = mock_dispatcher_class
            mock_dispatchers.__contains__.return_value = True

            params = {"flow": "test_flow", "kind": "triples"}
            result = await manager.process_flow_import("ws", "running", params)
            
            mock_dispatcher_class.assert_called_once_with(
                backend=mock_backend,
                ws="ws",
                running="running",
                queue="test_queue"
            )
            mock_dispatcher.start.assert_called_once()
            assert result == mock_dispatcher

    @pytest.mark.asyncio
    async def test_process_flow_import_with_invalid_flow(self):
        """Test process_flow_import with invalid flow"""
        mock_backend = Mock()
        mock_config_receiver = Mock()
        manager = DispatcherManager(mock_backend, mock_config_receiver, auth=Mock())
        
        params = {"flow": "invalid_flow", "kind": "triples"}
        
        with pytest.raises(RuntimeError, match="Invalid flow"):
            await manager.process_flow_import("ws", "running", params)

    @pytest.mark.asyncio
    async def test_process_flow_import_with_invalid_kind(self):
        """Test process_flow_import with invalid kind"""
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            mock_backend = Mock()
            mock_config_receiver = Mock()
            manager = DispatcherManager(mock_backend, mock_config_receiver, auth=Mock())
        
        # Setup test flow
        manager.flows[("default", "test_flow")] = {
            "interfaces": {
                "triples-store": {"flow": "test_queue"}
            }
        }

        with patch('trustgraph.gateway.dispatch.manager.import_dispatchers') as mock_dispatchers:
            mock_dispatchers.__contains__.return_value = False
            
            params = {"flow": "test_flow", "kind": "invalid_kind"}
            
            with pytest.raises(RuntimeError, match="Invalid kind"):
                await manager.process_flow_import("ws", "running", params)

    @pytest.mark.asyncio
    async def test_process_flow_export_with_valid_flow_and_kind(self):
        """Test process_flow_export with valid flow and kind"""
        mock_backend = Mock()
        mock_config_receiver = Mock()
        manager = DispatcherManager(mock_backend, mock_config_receiver, auth=Mock())
        
        # Setup test flow
        manager.flows[("default", "test_flow")] = {
            "interfaces": {
                "triples-store": {"flow": "test_queue"}
            }
        }

        with patch('trustgraph.gateway.dispatch.manager.export_dispatchers') as mock_dispatchers, \
             patch('uuid.uuid4') as mock_uuid:
            mock_uuid.return_value = "test-uuid"
            mock_dispatcher_class = Mock()
            mock_dispatcher = Mock()
            mock_dispatcher_class.return_value = mock_dispatcher
            mock_dispatchers.__getitem__.return_value = mock_dispatcher_class
            mock_dispatchers.__contains__.return_value = True
            
            params = {"flow": "test_flow", "kind": "triples"}
            result = await manager.process_flow_export("ws", "running", params)
            
            mock_dispatcher_class.assert_called_once_with(
                backend=mock_backend,
                ws="ws",
                running="running",
                queue="test_queue",
                consumer="api-gateway-test-uuid",
                subscriber="api-gateway-test-uuid"
            )
            assert result == mock_dispatcher

    @pytest.mark.asyncio
    async def test_process_socket(self):
        """process_socket constructs a Mux with the manager's auth
        instance passed through — this is the gateway's trust path
        for first-frame WebSocket authentication.  A Mux cannot be
        built without auth (tested separately); this test pins that
        the dispatcher-manager threads the correct auth value into
        the Mux constructor call."""
        mock_backend = Mock()
        mock_config_receiver = Mock()
        mock_auth = Mock()
        manager = DispatcherManager(
            mock_backend, mock_config_receiver, auth=mock_auth,
        )

        with patch('trustgraph.gateway.dispatch.manager.Mux') as mock_mux:
            mock_mux_instance = Mock()
            mock_mux.return_value = mock_mux_instance

            result = await manager.process_socket("ws", "running", {})

            mock_mux.assert_called_once_with(
                manager, "ws", "running", auth=mock_auth,
            )
            assert result == mock_mux_instance

    def test_dispatcher_manager_requires_auth(self):
        """Constructing a DispatcherManager without an auth argument
        must fail — a no-auth DispatcherManager would produce a
        Mux without authentication, silently downgrading the socket
        auth path."""
        mock_backend = Mock()
        mock_config_receiver = Mock()

        with pytest.raises(ValueError, match="auth"):
            DispatcherManager(mock_backend, mock_config_receiver, auth=None)

    @pytest.mark.asyncio
    async def test_process_flow_service(self):
        """Test process_flow_service method"""
        mock_backend = Mock()
        mock_config_receiver = Mock()
        manager = DispatcherManager(mock_backend, mock_config_receiver, auth=Mock())
        
        manager.invoke_flow_service = AsyncMock(return_value="flow_result")
        
        params = {"flow": "test_flow", "kind": "agent"}
        result = await manager.process_flow_service("data", "responder", params)
        
        manager.invoke_flow_service.assert_called_once_with("data", "responder", "default", "test_flow", "agent")
        assert result == "flow_result"

    @pytest.mark.asyncio
    async def test_invoke_flow_service_with_existing_dispatcher(self):
        """Test invoke_flow_service with existing dispatcher"""
        mock_backend = Mock()
        mock_config_receiver = Mock()
        manager = DispatcherManager(mock_backend, mock_config_receiver, auth=Mock())
        
        # Add flow to the flows dictionary
        manager.flows[("default", "test_flow")] = {"services": {"agent": {}}}

        # Pre-populate with existing dispatcher
        mock_dispatcher = Mock()
        mock_dispatcher.process = AsyncMock(return_value="cached_result")
        manager.dispatchers[("default", "test_flow", "agent")] = mock_dispatcher

        result = await manager.invoke_flow_service("data", "responder", "default", "test_flow", "agent")
        
        mock_dispatcher.process.assert_called_once_with("data", "responder")
        assert result == "cached_result"

    @pytest.mark.asyncio
    async def test_invoke_flow_service_creates_request_response_dispatcher(self):
        """Test invoke_flow_service creates request-response dispatcher"""
        mock_backend = Mock()
        mock_config_receiver = Mock()
        manager = DispatcherManager(mock_backend, mock_config_receiver, auth=Mock())
        
        # Setup test flow
        manager.flows[("default", "test_flow")] = {
            "interfaces": {
                "agent": {
                    "request": "agent_request_queue",
                    "response": "agent_response_queue"
                }
            }
        }

        with patch('trustgraph.gateway.dispatch.manager.request_response_dispatchers') as mock_dispatchers:
            mock_dispatcher_class = Mock()
            mock_dispatcher = Mock()
            mock_dispatcher.start = AsyncMock()
            mock_dispatcher.process = AsyncMock(return_value="new_result")
            mock_dispatcher_class.return_value = mock_dispatcher
            mock_dispatchers.__getitem__.return_value = mock_dispatcher_class
            mock_dispatchers.__contains__.return_value = True

            result = await manager.invoke_flow_service("data", "responder", "default", "test_flow", "agent")

            # Verify dispatcher was created with correct parameters
            mock_dispatcher_class.assert_called_once_with(
                backend=mock_backend,
                request_queue="agent_request_queue",
                response_queue="agent_response_queue",
                timeout=120,
                consumer="api-gateway-default-test_flow-agent-request",
                subscriber="api-gateway-default-test_flow-agent-request"
            )
            mock_dispatcher.start.assert_called_once()
            mock_dispatcher.process.assert_called_once_with("data", "responder")

            # Verify dispatcher was cached
            assert manager.dispatchers[("default", "test_flow", "agent")] == mock_dispatcher
            assert result == "new_result"

    @pytest.mark.asyncio
    async def test_invoke_flow_service_creates_sender_dispatcher(self):
        """Test invoke_flow_service creates sender dispatcher"""
        mock_backend = Mock()
        mock_config_receiver = Mock()
        manager = DispatcherManager(mock_backend, mock_config_receiver, auth=Mock())
        
        # Setup test flow
        manager.flows[("default", "test_flow")] = {
            "interfaces": {
                "text-load": {"flow": "text_load_queue"}
            }
        }

        with patch('trustgraph.gateway.dispatch.manager.request_response_dispatchers') as mock_rr_dispatchers, \
             patch('trustgraph.gateway.dispatch.manager.sender_dispatchers') as mock_sender_dispatchers:
            mock_rr_dispatchers.__contains__.return_value = False
            mock_sender_dispatchers.__contains__.return_value = True

            mock_dispatcher_class = Mock()
            mock_dispatcher = Mock()
            mock_dispatcher.start = AsyncMock()
            mock_dispatcher.process = AsyncMock(return_value="sender_result")
            mock_dispatcher_class.return_value = mock_dispatcher
            mock_sender_dispatchers.__getitem__.return_value = mock_dispatcher_class

            result = await manager.invoke_flow_service("data", "responder", "default", "test_flow", "text-load")

            # Verify dispatcher was created with correct parameters
            mock_dispatcher_class.assert_called_once_with(
                backend=mock_backend,
                queue="text_load_queue"
            )
            mock_dispatcher.start.assert_called_once()
            mock_dispatcher.process.assert_called_once_with("data", "responder")

            # Verify dispatcher was cached
            assert manager.dispatchers[("default", "test_flow", "text-load")] == mock_dispatcher
            assert result == "sender_result"

    @pytest.mark.asyncio
    async def test_invoke_flow_service_invalid_flow(self):
        """Test invoke_flow_service with invalid flow"""
        mock_backend = Mock()
        mock_config_receiver = Mock()
        manager = DispatcherManager(mock_backend, mock_config_receiver, auth=Mock())
        
        with pytest.raises(RuntimeError, match="Invalid flow"):
            await manager.invoke_flow_service("data", "responder", "default", "invalid_flow", "agent")

    @pytest.mark.asyncio
    async def test_invoke_flow_service_unsupported_kind_by_flow(self):
        """Test invoke_flow_service with kind not supported by flow"""
        mock_backend = Mock()
        mock_config_receiver = Mock()
        manager = DispatcherManager(mock_backend, mock_config_receiver, auth=Mock())
        
        # Setup test flow without agent interface
        manager.flows[("default", "test_flow")] = {
            "interfaces": {
                "text-completion": {"request": "req", "response": "resp"}
            }
        }

        with pytest.raises(RuntimeError, match="This kind not supported by flow"):
            await manager.invoke_flow_service("data", "responder", "default", "test_flow", "agent")

    @pytest.mark.asyncio
    async def test_invoke_flow_service_invalid_kind(self):
        """Test invoke_flow_service with invalid kind"""
        mock_backend = Mock()
        mock_config_receiver = Mock()
        manager = DispatcherManager(mock_backend, mock_config_receiver, auth=Mock())

        # Setup test flow with interface but unsupported kind
        manager.flows[("default", "test_flow")] = {
            "interfaces": {
                "invalid-kind": {"request": "req", "response": "resp"}
            }
        }

        with patch('trustgraph.gateway.dispatch.manager.request_response_dispatchers') as mock_rr_dispatchers, \
             patch('trustgraph.gateway.dispatch.manager.sender_dispatchers') as mock_sender_dispatchers:
            mock_rr_dispatchers.__contains__.return_value = False
            mock_sender_dispatchers.__contains__.return_value = False

            with pytest.raises(RuntimeError, match="Invalid kind"):
                await manager.invoke_flow_service("data", "responder", "default", "test_flow", "invalid-kind")

    @pytest.mark.asyncio
    async def test_invoke_global_service_concurrent_calls_create_single_dispatcher(self):
        """Concurrent calls for the same service must create exactly one dispatcher.

        Before the fix, await dispatcher.start() yielded to the event loop and
        multiple coroutines could all pass the 'key not in self.dispatchers' check
        before any of them wrote the result back, creating duplicate Pulsar consumers.
        """
        mock_backend = Mock()
        mock_config_receiver = Mock()
        manager = DispatcherManager(mock_backend, mock_config_receiver, auth=Mock())

        async def slow_start():
            # Yield to the event loop so other coroutines get a chance to run,
            # reproducing the window that caused the original race condition.
            await asyncio.sleep(0)

        with patch('trustgraph.gateway.dispatch.manager.global_dispatchers') as mock_dispatchers:
            mock_dispatcher_class = Mock()
            mock_dispatcher = Mock()
            mock_dispatcher.start = AsyncMock(side_effect=slow_start)
            mock_dispatcher.process = AsyncMock(return_value="result")
            mock_dispatcher_class.return_value = mock_dispatcher
            mock_dispatchers.__getitem__.return_value = mock_dispatcher_class

            results = await asyncio.gather(*[
                manager.invoke_global_service("data", "responder", "iam")
                for _ in range(5)
            ])

        assert mock_dispatcher_class.call_count == 1, (
            "Dispatcher class instantiated more than once — duplicate consumer bug"
        )
        assert mock_dispatcher.start.call_count == 1
        assert manager.dispatchers[(None, "iam")] is mock_dispatcher
        assert all(r == "result" for r in results)

    @pytest.mark.asyncio
    async def test_invoke_flow_service_concurrent_calls_create_single_dispatcher(self):
        """Concurrent calls for the same flow+kind must create exactly one dispatcher.

        invoke_flow_service has the same check-then-create pattern as
        invoke_global_service and is protected by the same dispatcher_lock.
        """
        mock_backend = Mock()
        mock_config_receiver = Mock()
        manager = DispatcherManager(mock_backend, mock_config_receiver, auth=Mock())

        manager.flows[("default", "test_flow")] = {
            "interfaces": {
                "agent": {
                    "request": "agent_request_queue",
                    "response": "agent_response_queue",
                }
            }
        }

        async def slow_start():
            await asyncio.sleep(0)

        with patch('trustgraph.gateway.dispatch.manager.request_response_dispatchers') as mock_rr_dispatchers:
            mock_dispatcher_class = Mock()
            mock_dispatcher = Mock()
            mock_dispatcher.start = AsyncMock(side_effect=slow_start)
            mock_dispatcher.process = AsyncMock(return_value="result")
            mock_dispatcher_class.return_value = mock_dispatcher
            mock_rr_dispatchers.__getitem__.return_value = mock_dispatcher_class
            mock_rr_dispatchers.__contains__.return_value = True

            results = await asyncio.gather(*[
                manager.invoke_flow_service("data", "responder", "default", "test_flow", "agent")
                for _ in range(5)
            ])

        assert mock_dispatcher_class.call_count == 1, (
            "Dispatcher class instantiated more than once — duplicate consumer bug"
        )
        assert mock_dispatcher.start.call_count == 1
        assert manager.dispatchers[("default", "test_flow", "agent")] is mock_dispatcher
        assert all(r == "result" for r in results)