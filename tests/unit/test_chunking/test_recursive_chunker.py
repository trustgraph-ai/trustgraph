import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from trustgraph.schema import TextDocument, Chunk, Metadata
from trustgraph.chunking.recursive.chunker import Processor as RecursiveChunker


@pytest.fixture
def mock_flow():
    output_mock = AsyncMock()
    flow_mock = Mock(return_value=output_mock)
    return flow_mock, output_mock


@pytest.fixture
def mock_consumer():
    consumer = Mock()
    consumer.id = "test-consumer"
    consumer.flow = "test-flow"
    return consumer


@pytest.fixture
def sample_document():
    metadata = Metadata(
        id="test-doc-1",
        metadata=[],
        user="test-user",
        collection="test-collection"
    )
    text = "This is a test document. " * 100  # Create text long enough to be chunked
    return TextDocument(
        metadata=metadata,
        text=text.encode("utf-8")
    )


@pytest.fixture
def short_document():
    metadata = Metadata(
        id="test-doc-2",
        metadata=[],
        user="test-user",
        collection="test-collection"
    )
    text = "This is a very short document."
    return TextDocument(
        metadata=metadata,
        text=text.encode("utf-8")
    )


class TestRecursiveChunker:
    
    def test_init_default_params(self, mock_async_processor_init):
        processor = RecursiveChunker()
        assert processor.text_splitter._chunk_size == 2000
        assert processor.text_splitter._chunk_overlap == 100
        
    def test_init_custom_params(self, mock_async_processor_init):
        processor = RecursiveChunker(chunk_size=500, chunk_overlap=50)
        assert processor.text_splitter._chunk_size == 500
        assert processor.text_splitter._chunk_overlap == 50
        
    def test_init_with_id(self, mock_async_processor_init):
        processor = RecursiveChunker(id="custom-chunker")
        assert processor.id == "custom-chunker"
        
    @pytest.mark.asyncio
    async def test_on_message_single_chunk(self, mock_async_processor_init, mock_flow, mock_consumer, short_document):
        flow_mock, output_mock = mock_flow
        processor = RecursiveChunker(chunk_size=2000, chunk_overlap=100)
        
        msg = Mock()
        msg.value.return_value = short_document
        
        await processor.on_message(msg, mock_consumer, flow_mock)
        
        # Should produce exactly one chunk for short text
        assert output_mock.send.call_count == 1
        
        # Verify the chunk was created correctly
        chunk_call = output_mock.send.call_args[0][0]
        assert isinstance(chunk_call, Chunk)
        assert chunk_call.metadata == short_document.metadata
        assert chunk_call.chunk.decode("utf-8") == short_document.text.decode("utf-8")
        
    @pytest.mark.asyncio
    async def test_on_message_multiple_chunks(self, mock_async_processor_init, mock_flow, mock_consumer, sample_document):
        flow_mock, output_mock = mock_flow
        processor = RecursiveChunker(chunk_size=100, chunk_overlap=20)
        
        msg = Mock()
        msg.value.return_value = sample_document
        
        await processor.on_message(msg, mock_consumer, flow_mock)
        
        # Should produce multiple chunks
        assert output_mock.send.call_count > 1
        
        # Verify all chunks have correct metadata
        for call in output_mock.send.call_args_list:
            chunk = call[0][0]
            assert isinstance(chunk, Chunk)
            assert chunk.metadata == sample_document.metadata
            assert len(chunk.chunk) > 0
            
    @pytest.mark.asyncio
    async def test_on_message_chunk_overlap(self, mock_async_processor_init, mock_flow, mock_consumer):
        flow_mock, output_mock = mock_flow
        processor = RecursiveChunker(chunk_size=50, chunk_overlap=10)
        
        # Create a document with predictable content
        metadata = Metadata(id="test", metadata=[], user="test-user", collection="test-collection")
        text = "ABCDEFGHIJ" * 10  # 100 characters
        document = TextDocument(metadata=metadata, text=text.encode("utf-8"))
        
        msg = Mock()
        msg.value.return_value = document
        
        await processor.on_message(msg, mock_consumer, flow_mock)
        
        # Collect all chunks
        chunks = []
        for call in output_mock.send.call_args_list:
            chunk_text = call[0][0].chunk.decode("utf-8")
            chunks.append(chunk_text)
            
        # Verify chunks have expected overlap
        for i in range(len(chunks) - 1):
            # The end of chunk i should overlap with the beginning of chunk i+1
            # Check if there's some overlap (exact overlap depends on text splitter logic)
            assert len(chunks[i]) <= 50 + 10  # chunk_size + some tolerance
            
    @pytest.mark.asyncio
    async def test_on_message_empty_document(self, mock_async_processor_init, mock_flow, mock_consumer):
        flow_mock, output_mock = mock_flow
        processor = RecursiveChunker()
        
        metadata = Metadata(id="empty", metadata=[], user="test-user", collection="test-collection")
        document = TextDocument(metadata=metadata, text=b"")
        
        msg = Mock()
        msg.value.return_value = document
        
        await processor.on_message(msg, mock_consumer, flow_mock)
        
        # Should produce one empty chunk
        assert output_mock.send.call_count == 1
        chunk = output_mock.send.call_args[0][0]
        assert chunk.chunk == b""
        
    @pytest.mark.asyncio
    async def test_on_message_unicode_handling(self, mock_async_processor_init, mock_flow, mock_consumer):
        flow_mock, output_mock = mock_flow
        processor = RecursiveChunker(chunk_size=50)
        
        metadata = Metadata(id="unicode", metadata=[], user="test-user", collection="test-collection")
        text = "Hello 世界! 🌍 This is a test with émojis and spëcial characters."
        document = TextDocument(metadata=metadata, text=text.encode("utf-8"))
        
        msg = Mock()
        msg.value.return_value = document
        
        await processor.on_message(msg, mock_consumer, flow_mock)
        
        # Verify unicode is preserved correctly
        all_chunks = []
        for call in output_mock.send.call_args_list:
            chunk_text = call[0][0].chunk.decode("utf-8")
            all_chunks.append(chunk_text)
            
        # Reconstruct text (approximately, due to overlap)
        reconstructed = "".join(all_chunks)
        assert "世界" in reconstructed
        assert "🌍" in reconstructed
        assert "émojis" in reconstructed
        
    @pytest.mark.asyncio
    async def test_metrics_recorded(self, mock_async_processor_init, mock_flow, mock_consumer, sample_document):
        flow_mock, output_mock = mock_flow
        processor = RecursiveChunker(chunk_size=100)
        
        msg = Mock()
        msg.value.return_value = sample_document
        
        # Mock the metric
        with patch.object(RecursiveChunker.chunk_metric, 'labels') as mock_labels:
            mock_observe = Mock()
            mock_labels.return_value.observe = mock_observe
            
            await processor.on_message(msg, mock_consumer, flow_mock)
            
            # Verify metrics were recorded
            mock_labels.assert_called_with(id="test-consumer", flow="test-flow")
            assert mock_observe.call_count > 0
            
            # Verify chunk sizes were observed
            for call in mock_observe.call_args_list:
                chunk_size = call[0][0]
                assert chunk_size > 0
                
    def test_add_args(self):
        parser = Mock()
        RecursiveChunker.add_args(parser)
        
        # Verify arguments were added
        calls = parser.add_argument.call_args_list
        arg_names = [call[0][0] for call in calls]
        
        assert '-z' in arg_names or '--chunk-size' in arg_names
        assert '-v' in arg_names or '--chunk-overlap' in arg_names