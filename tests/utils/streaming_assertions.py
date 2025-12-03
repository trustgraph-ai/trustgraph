"""
Streaming test assertion helpers

Provides reusable assertion functions for validating streaming behavior
across different TrustGraph services.
"""

from typing import List, Dict, Any, Optional


def assert_streaming_chunks_valid(chunks: List[Any], min_chunks: int = 1):
    """
    Assert that streaming chunks are valid and non-empty.

    Args:
        chunks: List of streaming chunks
        min_chunks: Minimum number of expected chunks
    """
    assert len(chunks) >= min_chunks, f"Expected at least {min_chunks} chunks, got {len(chunks)}"
    assert all(chunk is not None for chunk in chunks), "All chunks should be non-None"


def assert_streaming_sequence(chunks: List[Dict[str, Any]], expected_sequence: List[str], key: str = "chunk_type"):
    """
    Assert that streaming chunks follow an expected sequence.

    Args:
        chunks: List of chunk dictionaries
        expected_sequence: Expected sequence of chunk types/values
        key: Dictionary key to check (default: "chunk_type")
    """
    actual_sequence = [chunk.get(key) for chunk in chunks if key in chunk]
    assert actual_sequence == expected_sequence, \
        f"Expected sequence {expected_sequence}, got {actual_sequence}"


def assert_agent_streaming_chunks(chunks: List[Dict[str, Any]]):
    """
    Assert that agent streaming chunks have valid structure.

    Validates:
    - All chunks have chunk_type field
    - All chunks have content field
    - All chunks have end_of_message field
    - All chunks have end_of_dialog field
    - Last chunk has end_of_dialog=True

    Args:
        chunks: List of agent streaming chunk dictionaries
    """
    assert len(chunks) > 0, "Expected at least one chunk"

    for i, chunk in enumerate(chunks):
        assert "chunk_type" in chunk, f"Chunk {i} missing chunk_type"
        assert "content" in chunk, f"Chunk {i} missing content"
        assert "end_of_message" in chunk, f"Chunk {i} missing end_of_message"
        assert "end_of_dialog" in chunk, f"Chunk {i} missing end_of_dialog"

        # Validate chunk_type values
        valid_types = ["thought", "action", "observation", "final-answer"]
        assert chunk["chunk_type"] in valid_types, \
            f"Invalid chunk_type '{chunk['chunk_type']}' at index {i}"

    # Last chunk should signal end of dialog
    assert chunks[-1]["end_of_dialog"] is True, \
        "Last chunk should have end_of_dialog=True"


def assert_rag_streaming_chunks(chunks: List[Dict[str, Any]]):
    """
    Assert that RAG streaming chunks have valid structure.

    Validates:
    - All chunks except last have chunk field
    - All chunks have end_of_stream field
    - Last chunk has end_of_stream=True
    - Last chunk may have response field with complete text

    Args:
        chunks: List of RAG streaming chunk dictionaries
    """
    assert len(chunks) > 0, "Expected at least one chunk"

    for i, chunk in enumerate(chunks):
        assert "end_of_stream" in chunk, f"Chunk {i} missing end_of_stream"

        if i < len(chunks) - 1:
            # Non-final chunks should have chunk content and end_of_stream=False
            assert "chunk" in chunk, f"Chunk {i} missing chunk field"
            assert chunk["end_of_stream"] is False, \
                f"Non-final chunk {i} should have end_of_stream=False"
        else:
            # Final chunk should have end_of_stream=True
            assert chunk["end_of_stream"] is True, \
                "Last chunk should have end_of_stream=True"


def assert_streaming_completion(chunks: List[Dict[str, Any]], expected_complete_flag: str = "end_of_stream"):
    """
    Assert that streaming completed properly.

    Args:
        chunks: List of streaming chunk dictionaries
        expected_complete_flag: Name of the completion flag field
    """
    assert len(chunks) > 0, "Expected at least one chunk"

    # Check that all but last chunk have completion flag = False
    for i, chunk in enumerate(chunks[:-1]):
        assert chunk.get(expected_complete_flag) is False, \
            f"Non-final chunk {i} should have {expected_complete_flag}=False"

    # Check that last chunk has completion flag = True
    assert chunks[-1].get(expected_complete_flag) is True, \
        f"Final chunk should have {expected_complete_flag}=True"


