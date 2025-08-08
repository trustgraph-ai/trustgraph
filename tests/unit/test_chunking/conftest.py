import pytest
from unittest.mock import AsyncMock, Mock
from trustgraph.schema import TextDocument, Metadata
from trustgraph.chunking.recursive.chunker import Processor as RecursiveChunker
from trustgraph.chunking.token.chunker import Processor as TokenChunker


@pytest.fixture
def mock_flow():
    """Mock flow function that returns a mock output producer."""
    output_mock = AsyncMock()
    flow_mock = Mock(return_value=output_mock)
    return flow_mock, output_mock


@pytest.fixture
def mock_consumer():
    """Mock consumer with test attributes."""
    consumer = Mock()
    consumer.id = "test-consumer"
    consumer.flow = "test-flow"
    return consumer


@pytest.fixture
def sample_text_document():
    """Sample document with moderate length text."""
    metadata = Metadata(
        id="test-doc-1",
        metadata=[],
        user="test-user",
        collection="test-collection"
    )
    text = "The quick brown fox jumps over the lazy dog. " * 20
    return TextDocument(
        metadata=metadata,
        text=text.encode("utf-8")
    )


@pytest.fixture
def long_text_document():
    """Long document for testing multiple chunks."""
    metadata = Metadata(
        id="test-doc-long",
        metadata=[],
        user="test-user",
        collection="test-collection"
    )
    # Create a long text that will definitely be chunked
    text = " ".join([f"Sentence number {i}. This is part of a long document." for i in range(200)])
    return TextDocument(
        metadata=metadata,
        text=text.encode("utf-8")
    )


@pytest.fixture
def unicode_text_document():
    """Document with various unicode characters."""
    metadata = Metadata(
        id="test-doc-unicode",
        metadata=[],
        user="test-user",
        collection="test-collection"
    )
    text = """
    English: Hello World!
    Chinese: 你好世界
    Japanese: こんにちは世界
    Korean: 안녕하세요 세계
    Arabic: مرحبا بالعالم
    Russian: Привет мир
    Emoji: 🌍 🌎 🌏 😀 🎉
    Math: ∑ ∏ ∫ ∞ √ π
    Symbols: © ® ™ € £ ¥
    """
    return TextDocument(
        metadata=metadata,
        text=text.encode("utf-8")
    )


@pytest.fixture
def empty_text_document():
    """Empty document for edge case testing."""
    metadata = Metadata(
        id="test-doc-empty",
        metadata=[],
        user="test-user",
        collection="test-collection"
    )
    return TextDocument(
        metadata=metadata,
        text=b""
    )


@pytest.fixture
def mock_message(sample_text_document):
    """Mock message containing a document."""
    msg = Mock()
    msg.value.return_value = sample_text_document
    return msg


@pytest.fixture(autouse=True)
def clear_metrics():
    """Clear metrics before each test to avoid duplicates."""
    # Clear the chunk_metric class attribute if it exists
    if hasattr(RecursiveChunker, 'chunk_metric'):
        delattr(RecursiveChunker, 'chunk_metric')
    if hasattr(TokenChunker, 'chunk_metric'):
        delattr(TokenChunker, 'chunk_metric')
    yield
    # Clean up after test as well
    if hasattr(RecursiveChunker, 'chunk_metric'):
        delattr(RecursiveChunker, 'chunk_metric')
    if hasattr(TokenChunker, 'chunk_metric'):
        delattr(TokenChunker, 'chunk_metric')


@pytest.fixture
def mock_async_processor_init():
    """Mock AsyncProcessor.__init__ to avoid taskgroup requirement."""
    def init_mock(self, **kwargs):
        # Set attributes that AsyncProcessor would normally set
        self.config_handlers = []
        self.specifications = []
        self.flows = {}
        self.id = kwargs.get('id', 'test-processor')
        # Don't call the real __init__
    
    with pytest.mock.patch('trustgraph.base.async_processor.AsyncProcessor.__init__', init_mock):
        yield