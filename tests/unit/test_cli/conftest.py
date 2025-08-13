"""
Shared fixtures for CLI unit tests.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_websocket_connection():
    """Mock WebSocket connection for CLI tools."""
    mock_ws = AsyncMock()
    mock_ws.send = AsyncMock()
    mock_ws.recv = AsyncMock()
    mock_ws.close = AsyncMock()
    return mock_ws


@pytest.fixture
def mock_pulsar_client():
    """Mock Pulsar client for CLI tools that use messaging."""
    mock_client = MagicMock()
    mock_client.create_consumer = MagicMock()
    mock_client.create_producer = MagicMock()
    mock_client.close = MagicMock()
    return mock_client


@pytest.fixture
def sample_metadata():
    """Sample metadata structure used across CLI tools."""
    return {
        "id": "test-doc-123",
        "metadata": [],
        "user": "test-user",
        "collection": "test-collection"
    }