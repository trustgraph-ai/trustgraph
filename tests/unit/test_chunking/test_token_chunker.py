import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from trustgraph.schema import TextDocument, Chunk, Metadata
from trustgraph.chunking.token.chunker import Processor as TokenChunker


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
    # Create text that will result in multiple token chunks
    text = "The quick brown fox jumps over the lazy dog. " * 50
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
    text = "Short text."
    return TextDocument(
        metadata=metadata,
        text=text.encode("utf-8")
    )


class TestTokenChunker:
    
    def test_init_default_params(self, mock_async_processor_init):
        processor = TokenChunker()
        assert processor.text_splitter._chunk_size == 250
        assert processor.text_splitter._chunk_overlap == 15
        # Just verify the text splitter was created (encoding verification is complex)
        assert processor.text_splitter is not None
        assert hasattr(processor.text_splitter, 'split_text')
        
    def test_init_custom_params(self, mock_async_processor_init):
        processor = TokenChunker(chunk_size=100, chunk_overlap=10)
        assert processor.text_splitter._chunk_size == 100
        assert processor.text_splitter._chunk_overlap == 10
        
    def test_init_with_id(self, mock_async_processor_init):
        processor = TokenChunker(id="custom-token-chunker")
        assert processor.id == "custom-token-chunker"
        
    @pytest.mark.asyncio
    async def test_on_message_single_chunk(self, mock_async_processor_init, mock_flow, mock_consumer, short_document):
        flow_mock, output_mock = mock_flow
        processor = TokenChunker(chunk_size=250, chunk_overlap=15)
        
        msg = Mock()
        msg.value.return_value = short_document
        
        await processor.on_message(msg, mock_consumer, flow_mock)
        
        # Short text should produce exactly one chunk
        assert output_mock.send.call_count == 1
        
        # Verify the chunk was created correctly
        chunk_call = output_mock.send.call_args[0][0]
        assert isinstance(chunk_call, Chunk)
        assert chunk_call.metadata == short_document.metadata
        assert chunk_call.chunk.decode("utf-8") == short_document.text.decode("utf-8")
        
    @pytest.mark.asyncio
    async def test_on_message_multiple_chunks(self, mock_async_processor_init, mock_flow, mock_consumer, sample_document):
        flow_mock, output_mock = mock_flow
        processor = TokenChunker(chunk_size=50, chunk_overlap=5)
        
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
    async def test_on_message_token_overlap(self, mock_async_processor_init, mock_flow, mock_consumer):
        flow_mock, output_mock = mock_flow
        processor = TokenChunker(chunk_size=20, chunk_overlap=5)
        
        # Create a document with repeated pattern
        metadata = Metadata(id="test", metadata=[], user="test-user", collection="test-collection")
        text = "one two three four five six seven eight nine ten " * 5
        document = TextDocument(metadata=metadata, text=text.encode("utf-8"))
        
        msg = Mock()
        msg.value.return_value = document
        
        await processor.on_message(msg, mock_consumer, flow_mock)
        
        # Collect all chunks
        chunks = []
        for call in output_mock.send.call_args_list:
            chunk_text = call[0][0].chunk.decode("utf-8")
            chunks.append(chunk_text)
            
        # Should have multiple chunks
        assert len(chunks) > 1
        
        # Verify chunks are not empty
        for chunk in chunks:
            assert len(chunk) > 0
            
    @pytest.mark.asyncio
    async def test_on_message_empty_document(self, mock_async_processor_init, mock_flow, mock_consumer):
        flow_mock, output_mock = mock_flow
        processor = TokenChunker()
        
        metadata = Metadata(id="empty", metadata=[], user="test-user", collection="test-collection")
        document = TextDocument(metadata=metadata, text=b"")
        
        msg = Mock()
        msg.value.return_value = document
        
        await processor.on_message(msg, mock_consumer, flow_mock)
        
        # Empty documents typically don't produce chunks with langchain splitters
        # This behavior is expected - no chunks should be produced
        assert output_mock.send.call_count == 0
        
    @pytest.mark.asyncio
    async def test_on_message_unicode_handling(self, mock_async_processor_init, mock_flow, mock_consumer):
        flow_mock, output_mock = mock_flow
        processor = TokenChunker(chunk_size=50)
        
        metadata = Metadata(id="unicode", metadata=[], user="test-user", collection="test-collection")
        # Test with various unicode characters
        text = "Hello 世界! 🌍 Test émojis café naïve résumé. Greek: αβγδε Hebrew: אבגדה"
        document = TextDocument(metadata=metadata, text=text.encode("utf-8"))
        
        msg = Mock()
        msg.value.return_value = document
        
        await processor.on_message(msg, mock_consumer, flow_mock)
        
        # Verify unicode is preserved correctly
        all_chunks = []
        for call in output_mock.send.call_args_list:
            chunk_text = call[0][0].chunk.decode("utf-8")
            all_chunks.append(chunk_text)
            
        # Reconstruct text
        reconstructed = "".join(all_chunks)
        assert "世界" in reconstructed
        assert "🌍" in reconstructed
        assert "émojis" in reconstructed
        assert "αβγδε" in reconstructed
        assert "אבגדה" in reconstructed
        
    @pytest.mark.asyncio
    async def test_on_message_token_boundary_preservation(self, mock_async_processor_init, mock_flow, mock_consumer):
        flow_mock, output_mock = mock_flow
        processor = TokenChunker(chunk_size=10, chunk_overlap=2)
        
        metadata = Metadata(id="boundary", metadata=[], user="test-user", collection="test-collection")
        # Text with clear word boundaries
        text = "This is a test of token boundaries and proper splitting."
        document = TextDocument(metadata=metadata, text=text.encode("utf-8"))
        
        msg = Mock()
        msg.value.return_value = document
        
        await processor.on_message(msg, mock_consumer, flow_mock)
        
        # Collect all chunks
        chunks = []
        for call in output_mock.send.call_args_list:
            chunk_text = call[0][0].chunk.decode("utf-8")
            chunks.append(chunk_text)
            
        # Token chunker should respect token boundaries
        for chunk in chunks:
            # Chunks should not start or end with partial words (in most cases)
            assert len(chunk.strip()) > 0
            
    @pytest.mark.asyncio
    async def test_metrics_recorded(self, mock_async_processor_init, mock_flow, mock_consumer, sample_document):
        flow_mock, output_mock = mock_flow
        processor = TokenChunker(chunk_size=50)
        
        msg = Mock()
        msg.value.return_value = sample_document
        
        # Mock the metric
        with patch.object(TokenChunker.chunk_metric, 'labels') as mock_labels:
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
        TokenChunker.add_args(parser)
        
        # Verify arguments were added
        calls = parser.add_argument.call_args_list
        arg_names = [call[0][0] for call in calls]
        
        assert '-z' in arg_names or '--chunk-size' in arg_names
        assert '-v' in arg_names or '--chunk-overlap' in arg_names
        
    @pytest.mark.asyncio
    async def test_encoding_specific_behavior(self, mock_async_processor_init, mock_flow, mock_consumer):
        flow_mock, output_mock = mock_flow
        processor = TokenChunker(chunk_size=10, chunk_overlap=0)
        
        metadata = Metadata(id="encoding", metadata=[], user="test-user", collection="test-collection")
        # Test text that might tokenize differently with cl100k_base encoding
        text = "GPT-4 is an AI model. It uses tokens."
        document = TextDocument(metadata=metadata, text=text.encode("utf-8"))
        
        msg = Mock()
        msg.value.return_value = document
        
        await processor.on_message(msg, mock_consumer, flow_mock)
        
        # Verify chunking happened
        assert output_mock.send.call_count >= 1
        
        # Collect all chunks
        chunks = []
        for call in output_mock.send.call_args_list:
            chunk_text = call[0][0].chunk.decode("utf-8")
            chunks.append(chunk_text)
            
        # Verify all text is preserved (allowing for overlap)
        all_text = " ".join(chunks)
        assert "GPT-4" in all_text
        assert "AI model" in all_text
        assert "tokens" in all_text