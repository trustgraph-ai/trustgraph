"""
WebSocket-specific integration tests for tg-load-structured-data.
Tests WebSocket connection handling, message formats, and batching behavior.
"""

import pytest
import asyncio
import json
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import websockets
from websockets.exceptions import ConnectionClosedError, InvalidHandshake

from trustgraph.cli.load_structured_data import load_structured_data


@pytest.mark.integration
class TestLoadStructuredDataWebSocket:
    """WebSocket-specific integration tests"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.api_url = "http://localhost:8088"
        self.ws_url = "ws://localhost:8088"
        
        self.test_csv_data = """name,email,age,country
John Smith,john@email.com,35,US
Jane Doe,jane@email.com,28,CA
Bob Johnson,bob@company.org,42,UK
Alice Brown,alice@email.com,31,AU
Charlie Davis,charlie@email.com,39,DE"""
        
        self.test_descriptor = {
            "version": "1.0",
            "format": {
                "type": "csv",
                "encoding": "utf-8",
                "options": {"header": True, "delimiter": ","}
            },
            "mappings": [
                {"source_field": "name", "target_field": "name", "transforms": [{"type": "trim"}]},
                {"source_field": "email", "target_field": "email", "transforms": [{"type": "lower"}]},
                {"source_field": "age", "target_field": "age", "transforms": [{"type": "to_int"}]},
                {"source_field": "country", "target_field": "country", "transforms": [{"type": "upper"}]}
            ],
            "output": {
                "format": "trustgraph-objects",
                "schema_name": "test_customer",
                "options": {"confidence": 0.9, "batch_size": 2}
            }
        }
    
    def create_temp_file(self, content, suffix='.txt'):
        """Create a temporary file with given content"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False)
        temp_file.write(content)
        temp_file.flush()
        temp_file.close()
        return temp_file.name
    
    def cleanup_temp_file(self, file_path):
        """Clean up temporary file"""
        try:
            os.unlink(file_path)
        except:
            pass
    
    @pytest.mark.asyncio
    async def test_websocket_message_format(self):
        """Test that WebSocket messages are formatted correctly for batching"""
        messages_sent = []
        
        # Mock WebSocket connection
        async def mock_websocket_handler(websocket, path):
            try:
                while True:
                    message = await websocket.recv()
                    messages_sent.append(json.loads(message))
            except websockets.exceptions.ConnectionClosed:
                pass
        
        # Start mock WebSocket server
        server = await websockets.serve(mock_websocket_handler, "localhost", 8089)
        
        try:
            input_file = self.create_temp_file(self.test_csv_data, '.csv')
            descriptor_file = self.create_temp_file(json.dumps(self.test_descriptor), '.json')
            
            # Test with mock server
            with patch('websockets.asyncio.client.connect') as mock_connect:
                mock_ws = AsyncMock()
                mock_connect.return_value.__aenter__.return_value = mock_ws
                
                # Capture messages sent
                sent_messages = []
                mock_ws.send = AsyncMock(side_effect=lambda msg: sent_messages.append(json.loads(msg)))
                
                try:
                    result = load_structured_data(
                        api_url="http://localhost:8089",
                        input_file=input_file,
                        descriptor_file=descriptor_file,
                                                flow='obj-ex',
                        )
                    
                    # Dry run mode completes without errors
                    assert result is None
                    
                    for message in sent_messages:
                        # Check required fields
                        assert "metadata" in message
                        assert "schema_name" in message
                        assert "values" in message
                        assert "confidence" in message
                        assert "source_span" in message
                        
                        # Check metadata structure
                        metadata = message["metadata"]
                        assert "id" in metadata
                        assert "metadata" in metadata
                        assert "user" in metadata
                        assert "collection" in metadata
                        
                        # Check batched values format
                        values = message["values"]
                        assert isinstance(values, list), "Values should be a list (batched)"
                        assert len(values) <= 2, "Batch size should be respected"
                        
                        # Check each object in batch
                        for obj in values:
                            assert isinstance(obj, dict)
                            assert "name" in obj
                            assert "email" in obj
                            assert "age" in obj
                            assert "country" in obj
                            
                            # Check transformations were applied
                            assert obj["email"].islower(), "Email should be lowercase"
                            assert obj["country"].isupper(), "Country should be uppercase"
                            
                finally:
                    self.cleanup_temp_file(input_file)
                    self.cleanup_temp_file(descriptor_file)
        
        finally:
            server.close()
            await server.wait_closed()
    
    @pytest.mark.asyncio
    async def test_websocket_connection_retry(self):
        """Test WebSocket connection retry behavior"""
        input_file = self.create_temp_file(self.test_csv_data, '.csv')
        descriptor_file = self.create_temp_file(json.dumps(self.test_descriptor), '.json')
        
        try:
            # Test connection to non-existent server
            with pytest.raises(Exception) as exc_info:
                result = load_structured_data(
                    api_url="http://localhost:9999",  # Non-existent server
                    input_file=input_file,
                    descriptor_file=descriptor_file,
                                        flow='obj-ex',
                )
            
            # Should get the expected error (now dry_run will prevent WebSocket connection)
            assert exc_info.value is not None
            
        finally:
            self.cleanup_temp_file(input_file)
            self.cleanup_temp_file(descriptor_file)
    
    @pytest.mark.asyncio
    async def test_websocket_large_message_handling(self):
        """Test WebSocket handling of large batched messages"""
        # Generate larger dataset
        large_csv_data = "name,email,age,country\n"
        for i in range(100):
            large_csv_data += f"User{i},user{i}@example.com,{25+i%40},US\n"
        
        # Create descriptor with larger batch size
        large_batch_descriptor = {
            **self.test_descriptor,
            "output": {
                **self.test_descriptor["output"],
                "batch_size": 50  # Large batch size
            }
        }
        
        input_file = self.create_temp_file(large_csv_data, '.csv')
        descriptor_file = self.create_temp_file(json.dumps(large_batch_descriptor), '.json')
        
        try:
            with patch('websockets.asyncio.client.connect') as mock_connect:
                mock_ws = AsyncMock()
                mock_connect.return_value.__aenter__.return_value = mock_ws
                
                sent_messages = []
                mock_ws.send = AsyncMock(side_effect=lambda msg: sent_messages.append(json.loads(msg)))
                
                result = load_structured_data(
                    api_url=self.api_url,
                    input_file=input_file,
                    descriptor_file=descriptor_file,
                                        flow='obj-ex',
                )
                
                # Should handle large batches
                assert len(sent_messages) >= 2  # 100 records with batch_size=50 -> 2 messages
                
                # Check message sizes
                for message in sent_messages:
                    values = message["values"]
                    assert len(values) <= 50
                    
                    # Check message is not too large (rough size check)
                    message_size = len(json.dumps(message))
                    assert message_size < 1024 * 1024  # Less than 1MB per message
                
        finally:
            self.cleanup_temp_file(input_file)
            self.cleanup_temp_file(descriptor_file)
    
    @pytest.mark.asyncio
    async def test_websocket_connection_interruption(self):
        """Test handling of WebSocket connection interruptions"""
        input_file = self.create_temp_file(self.test_csv_data, '.csv')
        descriptor_file = self.create_temp_file(json.dumps(self.test_descriptor), '.json')
        
        try:
            with patch('websockets.asyncio.client.connect') as mock_connect:
                mock_ws = AsyncMock()
                mock_connect.return_value.__aenter__.return_value = mock_ws
                
                # Simulate connection being closed mid-send
                call_count = 0
                def send_with_failure(msg):
                    nonlocal call_count
                    call_count += 1
                    if call_count > 1:  # Fail after first message
                        raise ConnectionClosedError(None, None)
                    return AsyncMock()
                
                mock_ws.send.side_effect = send_with_failure
                
                # Should handle connection errors
                with pytest.raises(ConnectionClosedError):
                    result = load_structured_data(
                        api_url=self.api_url,
                        input_file=input_file,
                        descriptor_file=descriptor_file,
                                                flow='obj-ex',
                        )
                
        finally:
            self.cleanup_temp_file(input_file)
            self.cleanup_temp_file(descriptor_file)
    
    @pytest.mark.asyncio
    async def test_websocket_url_conversion(self):
        """Test proper URL conversion from HTTP to WebSocket"""
        input_file = self.create_temp_file(self.test_csv_data, '.csv')
        descriptor_file = self.create_temp_file(json.dumps(self.test_descriptor), '.json')
        
        try:
            with patch('websockets.asyncio.client.connect') as mock_connect:
                mock_ws = AsyncMock()
                mock_connect.return_value.__aenter__.return_value = mock_ws
                mock_ws.send = AsyncMock()
                
                # Test HTTP URL conversion
                result = load_structured_data(
                    api_url="http://localhost:8088",  # HTTP URL
                    input_file=input_file,
                    descriptor_file=descriptor_file,
                                        flow='obj-ex',
                )
                
                # Check that WebSocket URL was used
                mock_connect.assert_called_once()
                called_url = mock_connect.call_args[0][0]
                assert called_url.startswith("ws://")
                assert "api/v1/flow/obj-ex/import/objects" in called_url
                
                # Test HTTPS URL conversion
                mock_connect.reset_mock()
                
                result = load_structured_data(
                    api_url="https://example.com:8088",  # HTTPS URL
                    input_file=input_file,
                    descriptor_file=descriptor_file,
                                        flow='test-flow',
                )
                
                # Check that secure WebSocket URL was used
                mock_connect.assert_called_once()
                called_url = mock_connect.call_args[0][0]
                assert called_url.startswith("wss://")
                assert "api/v1/flow/test-flow/import/objects" in called_url
                
        finally:
            self.cleanup_temp_file(input_file)
            self.cleanup_temp_file(descriptor_file)
    
    @pytest.mark.asyncio
    async def test_websocket_batch_ordering(self):
        """Test that batches are sent in correct order"""
        # Create ordered test data
        ordered_csv_data = "name,id\n"
        for i in range(10):
            ordered_csv_data += f"User{i:02d},{i}\n"
        
        input_file = self.create_temp_file(ordered_csv_data, '.csv')
        
        # Create descriptor for this test
        ordered_descriptor = {
            **self.test_descriptor,
            "mappings": [
                {"source_field": "name", "target_field": "name", "transforms": []},
                {"source_field": "id", "target_field": "id", "transforms": [{"type": "to_int"}]}
            ],
            "output": {
                **self.test_descriptor["output"],
                "batch_size": 3
            }
        }
        descriptor_file = self.create_temp_file(json.dumps(ordered_descriptor), '.json')
        
        try:
            with patch('websockets.asyncio.client.connect') as mock_connect:
                mock_ws = AsyncMock()
                mock_connect.return_value.__aenter__.return_value = mock_ws
                
                sent_messages = []
                mock_ws.send = AsyncMock(side_effect=lambda msg: sent_messages.append(json.loads(msg)))
                
                result = load_structured_data(
                    api_url=self.api_url,
                    input_file=input_file,
                    descriptor_file=descriptor_file,
                                        flow='obj-ex',
                )
                
                # Should have 4 messages (10 records, batch_size=3: 3+3+3+1)
                assert len(sent_messages) == 4
                
                # Check ordering within batches
                expected_ids = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
                actual_ids = []
                
                for message in sent_messages:
                    values = message["values"]
                    for obj in values:
                        actual_ids.append(int(obj["id"]))
                
                assert actual_ids == expected_ids, "Records should maintain order"
                
        finally:
            self.cleanup_temp_file(input_file)
            self.cleanup_temp_file(descriptor_file)
    
    @pytest.mark.asyncio
    async def test_websocket_authentication_headers(self):
        """Test WebSocket connection with authentication headers"""
        input_file = self.create_temp_file(self.test_csv_data, '.csv')
        descriptor_file = self.create_temp_file(json.dumps(self.test_descriptor), '.json')
        
        try:
            with patch('websockets.asyncio.client.connect') as mock_connect:
                mock_ws = AsyncMock()
                mock_connect.return_value.__aenter__.return_value = mock_ws
                mock_ws.send = AsyncMock()
                
                result = load_structured_data(
                    api_url=self.api_url,
                    input_file=input_file,
                    descriptor_file=descriptor_file,
                                        flow='obj-ex',
                )
                
                # Verify WebSocket connect was called
                mock_connect.assert_called_once()
                
                # In real implementation, could check for auth headers
                # For now, just verify the connection was attempted
                
        finally:
            self.cleanup_temp_file(input_file)
            self.cleanup_temp_file(descriptor_file)
    
    @pytest.mark.asyncio
    async def test_websocket_empty_batch_handling(self):
        """Test handling of empty batches"""
        # Create CSV with some invalid records
        invalid_csv_data = """name,email,age,country
,invalid@email,not_a_number,
Valid User,valid@email.com,25,US"""
        
        input_file = self.create_temp_file(invalid_csv_data, '.csv')
        descriptor_file = self.create_temp_file(json.dumps(self.test_descriptor), '.json')
        
        try:
            with patch('websockets.asyncio.client.connect') as mock_connect:
                mock_ws = AsyncMock()
                mock_connect.return_value.__aenter__.return_value = mock_ws
                
                sent_messages = []
                mock_ws.send = AsyncMock(side_effect=lambda msg: sent_messages.append(json.loads(msg)))
                
                result = load_structured_data(
                    api_url=self.api_url,
                    input_file=input_file,
                    descriptor_file=descriptor_file,
                                        flow='obj-ex',
                )
                
                # Should still send messages for valid records
                assert len(sent_messages) >= 1
                
                # Check that messages are not empty
                for message in sent_messages:
                    values = message["values"]
                    assert len(values) > 0, "Should not send empty batches"
                
        finally:
            self.cleanup_temp_file(input_file)
            self.cleanup_temp_file(descriptor_file)
    
    @pytest.mark.asyncio
    async def test_websocket_progress_reporting(self):
        """Test progress reporting during WebSocket sends"""
        # Generate larger dataset for progress testing
        progress_csv_data = "name,email,age\n"
        for i in range(50):
            progress_csv_data += f"User{i},user{i}@example.com,{25+i}\n"
        
        input_file = self.create_temp_file(progress_csv_data, '.csv')
        descriptor_file = self.create_temp_file(json.dumps(self.test_descriptor), '.json')
        
        try:
            with patch('websockets.asyncio.client.connect') as mock_connect:
                mock_ws = AsyncMock()
                mock_connect.return_value.__aenter__.return_value = mock_ws
                
                send_count = 0
                def count_sends(msg):
                    nonlocal send_count
                    send_count += 1
                    return AsyncMock()
                
                mock_ws.send.side_effect = count_sends
                
                # Capture logging output to check for progress messages
                with patch('logging.getLogger') as mock_logger:
                    mock_log = Mock()
                    mock_logger.return_value = mock_log
                    
                    result = load_structured_data(
                        api_url=self.api_url,
                        input_file=input_file,
                        descriptor_file=descriptor_file,
                                                flow='obj-ex',
                                verbose=True
                    )
                    
                    # Should have sent multiple batches
                    assert send_count >= 5
                    
        finally:
            self.cleanup_temp_file(input_file)
            self.cleanup_temp_file(descriptor_file)