"""
Tests for AsyncProcessor config notify pattern:
- register_config_handler with types filtering
- on_config_notify version comparison, type/workspace matching
- fetch_and_apply_config retry logic over per-workspace fetches
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock


@pytest.fixture
def processor():
    """Create an AsyncProcessor with mocked dependencies."""
    with patch('trustgraph.base.async_processor.get_pubsub') as mock_pubsub, \
         patch('trustgraph.base.async_processor.Consumer') as mock_consumer, \
         patch('trustgraph.base.async_processor.ProcessorMetrics') as mock_pm, \
         patch('trustgraph.base.async_processor.ConsumerMetrics') as mock_cm:

        mock_pubsub.return_value = MagicMock()
        mock_consumer.return_value = MagicMock()
        mock_pm.return_value = MagicMock()
        mock_cm.return_value = MagicMock()

        from trustgraph.base.async_processor import AsyncProcessor
        p = AsyncProcessor(
            id="test-processor",
            taskgroup=AsyncMock(),
        )
        return p


class TestRegisterConfigHandler:

    def test_register_without_types(self, processor):
        handler = AsyncMock()
        processor.register_config_handler(handler)

        assert len(processor.config_handlers) == 1
        assert processor.config_handlers[0]["handler"] is handler
        assert processor.config_handlers[0]["types"] is None

    def test_register_with_types(self, processor):
        handler = AsyncMock()
        processor.register_config_handler(handler, types=["prompt"])

        assert processor.config_handlers[0]["types"] == {"prompt"}

    def test_register_multiple_types(self, processor):
        handler = AsyncMock()
        processor.register_config_handler(
            handler, types=["schema", "collection"]
        )

        assert processor.config_handlers[0]["types"] == {
            "schema", "collection"
        }

    def test_register_multiple_handlers(self, processor):
        h1 = AsyncMock()
        h2 = AsyncMock()
        processor.register_config_handler(h1, types=["prompt"])
        processor.register_config_handler(h2, types=["schema"])

        assert len(processor.config_handlers) == 2


def _notify_msg(version, changes):
    """Build a Mock config-notify message with given version and changes dict."""
    msg = Mock()
    msg.value.return_value = Mock(version=version, changes=changes)
    return msg


class TestOnConfigNotify:

    @pytest.mark.asyncio
    async def test_skip_old_version(self, processor):
        processor.config_version = 5

        handler = AsyncMock()
        processor.register_config_handler(handler, types=["prompt"])

        msg = _notify_msg(3, {"prompt": ["default"]})
        await processor.on_config_notify(msg, None, None)

        handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_skip_same_version(self, processor):
        processor.config_version = 5

        handler = AsyncMock()
        processor.register_config_handler(handler, types=["prompt"])

        msg = _notify_msg(5, {"prompt": ["default"]})
        await processor.on_config_notify(msg, None, None)

        handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_skip_irrelevant_types(self, processor):
        processor.config_version = 1

        handler = AsyncMock()
        processor.register_config_handler(handler, types=["prompt"])

        msg = _notify_msg(2, {"schema": ["default"]})
        await processor.on_config_notify(msg, None, None)

        handler.assert_not_called()
        # Version should still be updated
        assert processor.config_version == 2

    @pytest.mark.asyncio
    async def test_fetch_on_relevant_type(self, processor):
        processor.config_version = 1

        handler = AsyncMock()
        processor.register_config_handler(handler, types=["prompt"])

        mock_client = AsyncMock()
        with patch.object(
            processor, '_create_config_client', return_value=mock_client
        ), patch.object(
            processor, '_fetch_type_workspace',
            new_callable=AsyncMock,
            return_value={"key": "value"},
        ):
            msg = _notify_msg(2, {"prompt": ["default"]})
            await processor.on_config_notify(msg, None, None)

        handler.assert_called_once_with(
            "default", {"prompt": {"key": "value"}}, 2
        )
        assert processor.config_version == 2

    @pytest.mark.asyncio
    async def test_handler_without_types_ignored_on_notify(self, processor):
        """Handlers registered without types never fire on notifications."""
        processor.config_version = 1

        handler = AsyncMock()
        processor.register_config_handler(handler)  # No types

        msg = _notify_msg(2, {"whatever": ["default"]})
        await processor.on_config_notify(msg, None, None)

        handler.assert_not_called()
        # Version still advances past the notify
        assert processor.config_version == 2

    @pytest.mark.asyncio
    async def test_mixed_handlers_type_filtering(self, processor):
        processor.config_version = 1

        prompt_handler = AsyncMock()
        schema_handler = AsyncMock()
        all_handler = AsyncMock()

        processor.register_config_handler(prompt_handler, types=["prompt"])
        processor.register_config_handler(schema_handler, types=["schema"])
        processor.register_config_handler(all_handler)

        mock_client = AsyncMock()
        with patch.object(
            processor, '_create_config_client', return_value=mock_client
        ), patch.object(
            processor, '_fetch_type_workspace',
            new_callable=AsyncMock,
            return_value={},
        ):
            msg = _notify_msg(2, {"prompt": ["default"]})
            await processor.on_config_notify(msg, None, None)

        prompt_handler.assert_called_once_with(
            "default", {"prompt": {}}, 2
        )
        schema_handler.assert_not_called()
        all_handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_multi_workspace_notify_invokes_handler_per_ws(
        self, processor
    ):
        """Notify affecting multiple workspaces invokes handler once per workspace."""
        processor.config_version = 1

        handler = AsyncMock()
        processor.register_config_handler(handler, types=["prompt"])

        mock_client = AsyncMock()
        with patch.object(
            processor, '_create_config_client', return_value=mock_client
        ), patch.object(
            processor, '_fetch_type_workspace',
            new_callable=AsyncMock,
            return_value={},
        ):
            msg = _notify_msg(2, {"prompt": ["ws1", "ws2"]})
            await processor.on_config_notify(msg, None, None)

        assert handler.call_count == 2
        called_workspaces = {c.args[0] for c in handler.call_args_list}
        assert called_workspaces == {"ws1", "ws2"}

    @pytest.mark.asyncio
    async def test_fetch_failure_handled(self, processor):
        processor.config_version = 1

        handler = AsyncMock()
        processor.register_config_handler(handler, types=["prompt"])

        mock_client = AsyncMock()
        with patch.object(
            processor, '_create_config_client', return_value=mock_client
        ), patch.object(
            processor, '_fetch_type_workspace',
            new_callable=AsyncMock,
            side_effect=RuntimeError("Connection failed"),
        ):
            msg = _notify_msg(2, {"prompt": ["default"]})
            # Should not raise
            await processor.on_config_notify(msg, None, None)

        handler.assert_not_called()


class TestFetchAndApplyConfig:

    @pytest.mark.asyncio
    async def test_applies_config_per_workspace(self, processor):
        """Startup fetch invokes handler once per workspace affected."""
        h = AsyncMock()
        processor.register_config_handler(h, types=["prompt"])

        mock_client = AsyncMock()

        async def fake_fetch_all(client, config_type):
            return {
                "ws1": {"k": "v1"},
                "ws2": {"k": "v2"},
            }, 10

        with patch.object(
            processor, '_create_config_client', return_value=mock_client
        ), patch.object(
            processor, '_fetch_type_all_workspaces',
            new=fake_fetch_all,
        ):
            await processor.fetch_and_apply_config()

        assert h.call_count == 2
        call_map = {c.args[0]: c.args[1] for c in h.call_args_list}
        assert call_map["ws1"] == {"prompt": {"k": "v1"}}
        assert call_map["ws2"] == {"prompt": {"k": "v2"}}
        assert processor.config_version == 10

    @pytest.mark.asyncio
    async def test_handler_without_types_skipped_at_startup(self, processor):
        """Handlers registered without types fetch nothing at startup."""
        typed = AsyncMock()
        untyped = AsyncMock()
        processor.register_config_handler(typed, types=["prompt"])
        processor.register_config_handler(untyped)

        mock_client = AsyncMock()

        async def fake_fetch_all(client, config_type):
            return {"default": {}}, 1

        with patch.object(
            processor, '_create_config_client', return_value=mock_client
        ), patch.object(
            processor, '_fetch_type_all_workspaces',
            new=fake_fetch_all,
        ):
            await processor.fetch_and_apply_config()

        typed.assert_called_once()
        untyped.assert_not_called()

    @pytest.mark.asyncio
    async def test_retries_on_failure(self, processor):
        h = AsyncMock()
        processor.register_config_handler(h, types=["prompt"])

        call_count = 0

        async def fake_fetch_all(client, config_type):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("not ready")
            return {"default": {"k": "v"}}, 5

        mock_client = AsyncMock()
        with patch.object(
            processor, '_create_config_client', return_value=mock_client
        ), patch.object(
            processor, '_fetch_type_all_workspaces',
            new=fake_fetch_all,
        ), patch('asyncio.sleep', new_callable=AsyncMock):
            await processor.fetch_and_apply_config()

        assert call_count == 3
        assert processor.config_version == 5
        h.assert_called_once_with(
            "default", {"prompt": {"k": "v"}}, 5
        )
