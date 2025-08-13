"""
Unit tests for the load_knowledge CLI module.

Tests the business logic of loading triples and entity contexts from Turtle files
while mocking WebSocket connections and external dependencies.
"""

import pytest
import json
import tempfile
from unittest.mock import AsyncMock, patch, mock_open
from pathlib import Path

from trustgraph.cli.load_knowledge import KnowledgeLoader, main


@pytest.fixture
def sample_turtle_content():
    """Sample Turtle RDF content for testing."""
    return """
@prefix ex: <http://example.org/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .

ex:john foaf:name "John Smith" ;
        foaf:age "30" ;
        foaf:knows ex:mary .

ex:mary foaf:name "Mary Johnson" ;
        foaf:email "mary@example.com" .
"""


@pytest.fixture
def temp_turtle_file(sample_turtle_content):
    """Create a temporary Turtle file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ttl', delete=False) as f:
        f.write(sample_turtle_content)
        f.flush()
        yield f.name
    
    # Cleanup
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def mock_websocket():
    """Mock WebSocket connection."""
    mock_ws = AsyncMock()
    return mock_ws


@pytest.fixture
def knowledge_loader():
    """Create a KnowledgeLoader instance with test parameters."""
    return KnowledgeLoader(
        files=["test.ttl"],
        flow="test-flow",
        user="test-user", 
        collection="test-collection",
        document_id="test-doc-123",
        url="ws://test.example.com/"
    )


class TestKnowledgeLoader:
    """Test the KnowledgeLoader class business logic."""

    def test_init_constructs_urls_correctly(self):
        """Test that URLs are constructed properly."""
        loader = KnowledgeLoader(
            files=["test.ttl"],
            flow="my-flow",
            user="user1",
            collection="col1", 
            document_id="doc1",
            url="ws://example.com/"
        )
        
        assert loader.triples_url == "ws://example.com/api/v1/flow/my-flow/import/triples"
        assert loader.entity_contexts_url == "ws://example.com/api/v1/flow/my-flow/import/entity-contexts"
        assert loader.user == "user1"
        assert loader.collection == "col1"
        assert loader.document_id == "doc1"

    def test_init_adds_trailing_slash(self):
        """Test that trailing slash is added to URL if missing."""
        loader = KnowledgeLoader(
            files=["test.ttl"],
            flow="my-flow", 
            user="user1",
            collection="col1",
            document_id="doc1",
            url="ws://example.com"  # No trailing slash
        )
        
        assert loader.triples_url == "ws://example.com/api/v1/flow/my-flow/import/triples"

    @pytest.mark.asyncio
    async def test_load_triples_sends_correct_messages(self, temp_turtle_file, mock_websocket):
        """Test that triple loading sends correctly formatted messages."""
        loader = KnowledgeLoader(
            files=[temp_turtle_file],
            flow="test-flow",
            user="test-user",
            collection="test-collection", 
            document_id="test-doc"
        )
        
        await loader.load_triples(temp_turtle_file, mock_websocket)
        
        # Verify WebSocket send was called
        assert mock_websocket.send.call_count > 0
        
        # Check message format for one of the calls
        sent_messages = [json.loads(call.args[0]) for call in mock_websocket.send.call_args_list]
        
        # Verify message structure
        sample_message = sent_messages[0]
        assert "metadata" in sample_message
        assert "triples" in sample_message
        
        metadata = sample_message["metadata"]
        assert metadata["id"] == "test-doc"
        assert metadata["user"] == "test-user"
        assert metadata["collection"] == "test-collection"
        assert isinstance(metadata["metadata"], list)
        
        triple = sample_message["triples"][0]
        assert "s" in triple
        assert "p" in triple
        assert "o" in triple
        
        # Check Value structure
        assert "v" in triple["s"]
        assert "e" in triple["s"]
        assert triple["s"]["e"] is True  # Subject should be URI

    @pytest.mark.asyncio
    async def test_load_entity_contexts_processes_literals_only(self, temp_turtle_file, mock_websocket):
        """Test that entity contexts are created only for literals."""
        loader = KnowledgeLoader(
            files=[temp_turtle_file],
            flow="test-flow",
            user="test-user",
            collection="test-collection",
            document_id="test-doc"
        )
        
        await loader.load_entity_contexts(temp_turtle_file, mock_websocket)
        
        # Get all sent messages
        sent_messages = [json.loads(call.args[0]) for call in mock_websocket.send.call_args_list]
        
        # Verify we got entity context messages
        assert len(sent_messages) > 0
        
        for message in sent_messages:
            assert "metadata" in message
            assert "entities" in message
            
            metadata = message["metadata"]
            assert metadata["id"] == "test-doc"
            assert metadata["user"] == "test-user"
            assert metadata["collection"] == "test-collection"
            
            entity_context = message["entities"][0]
            assert "entity" in entity_context
            assert "context" in entity_context
            
            entity = entity_context["entity"]
            assert "v" in entity
            assert "e" in entity
            assert entity["e"] is True  # Entity should be URI (subject)
            
            # Context should be a string (the literal value)
            assert isinstance(entity_context["context"], str)

    @pytest.mark.asyncio 
    async def test_load_entity_contexts_skips_uri_objects(self, mock_websocket):
        """Test that URI objects don't generate entity contexts."""
        # Create turtle with only URI objects (no literals)
        turtle_content = """
@prefix ex: <http://example.org/> .
ex:john ex:knows ex:mary .
ex:mary ex:knows ex:bob .
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ttl', delete=False) as f:
            f.write(turtle_content)
            f.flush()
            
            loader = KnowledgeLoader(
                files=[f.name],
                flow="test-flow",
                user="test-user", 
                collection="test-collection",
                document_id="test-doc"
            )
            
            await loader.load_entity_contexts(f.name, mock_websocket)
            
        Path(f.name).unlink(missing_ok=True)
        
        # Should not send any messages since there are no literals
        mock_websocket.send.assert_not_called()

    @pytest.mark.asyncio
    @patch('trustgraph.cli.load_knowledge.connect')
    async def test_run_calls_both_loaders(self, mock_connect, knowledge_loader, temp_turtle_file):
        """Test that run() calls both triple and entity context loaders."""
        knowledge_loader.files = [temp_turtle_file]
        
        mock_ws = AsyncMock()
        mock_connect.return_value.__aenter__.return_value = mock_ws
        
        with patch.object(knowledge_loader, 'load_triples') as mock_load_triples, \
             patch.object(knowledge_loader, 'load_entity_contexts') as mock_load_contexts:
            
            await knowledge_loader.run()
            
            # Verify both methods were called
            mock_load_triples.assert_called_once_with(temp_turtle_file, mock_ws)
            mock_load_contexts.assert_called_once_with(temp_turtle_file, mock_ws)
            
            # Verify WebSocket connections were made to both URLs
            assert mock_connect.call_count == 2


class TestCLIArgumentParsing:
    """Test CLI argument parsing and main function."""

    @patch('trustgraph.cli.load_knowledge.KnowledgeLoader')
    @patch('trustgraph.cli.load_knowledge.asyncio.run')
    def test_main_parses_args_correctly(self, mock_asyncio_run, mock_loader_class):
        """Test that main() parses arguments correctly."""
        mock_loader_instance = AsyncMock()
        mock_loader_class.return_value = mock_loader_instance
        
        test_args = [
            'tg-load-knowledge',
            '-i', 'doc-123',
            '-f', 'my-flow', 
            '-U', 'my-user',
            '-C', 'my-collection',
            '-u', 'ws://custom.example.com/',
            'file1.ttl',
            'file2.ttl'
        ]
        
        with patch('sys.argv', test_args):
            main()
        
        # Verify KnowledgeLoader was instantiated with correct args
        mock_loader_class.assert_called_once_with(
            document_id='doc-123',
            url='ws://custom.example.com/',
            flow='my-flow',
            files=['file1.ttl', 'file2.ttl'],
            user='my-user',
            collection='my-collection'
        )
        
        # Verify the loader's run method was called
        mock_asyncio_run.assert_called_once()

    @patch('trustgraph.cli.load_knowledge.KnowledgeLoader')
    @patch('trustgraph.cli.load_knowledge.asyncio.run')
    def test_main_uses_defaults(self, mock_asyncio_run, mock_loader_class):
        """Test that main() uses default values when not specified."""
        mock_loader_instance = AsyncMock()
        mock_loader_class.return_value = mock_loader_instance
        
        test_args = [
            'tg-load-knowledge',
            '-i', 'doc-123',
            'file1.ttl'
        ]
        
        with patch('sys.argv', test_args):
            main()
        
        # Verify defaults were used
        call_args = mock_loader_class.call_args[1]
        assert call_args['flow'] == 'default'
        assert call_args['user'] == 'trustgraph'
        assert call_args['collection'] == 'default'
        assert call_args['url'] == 'ws://localhost:8088/'


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_load_triples_handles_invalid_turtle(self, mock_websocket):
        """Test handling of invalid Turtle content."""
        # Create file with invalid Turtle content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ttl', delete=False) as f:
            f.write("Invalid Turtle Content {{{")
            f.flush()
            
            loader = KnowledgeLoader(
                files=[f.name],
                flow="test-flow",
                user="test-user",
                collection="test-collection",
                document_id="test-doc"
            )
            
            # Should raise an exception for invalid Turtle
            with pytest.raises(Exception):
                await loader.load_triples(f.name, mock_websocket)
                
        Path(f.name).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_load_entity_contexts_handles_invalid_turtle(self, mock_websocket):
        """Test handling of invalid Turtle content in entity contexts."""
        # Create file with invalid Turtle content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ttl', delete=False) as f:
            f.write("Invalid Turtle Content {{{")
            f.flush()
            
            loader = KnowledgeLoader(
                files=[f.name],
                flow="test-flow",
                user="test-user", 
                collection="test-collection",
                document_id="test-doc"
            )
            
            # Should raise an exception for invalid Turtle
            with pytest.raises(Exception):
                await loader.load_entity_contexts(f.name, mock_websocket)
                
        Path(f.name).unlink(missing_ok=True)

    @pytest.mark.asyncio
    @patch('trustgraph.cli.load_knowledge.connect')
    async def test_run_handles_connection_errors(self, mock_connect, knowledge_loader, temp_turtle_file):
        """Test handling of WebSocket connection errors."""
        knowledge_loader.files = [temp_turtle_file]
        
        # Mock connection failure
        mock_connect.side_effect = ConnectionError("Failed to connect")
        
        # Should not raise exception, just print error
        await knowledge_loader.run()

    @patch('trustgraph.cli.load_knowledge.KnowledgeLoader')
    @patch('trustgraph.cli.load_knowledge.asyncio.run')
    @patch('trustgraph.cli.load_knowledge.time.sleep')
    def test_main_retries_on_exception(self, mock_sleep, mock_asyncio_run, mock_loader_class):
        """Test that main() retries on exceptions."""
        mock_loader_instance = AsyncMock()
        mock_loader_class.return_value = mock_loader_instance
        
        # First call raises exception, second succeeds
        mock_asyncio_run.side_effect = [Exception("Test error"), None]
        
        test_args = [
            'tg-load-knowledge',
            '-i', 'doc-123', 
            'file1.ttl'
        ]
        
        with patch('sys.argv', test_args):
            main()
        
        # Should have been called twice (first failed, second succeeded)
        assert mock_asyncio_run.call_count == 2
        mock_sleep.assert_called_once_with(10)


class TestDataValidation:
    """Test data validation and edge cases."""

    @pytest.mark.asyncio
    async def test_empty_turtle_file(self, mock_websocket):
        """Test handling of empty Turtle files."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ttl', delete=False) as f:
            f.write("")  # Empty file
            f.flush()
            
            loader = KnowledgeLoader(
                files=[f.name],
                flow="test-flow",
                user="test-user",
                collection="test-collection",
                document_id="test-doc"
            )
            
            await loader.load_triples(f.name, mock_websocket)
            await loader.load_entity_contexts(f.name, mock_websocket)
            
            # Should not send any messages for empty file
            mock_websocket.send.assert_not_called()
            
        Path(f.name).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_turtle_with_mixed_literals_and_uris(self, mock_websocket):
        """Test handling of Turtle with mixed literal and URI objects."""
        turtle_content = """
@prefix ex: <http://example.org/> .
ex:john ex:name "John Smith" ;
        ex:age "25" ;
        ex:knows ex:mary ;
        ex:city "New York" .
ex:mary ex:name "Mary Johnson" .
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ttl', delete=False) as f:
            f.write(turtle_content)
            f.flush()
            
            loader = KnowledgeLoader(
                files=[f.name],
                flow="test-flow",
                user="test-user",
                collection="test-collection", 
                document_id="test-doc"
            )
            
            await loader.load_entity_contexts(f.name, mock_websocket)
            
            sent_messages = [json.loads(call.args[0]) for call in mock_websocket.send.call_args_list]
            
            # Should have 4 entity contexts (for the 4 literals: "John Smith", "25", "New York", "Mary Johnson")
            # URI ex:mary should be skipped
            assert len(sent_messages) == 4
            
            # Verify all contexts are for literals (subjects should be URIs)
            contexts = []
            for message in sent_messages:
                entity_context = message["entities"][0]
                assert entity_context["entity"]["e"] is True  # Subject is URI
                contexts.append(entity_context["context"])
            
            assert "John Smith" in contexts
            assert "25" in contexts  
            assert "New York" in contexts
            assert "Mary Johnson" in contexts
            
        Path(f.name).unlink(missing_ok=True)