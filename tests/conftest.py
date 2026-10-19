"""
Global pytest configuration for all tests.

This conftest.py applies to all test directories.
"""

import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(scope="session", autouse=True)
def mock_loki_http():
    """
    Prevent Loki HTTP pushes during tests by mocking requests.Session.post
    on the _LokiHandler's session.
    """
    with patch(
        "trustgraph.base.logging.requests.Session",
        return_value=MagicMock(),
    ):
        yield
