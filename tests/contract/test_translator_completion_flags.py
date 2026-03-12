"""
Contract tests for message translator completion flag behavior.

These tests verify that translators correctly compute the is_final flag
based on message fields like end_of_stream and end_of_dialog.
"""

import pytest

from trustgraph.schema import (
    GraphRagResponse, DocumentRagResponse, AgentResponse, Error
)
from trustgraph.messaging import TranslatorRegistry


@pytest.mark.contract
class TestRAGTranslatorCompletionFlags:
    """Contract tests for RAG response translator completion flags"""

    def test_graph_rag_translator_is_final_with_end_of_session_true(self):
        """
        Test that GraphRagResponseTranslator returns is_final=True
        when end_of_session=True.
        """
        # Arrange
        translator = TranslatorRegistry.get_response_translator("graph-rag")
        response = GraphRagResponse(
            response="A small domesticated mammal.",
            message_type="chunk",
            end_of_stream=True,
            end_of_session=True,
            error=None
        )

        # Act
        response_dict, is_final = translator.from_response_with_completion(response)

        # Assert
        assert is_final is True, "is_final must be True when end_of_session=True"
        assert response_dict["response"] == "A small domesticated mammal."
        assert response_dict["end_of_session"] is True
        assert response_dict["message_type"] == "chunk"

    def test_graph_rag_translator_is_final_with_end_of_session_false(self):
        """
        Test that GraphRagResponseTranslator returns is_final=False
        when end_of_session=False (even if end_of_stream=True).
        """
        # Arrange
        translator = TranslatorRegistry.get_response_translator("graph-rag")
        response = GraphRagResponse(
            response="Chunk 1",
            message_type="chunk",
            end_of_stream=False,
            end_of_session=False,
            error=None
        )

        # Act
        response_dict, is_final = translator.from_response_with_completion(response)

        # Assert
        assert is_final is False, "is_final must be False when end_of_session=False"
        assert response_dict["response"] == "Chunk 1"
        assert response_dict["end_of_session"] is False

    def test_graph_rag_translator_provenance_message(self):
        """
        Test that GraphRagResponseTranslator handles provenance messages.
        """
        # Arrange
        translator = TranslatorRegistry.get_response_translator("graph-rag")
        response = GraphRagResponse(
            response="",
            message_type="explain",
            explain_id="urn:trustgraph:session:abc123",
            end_of_stream=False,
            end_of_session=False,
            error=None
        )

        # Act
        response_dict, is_final = translator.from_response_with_completion(response)

        # Assert
        assert is_final is False
        assert response_dict["message_type"] == "explain"
        assert response_dict["explain_id"] == "urn:trustgraph:session:abc123"

    def test_graph_rag_translator_end_of_stream_not_final(self):
        """
        Test that end_of_stream=True alone does NOT make is_final=True.
        The session continues with provenance messages after LLM stream completes.
        """
        # Arrange
        translator = TranslatorRegistry.get_response_translator("graph-rag")
        response = GraphRagResponse(
            response="Final chunk",
            message_type="chunk",
            end_of_stream=True,
            end_of_session=False,  # Session continues with provenance
            error=None
        )

        # Act
        response_dict, is_final = translator.from_response_with_completion(response)

        # Assert
        assert is_final is False, "end_of_stream=True should NOT make is_final=True"
        assert response_dict["end_of_stream"] is True
        assert response_dict["end_of_session"] is False

    def test_document_rag_translator_is_final_with_end_of_session_true(self):
        """
        Test that DocumentRagResponseTranslator returns is_final=True
        when end_of_session=True.
        """
        # Arrange
        translator = TranslatorRegistry.get_response_translator("document-rag")
        response = DocumentRagResponse(
            response="A document about cats.",
            end_of_stream=True,
            end_of_session=True,
            error=None
        )

        # Act
        response_dict, is_final = translator.from_response_with_completion(response)

        # Assert
        assert is_final is True, "is_final must be True when end_of_session=True"
        assert response_dict["response"] == "A document about cats."
        assert response_dict["end_of_session"] is True

    def test_document_rag_translator_end_of_stream_not_final(self):
        """
        Test that end_of_stream=True alone does NOT make is_final=True.
        The session continues with provenance messages after LLM stream completes.
        """
        # Arrange
        translator = TranslatorRegistry.get_response_translator("document-rag")
        response = DocumentRagResponse(
            response="Final chunk",
            end_of_stream=True,
            end_of_session=False,  # Session continues with provenance
            error=None
        )

        # Act
        response_dict, is_final = translator.from_response_with_completion(response)

        # Assert
        assert is_final is False, "end_of_stream=True should NOT make is_final=True"
        assert response_dict["end_of_stream"] is True
        assert response_dict["end_of_session"] is False

    def test_document_rag_translator_is_final_with_end_of_stream_false(self):
        """
        Test that DocumentRagResponseTranslator returns is_final=False
        when end_of_stream=False.
        """
        # Arrange
        translator = TranslatorRegistry.get_response_translator("document-rag")
        response = DocumentRagResponse(
            response="Chunk 1",
            end_of_stream=False,
            error=None
        )

        # Act
        response_dict, is_final = translator.from_response_with_completion(response)

        # Assert
        assert is_final is False, "is_final must be False when end_of_stream=False"
        assert response_dict["response"] == "Chunk 1"
        assert response_dict["end_of_stream"] is False


