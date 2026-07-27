"""
Tests for AsyncProcessor config notify pattern:
- register_config_handler with types filtering
- on_config_notify version comparison, type/workspace matching
- fetch_and_apply_config retry logic over per-workspace fetches
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock


def _make_processor(**extra):
    """Create an AsyncProcessor with mocked dependencies."""
    with patch('trustgraph.base.async_processor.get_async_pubsub') as mock_pubsub:

        mock_pubsub.return_value = MagicMock()

        from trustgraph.base.async_processor import AsyncProcessor
        return AsyncProcessor(
            id="test-processor",
            taskgroup=AsyncMock(),
            **extra,
        )


@pytest.fixture
def processor():
    return _make_processor()


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


class TestOnConfigNotify:

    @pytest.mark.asyncio
    async def test_skip_old_version(self, processor):
        processor.config_version = 10
        handler = AsyncMock()
        processor.register_config_handler(handler, types=["prompt"])

        msg = MagicMock()
        msg.value.return_value = MagicMock(
            version=5, changes={"prompt": ["default"]},
            workspace_changes=None,
        )

        await processor.on_config_notify(msg, None, None)
        handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_skip_same_version(self, processor):
        processor.config_version = 10
        handler = AsyncMock()
        processor.register_config_handler(handler, types=["prompt"])

        msg = MagicMock()
        msg.value.return_value = MagicMock(
            version=10, changes={"prompt": ["default"]},
            workspace_changes=None,
        )

        await processor.on_config_notify(msg, None, None)
        handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_skip_irrelevant_types(self, processor):
        processor.config_version = 0
        handler = AsyncMock()
        processor.register_config_handler(handler, types=["prompt"])

        msg = MagicMock()
        msg.value.return_value = MagicMock(
            version=1, changes={"schema": ["default"]},
            workspace_changes=None,
        )

        await processor.on_config_notify(msg, None, None)
        handler.assert_not_called()
        assert processor.config_version == 1

    @pytest.mark.asyncio
    async def test_fetch_on_relevant_type(self, processor):
        processor.config_version = 0
        handler = AsyncMock()
        processor.register_config_handler(handler, types=["prompt"])

        msg = MagicMock()
        msg.value.return_value = MagicMock(
            version=2, changes={"prompt": ["default"]},
            workspace_changes=None,
        )

        mock_client = AsyncMock()
        processor._fetch_type_workspace = AsyncMock(
            return_value={"system": "You are a bot"}
        )
        processor._create_config_client = AsyncMock(
            return_value=mock_client
        )

        await processor.on_config_notify(msg, None, None)

        handler.assert_called_once()
        call_args = handler.call_args
        assert call_args[0][0] == "default"
        assert processor.config_version == 2

    @pytest.mark.asyncio
    async def test_handler_without_types_ignored_on_notify(self, processor):
        processor.config_version = 0
        handler = AsyncMock()
        processor.register_config_handler(handler)

        msg = MagicMock()
        msg.value.return_value = MagicMock(
            version=1, changes={"prompt": ["default"]},
            workspace_changes=None,
        )

        await processor.on_config_notify(msg, None, None)
        handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_mixed_handlers_type_filtering(self, processor):
        h_prompt = AsyncMock()
        h_schema = AsyncMock()
        processor.register_config_handler(h_prompt, types=["prompt"])
        processor.register_config_handler(h_schema, types=["schema"])

        msg = MagicMock()
        msg.value.return_value = MagicMock(
            version=1, changes={"prompt": ["default"]},
            workspace_changes=None,
        )

        mock_client = AsyncMock()
        processor._fetch_type_workspace = AsyncMock(
            return_value={"system": "You are a bot"}
        )
        processor._create_config_client = AsyncMock(
            return_value=mock_client
        )

        await processor.on_config_notify(msg, None, None)

        h_prompt.assert_called_once()
        h_schema.assert_not_called()

    @pytest.mark.asyncio
    async def test_multi_workspace_notify_invokes_handler_per_ws(
        self, processor,
    ):
        handler = AsyncMock()
        processor.register_config_handler(handler, types=["prompt"])

        msg = MagicMock()
        msg.value.return_value = MagicMock(
            version=1, changes={"prompt": ["ws1", "ws2"]},
            workspace_changes=None,
        )

        mock_client = AsyncMock()
        processor._fetch_type_workspace = AsyncMock(
            return_value={"system": "You are a bot"}
        )
        processor._create_config_client = AsyncMock(
            return_value=mock_client
        )

        await processor.on_config_notify(msg, None, None)

        assert handler.call_count == 2
        workspaces = {call[0][0] for call in handler.call_args_list}
        assert workspaces == {"ws1", "ws2"}

    @pytest.mark.asyncio
    async def test_fetch_failure_handled(self, processor):
        handler = AsyncMock()
        processor.register_config_handler(handler, types=["prompt"])

        msg = MagicMock()
        msg.value.return_value = MagicMock(
            version=1, changes={"prompt": ["default"]},
            workspace_changes=None,
        )

        processor._create_config_client = AsyncMock(
            side_effect=RuntimeError("connection failed")
        )

        await processor.on_config_notify(msg, None, None)

        handler.assert_not_called()
        assert processor.config_version == 0


class TestFetchAndApplyConfig:

    @pytest.mark.asyncio
    async def test_applies_config_per_workspace(self, processor):
        handler = AsyncMock()
        processor.register_config_handler(handler, types=["prompt"])

        mock_client = AsyncMock()
        processor._create_config_client = AsyncMock(
            return_value=mock_client
        )
        processor._fetch_type_all_workspaces = AsyncMock(
            return_value=(
                {"default": {"system": "bot"}, "ws2": {"system": "other"}},
                5,
            )
        )

        await processor.fetch_and_apply_config()

        assert handler.call_count == 2
        workspaces = {call[0][0] for call in handler.call_args_list}
        assert workspaces == {"default", "ws2"}
        assert processor.config_version == 5

    @pytest.mark.asyncio
    async def test_handler_without_types_skipped_at_startup(self, processor):
        handler = AsyncMock()
        processor.register_config_handler(handler)

        mock_client = AsyncMock()
        processor._create_config_client = AsyncMock(
            return_value=mock_client
        )

        await processor.fetch_and_apply_config()

        handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_retries_on_failure(self, processor):
        handler = AsyncMock()
        processor.register_config_handler(handler, types=["prompt"])

        call_count = 0

        async def mock_create():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("transient failure")
            client = AsyncMock()
            return client

        processor._create_config_client = mock_create
        processor._fetch_type_all_workspaces = AsyncMock(
            return_value=({"default": {"system": "bot"}}, 1)
        )

        with patch('asyncio.sleep', new_callable=AsyncMock):
            await processor.fetch_and_apply_config()

        assert call_count == 2
        handler.assert_called_once()


class TestConfigTimeout:
    """--config-timeout threads from params into the config client."""

    def test_default(self, processor):
        assert processor.config_timeout == 60

    def test_param_override(self):
        p = _make_processor(config_timeout=25)
        assert p.config_timeout == 25

    @pytest.mark.asyncio
    async def test_create_config_client_uses_config_timeout(self):
        p = _make_processor(config_timeout=25)

        with patch(
            'trustgraph.base.async_processor.RequestResponseClient'
        ) as mock_rr:
            mock_rr.create = AsyncMock()
            await p._create_config_client()

        assert mock_rr.create.call_args.kwargs["default_timeout"] == 25

    def test_add_args(self):
        import argparse
        from trustgraph.base.async_processor import AsyncProcessor

        parser = argparse.ArgumentParser()
        AsyncProcessor.add_args(parser)

        args = parser.parse_args([])
        assert args.config_timeout == 60

        args = parser.parse_args(["--config-timeout", "120"])
        assert args.config_timeout == 120
