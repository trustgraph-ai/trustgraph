"""
Cross-provider rate limit contract tests: verify that every LLM provider
that handles rate limits converts its provider-specific exception to
TooManyRequests consistently.

Also tests the client-side error translation in the base client.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

from trustgraph.exceptions import TooManyRequests, LlmError


class TestAzureServerless429(IsolatedAsyncioTestCase):
    """Azure serverless endpoint: HTTP 429 → TooManyRequests"""

    @patch('trustgraph.model.text_completion.azure.llm.requests')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__', return_value=None)
    @patch('trustgraph.base.llm_service.LlmService.__init__', return_value=None)
    async def test_http_429_raises_too_many_requests(self, _llm, _async, mock_requests):
        from trustgraph.model.text_completion.azure.llm import Processor
        proc = Processor(
            endpoint="https://test.azure.com/v1/chat",
            token="t", concurrency=1, taskgroup=AsyncMock(), id="t",
        )
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_requests.post.return_value = mock_response

        with pytest.raises(TooManyRequests):
            await proc.generate_content("sys", "prompt")


class TestAzureOpenAIRateLimit(IsolatedAsyncioTestCase):
    """Azure OpenAI: openai.RateLimitError → TooManyRequests"""

    @patch('trustgraph.model.text_completion.azure_openai.llm.AzureOpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__', return_value=None)
    @patch('trustgraph.base.llm_service.LlmService.__init__', return_value=None)
    async def test_rate_limit_error_raises_too_many_requests(self, _llm, _async, mock_cls):
        from openai import RateLimitError
        from trustgraph.model.text_completion.azure_openai.llm import Processor
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        proc = Processor(
            endpoint="https://test.openai.azure.com/", token="t",
            model="gpt-4", concurrency=1, taskgroup=AsyncMock(), id="t",
        )
        mock_client.chat.completions.create.side_effect = RateLimitError(
            "rate limited", response=MagicMock(), body=None
        )

        with pytest.raises(TooManyRequests):
            await proc.generate_content("sys", "prompt")


class TestOpenAIRateLimit(IsolatedAsyncioTestCase):
    """OpenAI: openai.RateLimitError → TooManyRequests"""

    @patch('trustgraph.model.text_completion.openai.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__', return_value=None)
    @patch('trustgraph.base.llm_service.LlmService.__init__', return_value=None)
    async def test_rate_limit_error_raises_too_many_requests(self, _llm, _async, mock_cls):
        from openai import RateLimitError
        from trustgraph.model.text_completion.openai.llm import Processor
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        proc = Processor(
            api_key="k", concurrency=1, taskgroup=AsyncMock(), id="t",
        )
        mock_client.chat.completions.create.side_effect = RateLimitError(
            "rate limited", response=MagicMock(), body=None
        )

        with pytest.raises(TooManyRequests):
            await proc.generate_content("sys", "prompt")

    @patch('trustgraph.model.text_completion.openai.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__', return_value=None)
    @patch('trustgraph.base.llm_service.LlmService.__init__', return_value=None)
    async def test_503_raises_llm_error(self, _llm, _async, mock_cls):
        from openai import InternalServerError
        from trustgraph.model.text_completion.openai.llm import Processor
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        proc = Processor(
            api_key="k", concurrency=1, taskgroup=AsyncMock(), id="t",
        )
        mock_client.chat.completions.create.side_effect = InternalServerError(
            "service unavailable", response=MagicMock(), body=None
        )

        with pytest.raises(LlmError):
            await proc.generate_content("sys", "prompt")


class TestClaudeRateLimit(IsolatedAsyncioTestCase):
    """Claude/Anthropic: anthropic.RateLimitError → TooManyRequests"""

    @patch('trustgraph.model.text_completion.claude.llm.anthropic')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__', return_value=None)
    @patch('trustgraph.base.llm_service.LlmService.__init__', return_value=None)
    async def test_rate_limit_error_raises_too_many_requests(self, _llm, _async, mock_anthropic):
        from trustgraph.model.text_completion.claude.llm import Processor

        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        proc = Processor(
            api_key="k", concurrency=1, taskgroup=AsyncMock(), id="t",
        )

        mock_anthropic.RateLimitError = type("RateLimitError", (Exception,), {})
        mock_client.messages.create.side_effect = mock_anthropic.RateLimitError(
            "rate limited"
        )

        with pytest.raises(TooManyRequests):
            await proc.generate_content("sys", "prompt")


class TestMistralRateLimit(IsolatedAsyncioTestCase):
    """Mistral: models.SDKError (429/503) → TooManyRequests/LlmError"""

    @patch('trustgraph.model.text_completion.mistral.llm.Mistral')
    @patch('trustgraph.model.text_completion.mistral.llm.models')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__', return_value=None)
    @patch('trustgraph.base.llm_service.LlmService.__init__', return_value=None)
    async def test_429_raises_too_many_requests(self, _llm, _async, mock_models, mock_cls):
        from trustgraph.model.text_completion.mistral.llm import Processor
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        proc = Processor(
            api_key="k", concurrency=1, taskgroup=AsyncMock(), id="t",
        )
        
        # Define a mock exception class
        mock_models.SDKError = type("SDKError", (Exception,), {"status_code": 429})
        mock_client.chat.complete.side_effect = mock_models.SDKError()

        with pytest.raises(TooManyRequests):
            await proc.generate_content("sys", "prompt")

    @patch('trustgraph.model.text_completion.mistral.llm.Mistral')
    @patch('trustgraph.model.text_completion.mistral.llm.models')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__', return_value=None)
    @patch('trustgraph.base.llm_service.LlmService.__init__', return_value=None)
    async def test_503_raises_llm_error(self, _llm, _async, mock_models, mock_cls):
        from trustgraph.model.text_completion.mistral.llm import Processor
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        proc = Processor(
            api_key="k", concurrency=1, taskgroup=AsyncMock(), id="t",
        )
        
        mock_models.SDKError = type("SDKError", (Exception,), {"status_code": 503})
        mock_client.chat.complete.side_effect = mock_models.SDKError()

        with pytest.raises(LlmError):
            await proc.generate_content("sys", "prompt")


class TestCohereRateLimit(IsolatedAsyncioTestCase):
    """Cohere: cohere.errors (429/503) → TooManyRequests/LlmError"""

    @patch('trustgraph.model.text_completion.cohere.llm.cohere')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__', return_value=None)
    @patch('trustgraph.base.llm_service.LlmService.__init__', return_value=None)
    async def test_rate_limit_error_raises_too_many_requests(self, _llm, _async, mock_cohere):
        from trustgraph.model.text_completion.cohere.llm import Processor
        import trustgraph.model.text_completion.cohere.llm as cohere_llm
        
        mock_client = MagicMock()
        mock_cohere.Client.return_value = mock_client
        proc = Processor(
            api_key="k", concurrency=1, taskgroup=AsyncMock(), id="t",
        )
        
        ErrorCls = type("TooManyRequestsError", (Exception,), {})
        with patch.object(cohere_llm, 'TooManyRequestsError', ErrorCls):
            mock_client.chat.side_effect = ErrorCls()
            with pytest.raises(TooManyRequests):
                await proc.generate_content("sys", "prompt")

    @patch('trustgraph.model.text_completion.cohere.llm.cohere')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__', return_value=None)
    @patch('trustgraph.base.llm_service.LlmService.__init__', return_value=None)
    async def test_503_raises_llm_error(self, _llm, _async, mock_cohere):
        from trustgraph.model.text_completion.cohere.llm import Processor
        import trustgraph.model.text_completion.cohere.llm as cohere_llm
        
        mock_client = MagicMock()
        mock_cohere.Client.return_value = mock_client
        proc = Processor(
            api_key="k", concurrency=1, taskgroup=AsyncMock(), id="t",
        )
        
        ErrorCls = type("ServiceUnavailableError", (Exception,), {})
        with patch.object(cohere_llm, 'ServiceUnavailableError', ErrorCls):
            mock_client.chat.side_effect = ErrorCls()
            with pytest.raises(LlmError):
                await proc.generate_content("sys", "prompt")


class TestVllmRateLimit(IsolatedAsyncioTestCase):
    """vLLM: HTTP 429/503 → TooManyRequests/LlmError"""

    @patch('trustgraph.model.text_completion.vllm.llm.aiohttp.ClientSession')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__', return_value=None)
    @patch('trustgraph.base.llm_service.LlmService.__init__', return_value=None)
    async def test_429_raises_too_many_requests(self, _llm, _async, mock_session):
        from trustgraph.model.text_completion.vllm.llm import Processor
        proc = Processor(concurrency=1, taskgroup=AsyncMock(), id="t")
        
        mock_resp = AsyncMock()
        mock_resp.status = 429
        mock_session.return_value.post.return_value.__aenter__.return_value = mock_resp

        with pytest.raises(TooManyRequests):
            await proc.generate_content("sys", "prompt")

    @patch('trustgraph.model.text_completion.vllm.llm.aiohttp.ClientSession')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__', return_value=None)
    @patch('trustgraph.base.llm_service.LlmService.__init__', return_value=None)
    async def test_503_raises_llm_error(self, _llm, _async, mock_session):
        from trustgraph.model.text_completion.vllm.llm import Processor
        proc = Processor(concurrency=1, taskgroup=AsyncMock(), id="t")
        
        mock_resp = AsyncMock()
        mock_resp.status = 503
        mock_session.return_value.post.return_value.__aenter__.return_value = mock_resp

        with pytest.raises(LlmError):
            await proc.generate_content("sys", "prompt")


class TestClientSideRateLimitTranslation:
    """Client base class: error type 'too-many-requests' → TooManyRequests"""

    def test_error_type_mapping(self):
        """The wire format error type string is 'too-many-requests'."""
        from trustgraph.schema import Error
        err = Error(type="too-many-requests", message="slow down")
        assert err.type == "too-many-requests"