@pytest.mark.contract
class TestAgentTranslatorCompletionFlags:
    """Contract tests for Agent response translator completion flags"""

    def test_agent_translator_is_final_with_end_of_dialog_true(self):
        """
        Test that AgentResponseTranslator returns is_final=True
        when end_of_dialog=True.
        """
        # Arrange
        translator = TranslatorRegistry.get_response_translator("agent")
        response = AgentResponse(
            answer="4",
            error=None,
            thought=None,
            observation=None,
            end_of_message=True,
            end_of_dialog=True
        )

        # Act
        response_dict, is_final = translator.from_response_with_completion(response)

        # Assert
        assert is_final is True, "is_final must be True when end_of_dialog=True"
        assert response_dict["answer"] == "4"
        assert response_dict["end_of_dialog"] is True

    def test_agent_translator_is_final_with_end_of_dialog_false(self):
        """
        Test that AgentResponseTranslator returns is_final=False
        when end_of_dialog=False.
        """
        # Arrange
        translator = TranslatorRegistry.get_response_translator("agent")
        response = AgentResponse(
            answer=None,
            error=None,
            thought="I need to solve this.",
            observation=None,
            end_of_message=True,
            end_of_dialog=False
        )

        # Act
        response_dict, is_final = translator.from_response_with_completion(response)

        # Assert
        assert is_final is False, "is_final must be False when end_of_dialog=False"
        assert response_dict["thought"] == "I need to solve this."
        assert response_dict["end_of_dialog"] is False

    def test_agent_translator_is_final_fallback_with_answer(self):
        """
        Test that AgentResponseTranslator returns is_final=True
        when answer is present (fallback for legacy responses).
        """
        # Arrange
        translator = TranslatorRegistry.get_response_translator("agent")
        # Legacy response without end_of_dialog flag
        response = AgentResponse(
            answer="4",
            error=None,
            thought=None,
            observation=None
        )

        # Act
        response_dict, is_final = translator.from_response_with_completion(response)

        # Assert
        assert is_final is True, "is_final must be True when answer is present (legacy fallback)"
        assert response_dict["answer"] == "4"

    def test_agent_translator_intermediate_message_is_not_final(self):
        """
        Test that intermediate messages (thought/observation) return is_final=False.
        """
        # Arrange
        translator = TranslatorRegistry.get_response_translator("agent")

        # Test thought message
        thought_response = AgentResponse(
            answer=None,
            error=None,
            thought="Processing...",
            observation=None,
            end_of_message=True,
            end_of_dialog=False
        )

        # Act
        thought_dict, thought_is_final = translator.from_response_with_completion(thought_response)

        # Assert
        assert thought_is_final is False, "Thought message must not be final"

        # Test observation message
        observation_response = AgentResponse(
            answer=None,
            error=None,
            thought=None,
            observation="Result found",
            end_of_message=True,
            end_of_dialog=False
        )

        # Act
        obs_dict, obs_is_final = translator.from_response_with_completion(observation_response)

        # Assert
        assert obs_is_final is False, "Observation message must not be final"

    def test_agent_translator_streaming_format_with_end_of_dialog(self):
        """
        Test that streaming format messages use end_of_dialog for is_final.
        """
        # Arrange
        translator = TranslatorRegistry.get_response_translator("agent")

        # Streaming format with end_of_dialog=True
        response = AgentResponse(
            chunk_type="answer",
            content="",
            end_of_message=True,
            end_of_dialog=True,
            answer=None,
            error=None,
            thought=None,
            observation=None
        )

        # Act
        response_dict, is_final = translator.from_response_with_completion(response)

        # Assert
        assert is_final is True, "Streaming format must use end_of_dialog for is_final"
        assert response_dict["end_of_dialog"] is True
