"""
Unit tests for the load_knowledge CLI module.

Tests the business logic of loading triples and entity contexts from Turtle files
using the BulkClient API.
"""

import pytest
import tempfile
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path

from trustgraph.cli.load_knowledge import KnowledgeLoader, main
from trustgraph.api import Triple


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
def knowledge_loader():
    """Create a KnowledgeLoader instance with test parameters."""
    return KnowledgeLoader(
        files=["test.ttl"],
        flow="test-flow",
        user="test-user",
        collection="test-collection",
        document_id="test-doc-123",
        url="http://test.example.com/",
        token=None
    )


class TestKnowledgeLoader:
    """Test the KnowledgeLoader class business logic."""

    def test_init_stores_parameters_correctly(self):
        """Test that initialization stores parameters correctly."""
        loader = KnowledgeLoader(
            files=["file1.ttl", "file2.ttl"],
            flow="my-flow",
            user="user1",
            collection="col1",
            document_id="doc1",
            url="http://example.com/",
            token="test-token"
        )

        assert loader.files == ["file1.ttl", "file2.ttl"]
        assert loader.flow == "my-flow"
        assert loader.user == "user1"
        assert loader.collection == "col1"
        assert loader.document_id == "doc1"
        assert loader.url == "http://example.com/"
        assert loader.token == "test-token"

    def test_load_triples_from_file_yields_triples(self, temp_turtle_file, knowledge_loader):
        """Test that load_triples_from_file yields Triple objects."""
        triples = list(knowledge_loader.load_triples_from_file(temp_turtle_file))

        # Should have triples for all statements in the file
        assert len(triples) > 0

        # Verify they are Triple objects
        for triple in triples:
            assert isinstance(triple, Triple)
            assert hasattr(triple, 's')
            assert hasattr(triple, 'p')
            assert hasattr(triple, 'o')
            assert isinstance(triple.s, str)
            assert isinstance(triple.p, str)
            assert isinstance(triple.o, str)

    def test_load_entity_contexts_from_file_yields_literals_only(self, temp_turtle_file, knowledge_loader):
        """Test that entity contexts are created only for literals."""
        contexts = list(knowledge_loader.load_entity_contexts_from_file(temp_turtle_file))

        # Should have contexts for literal objects (foaf:name, foaf:age, foaf:email)
        assert len(contexts) > 0

        # Verify format: (entity, context) tuples
        for entity, context in contexts:
            assert isinstance(entity, str)
            assert isinstance(context, str)
            # Entity should be a URI (subject)
            assert entity.startswith("http://")

    def test_load_entity_contexts_skips_uri_objects(self):
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
                document_id="test-doc",
                url="http://test.example.com/"
            )

            contexts = list(loader.load_entity_contexts_from_file(f.name))

        Path(f.name).unlink(missing_ok=True)

        # Should have no contexts since there are no literals
        assert len(contexts) == 0

    @patch('trustgraph.cli.load_knowledge.Api')
    def test_run_calls_bulk_api(self, mock_api_class, temp_turtle_file):
        """Test that run() uses BulkClient API."""
        # Setup mocks
        mock_api = MagicMock()
        mock_bulk = MagicMock()
        mock_api_class.return_value = mock_api
        mock_api.bulk.return_value = mock_bulk

        loader = KnowledgeLoader(
            files=[temp_turtle_file],
            flow="test-flow",
            user="test-user",
            collection="test-collection",
            document_id="test-doc",
            url="http://test.example.com/",
            token="test-token"
        )

        loader.run()

        # Verify Api was created with correct parameters
        mock_api_class.assert_called_once_with(
            url="http://test.example.com/",
            token="test-token"
        )

        # Verify bulk client was obtained
        mock_api.bulk.assert_called_once()

        # Verify import_triples was called
        assert mock_bulk.import_triples.call_count == 1
        call_args = mock_bulk.import_triples.call_args
        assert call_args[1]['flow'] == "test-flow"
        assert call_args[1]['metadata']['id'] == "test-doc"
        assert call_args[1]['metadata']['user'] == "test-user"
        assert call_args[1]['metadata']['collection'] == "test-collection"

        # Verify import_entity_contexts was called
        assert mock_bulk.import_entity_contexts.call_count == 1
        call_args = mock_bulk.import_entity_contexts.call_args
        assert call_args[1]['flow'] == "test-flow"
        assert call_args[1]['metadata']['id'] == "test-doc"


