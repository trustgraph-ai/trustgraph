"""
Unit tests for streaming behavior in message translators.

These tests verify that translators correctly handle empty strings and
end_of_stream flags in streaming responses, preventing bugs where empty
final chunks could be dropped due to falsy value checks.
"""

import pytest
from unittest.mock import MagicMock
from trustgraph.messaging.translators.retrieval import (
    GraphRagResponseTranslator,
    DocumentRagResponseTranslator,
)
from trustgraph.messaging.translators.prompt import PromptResponseTranslator
from trustgraph.messaging.translators.text_completion import TextCompletionResponseTranslator
from trustgraph.schema import (
    GraphRagResponse,
    DocumentRagResponse,
    PromptResponse,
    TextCompletionResponse,
)


class TestGraphRagResponseTranslator:
    """Test GraphRagResponseTranslator streaming behavior"""

    def test_from_pulsar_with_empty_response(self):
        """Test that empty response strings are preserved"""
        # Arrange
        translator = GraphRagResponseTranslator()
        response = GraphRagResponse(
            response="",
            end_of_stream=True,
            error=None
        )

        # Act
        result = translator.from_pulsar(response)

        # Assert - Empty string should be included in result
        assert "response" in result
        assert result["response"] == ""
        assert result["end_of_stream"] is True

    def test_from_pulsar_with_non_empty_response(self):
        """Test that non-empty responses work correctly"""
        # Arrange
        translator = GraphRagResponseTranslator()
        response = GraphRagResponse(
            response="Some text",
            end_of_stream=False,
            error=None
        )

        # Act
        result = translator.from_pulsar(response)

        # Assert
        assert result["response"] == "Some text"
        assert result["end_of_stream"] is False

    def test_from_pulsar_with_none_response(self):
        """Test that None response is handled correctly"""
        # Arrange
        translator = GraphRagResponseTranslator()
        response = GraphRagResponse(
            response=None,
            end_of_stream=True,
            error=None
        )

        # Act
        result = translator.from_pulsar(response)

        # Assert - None should not be included
        assert "response" not in result
        assert result["end_of_stream"] is True

    def test_from_response_with_completion_returns_correct_flag(self):
        """Test that from_response_with_completion returns correct is_final flag"""
        # Arrange
        translator = GraphRagResponseTranslator()

        # Test non-final chunk
        response_chunk = GraphRagResponse(
            response="chunk",
            end_of_stream=False,
            error=None
        )

        # Act
        result, is_final = translator.from_response_with_completion(response_chunk)

        # Assert
        assert is_final is False
        assert result["end_of_stream"] is False

        # Test final chunk with empty content
        final_response = GraphRagResponse(
            response="",
            end_of_stream=True,
            error=None
        )

        # Act
        result, is_final = translator.from_response_with_completion(final_response)

        # Assert
        assert is_final is True
        assert result["response"] == ""
        assert result["end_of_stream"] is True


class TestDocumentRagResponseTranslator:
    """Test DocumentRagResponseTranslator streaming behavior"""

    def test_from_pulsar_with_empty_response(self):
        """Test that empty response strings are preserved"""
        # Arrange
        translator = DocumentRagResponseTranslator()
        response = DocumentRagResponse(
            response="",
            end_of_stream=True,
            error=None
        )

        # Act
        result = translator.from_pulsar(response)

        # Assert
        assert "response" in result
        assert result["response"] == ""
        assert result["end_of_stream"] is True

    def test_from_pulsar_with_non_empty_response(self):
        """Test that non-empty responses work correctly"""
        # Arrange
        translator = DocumentRagResponseTranslator()
        response = DocumentRagResponse(
            response="Document content",
            end_of_stream=False,
            error=None
        )

        # Act
        result = translator.from_pulsar(response)

        # Assert
        assert result["response"] == "Document content"
        assert result["end_of_stream"] is False


