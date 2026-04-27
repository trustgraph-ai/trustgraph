import asyncio
import io
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from uuid import uuid4
from minio.error import S3Error
from trustgraph.librarian.blob_store import BlobStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_blob_store():
    """Create a BlobStore with mocked Minio client."""
    mock_minio = MagicMock()
    with patch('trustgraph.librarian.blob_store.Minio', return_value=mock_minio):
        # Prevent ensure_bucket from making network calls during init
        with patch('trustgraph.librarian.blob_store.BlobStore.ensure_bucket'):
            store = BlobStore(
                endpoint="localhost:9000",
                access_key="access",
                secret_key="secret",
                bucket_name="test-bucket"
            )
    return store, mock_minio

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_add_success_no_retry():
    store, mock_minio = _make_blob_store()
    object_id = uuid4()
    
    await store.add(object_id, b"data", "text/plain")

    mock_minio.put_object.assert_called_once()

@pytest.mark.asyncio
async def test_retry_recovery_on_transient_failure():
    store, mock_minio = _make_blob_store()
    store.base_delay = 0  # Disable delay for fast tests
    
    # Fail twice, succeed third time
    mock_minio.put_object.side_effect = [
        Exception("Error 1"),
        Exception("Error 2"),
        MagicMock()
    ]

    await store.add(uuid4(), b"data", "text/plain")
    
    assert mock_minio.put_object.call_count == 3

@pytest.mark.asyncio
async def test_retry_exhaustion_after_8_attempts():
    store, mock_minio = _make_blob_store()
    store.base_delay = 0
    
    # Permanent failure
    mock_minio.put_object.side_effect = Exception("Permanent failure")

    with pytest.raises(Exception, match="Permanent failure"):
        await store.add(uuid4(), b"data", "text/plain")
    
    # Author requirement: exactly 8 attempts
    assert mock_minio.put_object.call_count == 8

@pytest.mark.asyncio
async def test_s3_error_triggers_retry():
    store, mock_minio = _make_blob_store()
    store.base_delay = 0
    
    # Mock S3Error
    s3_err = S3Error("code", "msg", "res", "req", "host", None)
    mock_minio.get_object.side_effect = [s3_err, MagicMock()]

    await store.get(uuid4())
    
    assert mock_minio.get_object.call_count == 2

@pytest.mark.asyncio
async def test_exponential_backoff_delays():
    store, mock_minio = _make_blob_store()
    # Use real base_delay to check math
    store.base_delay = 0.25
    
    # Correct method name is stat_object, not get_size
    mock_minio.stat_object = MagicMock(side_effect=Exception("Wait"))

    with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
        with pytest.raises(Exception):
            await store.get_size(uuid4())
        
        # Should have 7 sleep calls for 8 attempts
        assert mock_sleep.call_count == 7
        
        # Check actual sleep durations: 0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0
        sleep_args = [call[0][0] for call in mock_sleep.call_args_list]
        assert sleep_args == [0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0]

@pytest.mark.asyncio
async def test_runs_in_executor():
    """Verify that synchronous Minio calls are offloaded to an executor."""
    store, mock_minio = _make_blob_store()
    
    # Mock response object with .read() method
    mock_response = MagicMock()
    mock_response.read.return_value = b"result"

    with patch('asyncio.get_event_loop') as mock_loop:
        mock_loop_instance = MagicMock()
        mock_loop.return_value = mock_loop_instance
        mock_loop_instance.run_in_executor = AsyncMock(return_value=mock_response)

        await store.get(uuid4())
        
        mock_loop_instance.run_in_executor.assert_called_once()