class TestCLIArgumentParsing:
    """Test CLI argument parsing and main function."""

    @patch('trustgraph.cli.load_knowledge.KnowledgeLoader')
    @patch('trustgraph.cli.load_knowledge.time.sleep')
    def test_main_parses_args_correctly(self, mock_sleep, mock_loader_class):
        """Test that main() parses arguments correctly."""
        mock_loader_instance = MagicMock()
        mock_loader_class.return_value = mock_loader_instance

        test_args = [
            'tg-load-knowledge',
            '-i', 'doc-123',
            '-f', 'my-flow',
            '-U', 'my-user',
            '-C', 'my-collection',
            '-u', 'http://custom.example.com/',
            '-t', 'my-token',
            'file1.ttl',
            'file2.ttl'
        ]

        with patch('sys.argv', test_args):
            main()

        # Verify KnowledgeLoader was instantiated with correct args
        mock_loader_class.assert_called_once_with(
            document_id='doc-123',
            url='http://custom.example.com/',
            token='my-token',
            flow='my-flow',
            files=['file1.ttl', 'file2.ttl'],
            user='my-user',
            collection='my-collection'
        )

        # Verify run was called
        mock_loader_instance.run.assert_called_once()

    @patch('trustgraph.cli.load_knowledge.KnowledgeLoader')
    @patch('trustgraph.cli.load_knowledge.time.sleep')
    def test_main_uses_defaults(self, mock_sleep, mock_loader_class):
        """Test that main() uses default values when not specified."""
        mock_loader_instance = MagicMock()
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
        assert call_args['url'] == 'http://localhost:8088/'
        assert call_args['token'] is None


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_load_triples_handles_invalid_turtle(self, knowledge_loader):
        """Test handling of invalid Turtle content."""
        # Create file with invalid Turtle content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ttl', delete=False) as f:
            f.write("Invalid Turtle Content {{{")
            f.flush()

            # Should raise an exception for invalid Turtle
            with pytest.raises(Exception):
                list(knowledge_loader.load_triples_from_file(f.name))

        Path(f.name).unlink(missing_ok=True)

    def test_load_entity_contexts_handles_invalid_turtle(self, knowledge_loader):
        """Test handling of invalid Turtle content in entity contexts."""
        # Create file with invalid Turtle content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ttl', delete=False) as f:
            f.write("Invalid Turtle Content {{{")
            f.flush()

            # Should raise an exception for invalid Turtle
            with pytest.raises(Exception):
                list(knowledge_loader.load_entity_contexts_from_file(f.name))

        Path(f.name).unlink(missing_ok=True)

    @patch('trustgraph.cli.load_knowledge.Api')
    @patch('builtins.print')  # Mock print to avoid output during tests
    def test_run_handles_api_errors(self, mock_print, mock_api_class, temp_turtle_file):
        """Test handling of API errors."""
        # Mock API to raise an error
        mock_api_class.side_effect = Exception("API connection failed")

        loader = KnowledgeLoader(
            files=[temp_turtle_file],
            flow="test-flow",
            user="test-user",
            collection="test-collection",
            document_id="test-doc",
            url="http://test.example.com/"
        )

        # Should raise the exception
        with pytest.raises(Exception, match="API connection failed"):
            loader.run()

    @patch('trustgraph.cli.load_knowledge.KnowledgeLoader')
    @patch('trustgraph.cli.load_knowledge.time.sleep')
    @patch('builtins.print')  # Mock print to avoid output during tests
    def test_main_retries_on_exception(self, mock_print, mock_sleep, mock_loader_class):
        """Test that main() retries on exceptions."""
        mock_loader_instance = MagicMock()
        mock_loader_class.return_value = mock_loader_instance

        # First call raises exception, second succeeds
        mock_loader_instance.run.side_effect = [Exception("Test error"), None]

        test_args = [
            'tg-load-knowledge',
            '-i', 'doc-123',
            'file1.ttl'
        ]

        with patch('sys.argv', test_args):
            main()

        # Should have been called twice (first failed, second succeeded)
        assert mock_loader_instance.run.call_count == 2
        mock_sleep.assert_called_once_with(10)


class TestDataValidation:
    """Test data validation and edge cases."""

    def test_empty_turtle_file(self, knowledge_loader):
        """Test handling of empty Turtle files."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ttl', delete=False) as f:
            f.write("")  # Empty file
            f.flush()

            triples = list(knowledge_loader.load_triples_from_file(f.name))
            contexts = list(knowledge_loader.load_entity_contexts_from_file(f.name))

            # Should return empty lists for empty file
            assert len(triples) == 0
            assert len(contexts) == 0

        Path(f.name).unlink(missing_ok=True)

    def test_turtle_with_mixed_literals_and_uris(self, knowledge_loader):
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

            contexts = list(knowledge_loader.load_entity_contexts_from_file(f.name))

            # Should have 4 entity contexts (for the 4 literals: "John Smith", "25", "New York", "Mary Johnson")
            # URI ex:mary should be skipped
            assert len(contexts) == 4

            # Verify all contexts are for literals (subjects should be URIs)
            context_values = [context for entity, context in contexts]

            assert "John Smith" in context_values
            assert "25" in context_values
            assert "New York" in context_values
            assert "Mary Johnson" in context_values

        Path(f.name).unlink(missing_ok=True)