def assert_streaming_content_matches(chunks: List, expected_content: str, content_key: str = "chunk"):
    """
    Assert that concatenated streaming chunks match expected content.

    Args:
        chunks: List of streaming chunks (strings or dicts)
        expected_content: Expected complete content after concatenation
        content_key: Dictionary key for content (used if chunks are dicts)
    """
    if isinstance(chunks[0], dict):
        # Extract content from chunk dictionaries
        content_chunks = [
            chunk.get(content_key, "")
            for chunk in chunks
            if chunk.get(content_key) is not None
        ]
        actual_content = "".join(content_chunks)
    else:
        # Chunks are already strings
        actual_content = "".join(chunks)

    assert actual_content == expected_content, \
        f"Expected content '{expected_content}', got '{actual_content}'"


def assert_no_empty_chunks(chunks: List[Dict[str, Any]], content_key: str = "content"):
    """
    Assert that no chunks have empty content (except final chunk if it's completion marker).

    Args:
        chunks: List of streaming chunk dictionaries
        content_key: Dictionary key for content
    """
    for i, chunk in enumerate(chunks[:-1]):
        content = chunk.get(content_key)
        assert content is not None and len(content) > 0, \
            f"Chunk {i} has empty content"


def assert_streaming_error_handled(chunks: List[Dict[str, Any]], error_flag: str = "error"):
    """
    Assert that streaming error was properly signaled.

    Args:
        chunks: List of streaming chunk dictionaries
        error_flag: Name of the error flag field
    """
    # Check that at least one chunk has error flag
    has_error = any(chunk.get(error_flag) is not None for chunk in chunks)
    assert has_error, "Expected error flag in at least one chunk"

    # If last chunk has error, should also have completion flag
    if chunks[-1].get(error_flag):
        # Check for completion flags (either end_of_stream or end_of_dialog)
        completion_flags = ["end_of_stream", "end_of_dialog"]
        has_completion = any(chunks[-1].get(flag) is True for flag in completion_flags)
        assert has_completion, \
            "Error chunk should have completion flag set to True"


def assert_chunk_types_valid(chunks: List[Dict[str, Any]], valid_types: List[str], type_key: str = "chunk_type"):
    """
    Assert that all chunk types are from a valid set.

    Args:
        chunks: List of streaming chunk dictionaries
        valid_types: List of valid chunk type values
        type_key: Dictionary key for chunk type
    """
    for i, chunk in enumerate(chunks):
        chunk_type = chunk.get(type_key)
        assert chunk_type in valid_types, \
            f"Chunk {i} has invalid type '{chunk_type}', expected one of {valid_types}"


def assert_streaming_latency_acceptable(chunk_timestamps: List[float], max_gap_seconds: float = 5.0):
    """
    Assert that streaming latency between chunks is acceptable.

    Args:
        chunk_timestamps: List of timestamps when chunks were received
        max_gap_seconds: Maximum acceptable gap between chunks in seconds
    """
    assert len(chunk_timestamps) > 1, "Need at least 2 timestamps to check latency"

    for i in range(1, len(chunk_timestamps)):
        gap = chunk_timestamps[i] - chunk_timestamps[i-1]
        assert gap <= max_gap_seconds, \
            f"Gap between chunks {i-1} and {i} is {gap:.2f}s, exceeds max {max_gap_seconds}s"


def assert_callback_invoked(mock_callback, min_calls: int = 1):
    """
    Assert that a streaming callback was invoked minimum number of times.

    Args:
        mock_callback: AsyncMock callback object
        min_calls: Minimum number of expected calls
    """
    assert mock_callback.call_count >= min_calls, \
        f"Expected callback to be called at least {min_calls} times, was called {mock_callback.call_count} times"
