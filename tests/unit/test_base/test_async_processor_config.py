"""
Tests for AsyncProcessor config notify pattern:
- register_config_handler with types filtering
- on_config_notify version comparison and type matching
- fetch_config with short-lived client
- fetch_and_apply_config retry logic
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from trustgraph.schema import Term, IRI, LITERAL


# Patch heavy dependencies before importing AsyncProcessor
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


class TestOnConfigNotify:

    @pytest.mark.asyncio
    async def test_skip_old_version(self, processor):
        processor.config_version = 5

        handler = AsyncMock()
        processor.register_config_handler(handler, types=["prompt"])

        msg = Mock()
        msg.value.return_value = Mock(version=3, types=["prompt"])

        await processor.on_config_notify(msg, None, None)

        handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_skip_same_version(self, processor):
        processor.config_version = 5

        handler = AsyncMock()
        processor.register_config_handler(handler, types=["prompt"])

        msg = Mock()
        msg.value.return_value = Mock(version=5, types=["prompt"])

        await processor.on_config_notify(msg, None, None)

        handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_skip_irrelevant_types(self, processor):
        processor.config_version = 1

        handler = AsyncMock()
        processor.register_config_handler(handler, types=["prompt"])

        msg = Mock()
        msg.value.return_value = Mock(version=2, types=["schema"])

        await processor.on_config_notify(msg, None, None)

        handler.assert_not_called()
        # Version should still be updated
        assert processor.config_version == 2

    @pytest.mark.asyncio
    async def test_fetch_on_relevant_type(self, processor):
        processor.config_version = 1

        handler = AsyncMock()
        processor.register_config_handler(handler, types=["prompt"])

        # Mock fetch_config
        mock_config = {"prompt": {"key": "value"}}
        with patch.object(
            processor, 'fetch_config',
            new_callable=AsyncMock,
            return_value=(mock_config, 2)
        ):
            msg = Mock()
            msg.value.return_value = Mock(version=2, types=["prompt"])

            await processor.on_config_notify(msg, None, None)

        handler.assert_called_once_with(mock_config, 2)
        assert processor.config_version == 2

    @pytest.mark.asyncio
    async def test_handler_without_types_always_called(self, processor):
        processor.config_version = 1

        handler = AsyncMock()
        processor.register_config_handler(handler)  # No types = all

        mock_config = {"anything": {}}
        with patch.object(
            processor, 'fetch_config',
            new_callable=AsyncMock,
            return_value=(mock_config, 2)
        ):
            msg = Mock()
            msg.value.return_value = Mock(version=2, types=["whatever"])

            await processor.on_config_notify(msg, None, None)

        handler.assert_called_once_with(mock_config, 2)

    @pytest.mark.asyncio
    async def test_mixed_handlers_type_filtering(self, processor):
        processor.config_version = 1

        prompt_handler = AsyncMock()
        schema_handler = AsyncMock()
        all_handler = AsyncMock()

        processor.register_config_handler(prompt_handler, types=["prompt"])
        processor.register_config_handler(schema_handler, types=["schema"])
        processor.register_config_handler(all_handler)

        mock_config = {"prompt": {}}
        with patch.object(
            processor, 'fetch_config',
            new_callable=AsyncMock,
            return_value=(mock_config, 2)
        ):
            msg = Mock()
            msg.value.return_value = Mock(version=2, types=["prompt"])

            await processor.on_config_notify(msg, None, None)

        prompt_handler.assert_called_once()
        schema_handler.assert_not_called()
        all_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_empty_types_invokes_all(self, processor):
        """Empty types list (startup signal) should invoke all handlers."""
        processor.config_version = 1

        h1 = AsyncMock()
        h2 = AsyncMock()
        processor.register_config_handler(h1, types=["prompt"])
        processor.register_config_handler(h2, types=["schema"])

        mock_config = {}
        with patch.object(
            processor, 'fetch_config',
            new_callable=AsyncMock,
            return_value=(mock_config, 2)
        ):
            msg = Mock()
            msg.value.return_value = Mock(version=2, types=[])

            await processor.on_config_notify(msg, None, None)

        h1.assert_called_once()
        h2.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_failure_handled(self, processor):
        processor.config_version = 1

        handler = AsyncMock()
        processor.register_config_handler(handler)

        with patch.object(
            processor, 'fetch_config',
            new_callable=AsyncMock,
            side_effect=RuntimeError("Connection failed")
        ):
            msg = Mock()
            msg.value.return_value = Mock(version=2, types=["prompt"])

            # Should not raise
            await processor.on_config_notify(msg, None, None)

        handler.assert_not_called()


class TestFetchConfig:

    @pytest.mark.asyncio
    async def test_fetch_returns_config_and_version(self, processor):
        mock_resp = Mock()
        mock_resp.error = None
        mock_resp.config = {"prompt": {"key": "val"}}
        mock_resp.version = 42

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_resp

        with patch.object(
            processor, '_create_config_client', return_value=mock_client
        ):
            config, version = await processor.fetch_config()

        assert config == {"prompt": {"key": "val"}}
        assert version == 42
        mock_client.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_raises_on_error_response(self, processor):
        mock_resp = Mock()
        mock_resp.error = Mock(message="not found")
        mock_resp.config = {}
        mock_resp.version = 0

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_resp

        with patch.object(
            processor, '_create_config_client', return_value=mock_client
        ):
            with pytest.raises(RuntimeError, match="Config error"):
                await processor.fetch_config()

        mock_client.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_stops_client_on_exception(self, processor):
        mock_client = AsyncMock()
        mock_client.request.side_effect = TimeoutError("timeout")

        with patch.object(
            processor, '_create_config_client', return_value=mock_client
        ):
            with pytest.raises(TimeoutError):
                await processor.fetch_config()

        mock_client.stop.assert_called_once()


class TestFetchAndApplyConfig:

    @pytest.mark.asyncio
    async def test_applies_config_to_all_handlers(self, processor):
        h1 = AsyncMock()
        h2 = AsyncMock()
        processor.register_config_handler(h1, types=["prompt"])
        processor.register_config_handler(h2, types=["schema"])

        mock_config = {"prompt": {}, "schema": {}}
        with patch.object(
            processor, 'fetch_config',
            new_callable=AsyncMock,
            return_value=(mock_config, 10)
        ):
            await processor.fetch_and_apply_config()

        # On startup, all handlers are invoked regardless of type
        h1.assert_called_once_with(mock_config, 10)
        h2.assert_called_once_with(mock_config, 10)
        assert processor.config_version == 10

    @pytest.mark.asyncio
    async def test_retries_on_failure(self, processor):
        call_count = 0
        mock_config = {"prompt": {}}

        async def mock_fetch():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("not ready")
            return mock_config, 5

        with patch.object(processor, 'fetch_config', side_effect=mock_fetch), \
             patch('asyncio.sleep', new_callable=AsyncMock):
            await processor.fetch_and_apply_config()

        assert call_count == 3
        assert processor.config_version == 5