class TestPromptResponseTranslator:
    """Test PromptResponseTranslator streaming behavior"""

    def test_from_pulsar_with_empty_text(self):
        """Test that empty text strings are preserved"""
        # Arrange
        translator = PromptResponseTranslator()
        response = PromptResponse(
            text="",
            object=None,
            end_of_stream=True,
            error=None
        )

        # Act
        result = translator.from_pulsar(response)

        # Assert
        assert "text" in result
        assert result["text"] == ""
        assert result["end_of_stream"] is True

    def test_from_pulsar_with_non_empty_text(self):
        """Test that non-empty text works correctly"""
        # Arrange
        translator = PromptResponseTranslator()
        response = PromptResponse(
            text="Some prompt response",
            object=None,
            end_of_stream=False,
            error=None
        )

        # Act
        result = translator.from_pulsar(response)

        # Assert
        assert result["text"] == "Some prompt response"
        assert result["end_of_stream"] is False

    def test_from_pulsar_with_none_text(self):
        """Test that None text is handled correctly"""
        # Arrange
        translator = PromptResponseTranslator()
        response = PromptResponse(
            text=None,
            object='{"result": "data"}',
            end_of_stream=True,
            error=None
        )

        # Act
        result = translator.from_pulsar(response)

        # Assert
        assert "text" not in result
        assert "object" in result
        assert result["end_of_stream"] is True

    def test_from_pulsar_includes_end_of_stream(self):
        """Test that end_of_stream flag is always included"""
        # Arrange
        translator = PromptResponseTranslator()

        # Test with end_of_stream=False
        response = PromptResponse(
            text="chunk",
            object=None,
            end_of_stream=False,
            error=None
        )

        # Act
        result = translator.from_pulsar(response)

        # Assert
        assert "end_of_stream" in result
        assert result["end_of_stream"] is False


class TestTextCompletionResponseTranslator:
    """Test TextCompletionResponseTranslator streaming behavior"""

    def test_from_pulsar_always_includes_response(self):
        """Test that response field is always included, even if empty"""
        # Arrange
        translator = TextCompletionResponseTranslator()
        response = TextCompletionResponse(
            response="",
            end_of_stream=True,
            error=None,
            in_token=100,
            out_token=5,
            model="test-model"
        )

        # Act
        result = translator.from_pulsar(response)

        # Assert - Response should always be present
        assert "response" in result
        assert result["response"] == ""

    def test_from_response_with_completion_with_empty_final(self):
        """Test that empty final response is handled correctly"""
        # Arrange
        translator = TextCompletionResponseTranslator()
        response = TextCompletionResponse(
            response="",
            end_of_stream=True,
            error=None,
            in_token=100,
            out_token=5,
            model="test-model"
        )

        # Act
        result, is_final = translator.from_response_with_completion(response)

        # Assert
        assert is_final is True
        assert result["response"] == ""


class TestStreamingProtocolCompliance:
    """Test that all translators follow streaming protocol conventions"""

    @pytest.mark.parametrize("translator_class,response_class,field_name", [
        (GraphRagResponseTranslator, GraphRagResponse, "response"),
        (DocumentRagResponseTranslator, DocumentRagResponse, "response"),
        (PromptResponseTranslator, PromptResponse, "text"),
        (TextCompletionResponseTranslator, TextCompletionResponse, "response"),
    ])
    def test_empty_final_chunk_preserved(self, translator_class, response_class, field_name):
        """Test that all translators preserve empty final chunks"""
        # Arrange
        translator = translator_class()
        kwargs = {
            field_name: "",
            "end_of_stream": True,
            "error": None,
        }
        response = response_class(**kwargs)

        # Act
        result = translator.from_pulsar(response)

        # Assert
        assert field_name in result, f"{translator_class.__name__} should include '{field_name}' field even when empty"
        assert result[field_name] == "", f"{translator_class.__name__} should preserve empty string"

    @pytest.mark.parametrize("translator_class,response_class,field_name", [
        (GraphRagResponseTranslator, GraphRagResponse, "response"),
        (DocumentRagResponseTranslator, DocumentRagResponse, "response"),
        (TextCompletionResponseTranslator, TextCompletionResponse, "response"),
    ])
    def test_end_of_stream_flag_included(self, translator_class, response_class, field_name):
        """Test that end_of_stream flag is included in all response translators"""
        # Arrange
        translator = translator_class()
        kwargs = {
            field_name: "test content",
            "end_of_stream": True,
            "error": None,
        }
        response = response_class(**kwargs)

        # Act
        result = translator.from_pulsar(response)

        # Assert
        assert "end_of_stream" in result, f"{translator_class.__name__} should include 'end_of_stream' flag"
        assert result["end_of_stream"] is True
