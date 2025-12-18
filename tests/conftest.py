"""
Global pytest configuration for all tests.

This conftest.py applies to all test directories.
"""

import pytest
from unittest.mock import MagicMock


@pytest.fixture(scope="session", autouse=True)
def mock_loki_handler(session_mocker=None):
    """
    Mock LokiHandler to prevent connection attempts during tests.

    This fixture runs once per test session and prevents the logging
    module from trying to connect to a Loki server that doesn't exist
    in the test environment.
    """
    # Try to import logging_loki and mock it if available
    try:
        import logging_loki
        # Create a mock LokiHandler that does nothing
        original_loki_handler = logging_loki.LokiHandler

        class MockLokiHandler:
            """Mock LokiHandler that doesn't make network calls."""
            def __init__(self, *args, **kwargs):
                pass

            def emit(self, record):
                pass

            def flush(self):
                pass

            def close(self):
                pass

        # Replace the real LokiHandler with our mock
        logging_loki.LokiHandler = MockLokiHandler

        yield

        # Restore original after tests
        logging_loki.LokiHandler = original_loki_handler

    except ImportError:
        # If logging_loki isn't installed, no need to mock
        yield
