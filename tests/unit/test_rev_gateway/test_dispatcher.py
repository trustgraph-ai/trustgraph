"""
Tests for Reverse Gateway Dispatcher
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch, ANY

from trustgraph.rev_gateway.dispatcher import MessageDispatcher


class TestMessageDispatcher:
    """Test cases for MessageDispatcher class"""

    def test_message_dispatcher_initialization_with_defaults(self):
        dispatcher = MessageDispatcher()

        assert dispatcher.max_workers == 10
        assert dispatcher.semaphore._value == 10
        assert dispatcher.active_tasks == set()
        assert dispatcher.backend is None
        assert dispatcher.auth is None
        assert dispatcher.dispatcher_manager is None
        assert len(dispatcher.service_mapping) > 0

    def test_message_dispatcher_initialization_with_custom_workers(self):
        dispatcher = MessageDispatcher(max_workers=5)

        assert dispatcher.max_workers == 5
        assert dispatcher.semaphore._value == 5

    @patch('trustgraph.rev_gateway.dispatcher.DispatcherManager')
    def test_message_dispatcher_initialization_with_backend(
        self, mock_dispatcher_manager,
    ):
        mock_backend = MagicMock()
        mock_config_receiver = MagicMock()
        mock_auth = MagicMock()
        mock_dispatcher_instance = MagicMock()
        mock_dispatcher_manager.return_value = mock_dispatcher_instance

        dispatcher = MessageDispatcher(
            max_workers=8,
            config_receiver=mock_config_receiver,
            backend=mock_backend,
            auth=mock_auth,
            timeout=300,
        )

        assert dispatcher.max_workers == 8
        assert dispatcher.backend == mock_backend
        assert dispatcher.auth == mock_auth
        assert dispatcher.dispatcher_manager == mock_dispatcher_instance
        mock_dispatcher_manager.assert_called_once_with(
            mock_backend, mock_config_receiver,
            auth=mock_auth, prefix="rev-gateway", timeout=300,
        )

    def test_message_dispatcher_service_mapping(self):
        dispatcher = MessageDispatcher()

        expected_services = [
            "text-completion", "graph-rag", "agent", "embeddings",
            "graph-embeddings", "triples", "document-load", "text-load",
            "flow", "knowledge", "config", "librarian", "document-rag",
        ]

        for service in expected_services:
            assert service in dispatcher.service_mapping

        assert dispatcher.service_mapping["document-load"] == "document"
        assert dispatcher.service_mapping["text-load"] == "text-document"

    @pytest.mark.asyncio
    async def test_handle_message_without_dispatcher_manager(self):
        dispatcher = MessageDispatcher()
        dispatcher.auth = MagicMock()
        dispatcher.auth.authenticate = AsyncMock(
            return_value=MagicMock(workspace="default")
        )

        sender = AsyncMock()

        await dispatcher.handle_message(
            {"id": "test-1", "service": "test", "request": {}},
            sender,
        )

        sender.assert_called_once()
        sent = sender.call_args[0][0]
        assert sent["id"] == "test-1"
        assert sent["error"]["message"] == "DispatcherManager not available"
        assert sent["error"]["type"] == "error"
        assert sent["complete"] is True

    @pytest.mark.asyncio
    async def test_handle_message_auth_failure(self):
        dispatcher = MessageDispatcher()
        dispatcher.auth = MagicMock()
        dispatcher.auth.authenticate = AsyncMock(
            side_effect=Exception("auth failure")
        )
        dispatcher.dispatcher_manager = MagicMock()

        sender = AsyncMock()

        await dispatcher.handle_message(
            {"id": "test-2", "token": "bad", "service": "test", "request": {}},
            sender,
        )

        sender.assert_called_once()
        sent = sender.call_args[0][0]
        assert sent["id"] == "test-2"
        assert "auth failure" in sent["error"]["message"]
        assert sent["complete"] is True

    @pytest.mark.asyncio
    async def test_handle_message_global_service(self):
        mock_dm = MagicMock()
        mock_dm.invoke_global_service = AsyncMock()

        dispatcher = MessageDispatcher()
        dispatcher.dispatcher_manager = mock_dm
        dispatcher.auth = MagicMock()
        dispatcher.auth.authenticate = AsyncMock(
            return_value=MagicMock(workspace="ws1")
        )

        sender = AsyncMock()

        with patch(
            'trustgraph.gateway.dispatch.manager.global_dispatchers',
            {"text-completion": True},
        ):
            await dispatcher.handle_message(
                {
                    "id": "test-3",
                    "token": "tg_key",
                    "service": "text-completion",
                    "request": {"prompt": "hello"},
                },
                sender,
            )

        mock_dm.invoke_global_service.assert_called_once()
        args, kwargs = mock_dm.invoke_global_service.call_args
        assert args[0] == {"prompt": "hello"}
        assert args[2] == "text-completion"
        assert kwargs["workspace"] == "ws1"

    @pytest.mark.asyncio
    async def test_handle_message_flow_service(self):
        mock_dm = MagicMock()
        mock_dm.invoke_flow_service = AsyncMock()

        dispatcher = MessageDispatcher()
        dispatcher.dispatcher_manager = mock_dm
        dispatcher.auth = MagicMock()
        dispatcher.auth.authenticate = AsyncMock(
            return_value=MagicMock(workspace="ws2")
        )

        sender = AsyncMock()

        with patch(
            'trustgraph.gateway.dispatch.manager.global_dispatchers', {},
        ):
            await dispatcher.handle_message(
                {
                    "id": "test-4",
                    "token": "tg_key",
                    "service": "document-rag",
                    "request": {"query": "test"},
                    "flow": "my-flow",
                },
                sender,
            )

        mock_dm.invoke_flow_service.assert_called_once_with(
            {"query": "test"}, ANY, "ws2", "my-flow", "document-rag",
        )

    @pytest.mark.asyncio
    async def test_handle_message_responder_sends_frames(self):
        mock_dm = MagicMock()

        async def fake_invoke(data, responder, svc, workspace=None):
            await responder({"partial": 1}, False)
            await responder({"partial": 2}, True)

        mock_dm.invoke_global_service = AsyncMock(side_effect=fake_invoke)

        dispatcher = MessageDispatcher()
        dispatcher.dispatcher_manager = mock_dm
        dispatcher.auth = MagicMock()
        dispatcher.auth.authenticate = AsyncMock(
            return_value=MagicMock(workspace="ws1")
        )

        sender = AsyncMock()

        with patch(
            'trustgraph.gateway.dispatch.manager.global_dispatchers',
            {"text-completion": True},
        ):
            await dispatcher.handle_message(
                {
                    "id": "test-5",
                    "token": "tg_key",
                    "service": "text-completion",
                    "request": {"prompt": "hi"},
                },
                sender,
            )

        assert sender.call_count == 2
        first = sender.call_args_list[0][0][0]
        second = sender.call_args_list[1][0][0]

        assert first == {
            "id": "test-5", "response": {"partial": 1}, "complete": False,
        }
        assert second == {
            "id": "test-5", "response": {"partial": 2}, "complete": True,
        }

    @pytest.mark.asyncio
    async def test_handle_message_workspace_from_identity(self):
        mock_dm = MagicMock()
        mock_dm.invoke_flow_service = AsyncMock()

        dispatcher = MessageDispatcher()
        dispatcher.dispatcher_manager = mock_dm
        dispatcher.auth = MagicMock()
        dispatcher.auth.authenticate = AsyncMock(
            return_value=MagicMock(workspace="derived-ws")
        )

        sender = AsyncMock()

        with patch(
            'trustgraph.gateway.dispatch.manager.global_dispatchers', {},
        ):
            await dispatcher.handle_message(
                {
                    "id": "test-6",
                    "token": "tg_key",
                    "service": "agent",
                    "request": {"question": "test"},
                    "flow": "default",
                },
                sender,
            )

        args = mock_dm.invoke_flow_service.call_args[0]
        assert args[2] == "derived-ws"

    @pytest.mark.asyncio
    async def test_shutdown(self):
        dispatcher = MessageDispatcher()

        async def dummy_task():
            await asyncio.sleep(0.01)

        task1 = asyncio.create_task(dummy_task())
        task2 = asyncio.create_task(dummy_task())
        dispatcher.active_tasks = {task1, task2}

        await dispatcher.shutdown()

        assert task1.done()
        assert task2.done()

    @pytest.mark.asyncio
    async def test_shutdown_with_no_tasks(self):
        dispatcher = MessageDispatcher()

        await dispatcher.shutdown()

        assert dispatcher.active_tasks == set()
