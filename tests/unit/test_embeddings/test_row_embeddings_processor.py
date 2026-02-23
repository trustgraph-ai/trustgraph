"""
Unit tests for trustgraph.embeddings.row_embeddings.embeddings
Tests the Stage 1 processor that computes embeddings for row index fields.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase


class TestRowEmbeddingsProcessor(IsolatedAsyncioTestCase):
    """Test row embeddings processor functionality"""

    async def test_processor_initialization(self):
        """Test basic processor initialization"""
        from trustgraph.embeddings.row_embeddings.embeddings import Processor

        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-row-embeddings'
        }

        processor = Processor(**config)

        assert hasattr(processor, 'schemas')
        assert processor.schemas == {}
        assert processor.batch_size == 10  # default

    async def test_processor_initialization_with_custom_batch_size(self):
        """Test processor initialization with custom batch size"""
        from trustgraph.embeddings.row_embeddings.embeddings import Processor

        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-row-embeddings',
            'batch_size': 25
        }

        processor = Processor(**config)

        assert processor.batch_size == 25

    async def test_get_index_names_single_index(self):
        """Test getting index names with single indexed field"""
        from trustgraph.embeddings.row_embeddings.embeddings import Processor
        from trustgraph.schema import RowSchema, Field

        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        schema = RowSchema(
            name='customers',
            description='Customer records',
            fields=[
                Field(name='id', type='text', primary=True),
                Field(name='name', type='text', indexed=True),
                Field(name='email', type='text', indexed=False),
            ]
        )

        index_names = processor.get_index_names(schema)

        # Should include primary key and indexed field
        assert 'id' in index_names
        assert 'name' in index_names
        assert 'email' not in index_names

    async def test_get_index_names_no_indexes(self):
        """Test getting index names when no fields are indexed"""
        from trustgraph.embeddings.row_embeddings.embeddings import Processor
        from trustgraph.schema import RowSchema, Field

        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        schema = RowSchema(
            name='logs',
            description='Log records',
            fields=[
                Field(name='timestamp', type='text'),
                Field(name='message', type='text'),
            ]
        )

        index_names = processor.get_index_names(schema)

        assert index_names == []

    async def test_build_index_value_single_field(self):
        """Test building index value for single field"""
        from trustgraph.embeddings.row_embeddings.embeddings import Processor

        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        value_map = {
            'id': 'CUST001',
            'name': 'John Doe',
            'email': 'john@example.com'
        }

        result = processor.build_index_value(value_map, 'name')

        assert result == ['John Doe']

    async def test_build_index_value_composite_index(self):
        """Test building index value for composite index"""
        from trustgraph.embeddings.row_embeddings.embeddings import Processor

        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        value_map = {
            'first_name': 'John',
            'last_name': 'Doe',
            'city': 'New York'
        }

        result = processor.build_index_value(value_map, 'first_name, last_name')

        assert result == ['John', 'Doe']

    async def test_build_index_value_missing_field(self):
        """Test building index value when field is missing"""
        from trustgraph.embeddings.row_embeddings.embeddings import Processor

        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        value_map = {
            'name': 'John Doe'
        }

        result = processor.build_index_value(value_map, 'missing_field')

        assert result == ['']

    async def test_build_text_for_embedding_single_value(self):
        """Test building text representation for single value"""
        from trustgraph.embeddings.row_embeddings.embeddings import Processor

        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        result = processor.build_text_for_embedding(['John Doe'])

        assert result == 'John Doe'

    async def test_build_text_for_embedding_multiple_values(self):
        """Test building text representation for multiple values"""
        from trustgraph.embeddings.row_embeddings.embeddings import Processor

        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        result = processor.build_text_for_embedding(['John', 'Doe', 'NYC'])

        assert result == 'John Doe NYC'

    async def test_on_schema_config_loads_schemas(self):
        """Test that schema configuration is loaded correctly"""
        from trustgraph.embeddings.row_embeddings.embeddings import Processor
        import json

        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-processor',
            'config_type': 'schema'
        }

        processor = Processor(**config)

        schema_def = {
            'name': 'customers',
            'description': 'Customer records',
            'fields': [
                {'name': 'id', 'type': 'text', 'primary_key': True},
                {'name': 'name', 'type': 'text', 'indexed': True},
                {'name': 'email', 'type': 'text'}
            ]
        }

        config_data = {
            'schema': {
                'customers': json.dumps(schema_def)
            }
        }

        await processor.on_schema_config(config_data, 1)

        assert 'customers' in processor.schemas
        assert processor.schemas['customers'].name == 'customers'
        assert len(processor.schemas['customers'].fields) == 3

    async def test_on_schema_config_handles_missing_type(self):
        """Test that missing schema type is handled gracefully"""
        from trustgraph.embeddings.row_embeddings.embeddings import Processor

        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-processor',
            'config_type': 'schema'
        }

        processor = Processor(**config)

        config_data = {
            'other_type': {}
        }

        await processor.on_schema_config(config_data, 1)

        assert processor.schemas == {}

    async def test_on_message_drops_unknown_collection(self):
        """Test that messages for unknown collections are dropped"""
        from trustgraph.embeddings.row_embeddings.embeddings import Processor
        from trustgraph.schema import ExtractedObject

        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)
        # No collections registered

        metadata = MagicMock()
        metadata.user = 'unknown_user'
        metadata.collection = 'unknown_collection'
        metadata.id = 'doc-123'

        obj = ExtractedObject(
            metadata=metadata,
            schema_name='customers',
            values=[{'id': '123', 'name': 'Test'}]
        )

        mock_msg = MagicMock()
        mock_msg.value.return_value = obj

        mock_flow = MagicMock()

        await processor.on_message(mock_msg, MagicMock(), mock_flow)

        # Flow should not be called for output
        mock_flow.assert_not_called()

    async def test_on_message_drops_unknown_schema(self):
        """Test that messages for unknown schemas are dropped"""
        from trustgraph.embeddings.row_embeddings.embeddings import Processor
        from trustgraph.schema import ExtractedObject

        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)
        processor.known_collections[('test_user', 'test_collection')] = {}
        # No schemas registered

        metadata = MagicMock()
        metadata.user = 'test_user'
        metadata.collection = 'test_collection'
        metadata.id = 'doc-123'

        obj = ExtractedObject(
            metadata=metadata,
            schema_name='unknown_schema',
            values=[{'id': '123', 'name': 'Test'}]
        )

        mock_msg = MagicMock()
        mock_msg.value.return_value = obj

        mock_flow = MagicMock()

        await processor.on_message(mock_msg, MagicMock(), mock_flow)

        # Flow should not be called for output
        mock_flow.assert_not_called()

    async def test_on_message_processes_embeddings(self):
        """Test processing a message and computing embeddings"""
        from trustgraph.embeddings.row_embeddings.embeddings import Processor
        from trustgraph.schema import ExtractedObject, RowSchema, Field
        import json

        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-processor',
            'config_type': 'schema'
        }

        processor = Processor(**config)
        processor.known_collections[('test_user', 'test_collection')] = {}

        # Set up schema
        processor.schemas['customers'] = RowSchema(
            name='customers',
            description='Customer records',
            fields=[
                Field(name='id', type='text', primary=True),
                Field(name='name', type='text', indexed=True),
            ]
        )

        metadata = MagicMock()
        metadata.user = 'test_user'
        metadata.collection = 'test_collection'
        metadata.id = 'doc-123'

        obj = ExtractedObject(
            metadata=metadata,
            schema_name='customers',
            values=[
                {'id': 'CUST001', 'name': 'John Doe'},
                {'id': 'CUST002', 'name': 'Jane Smith'}
            ]
        )

        mock_msg = MagicMock()
        mock_msg.value.return_value = obj

        # Mock the flow
        mock_embeddings_request = AsyncMock()
        mock_embeddings_request.embed.return_value = [[0.1, 0.2, 0.3]]

        mock_output = AsyncMock()

        def flow_factory(name):
            if name == 'embeddings-request':
                return mock_embeddings_request
            elif name == 'output':
                return mock_output
            return MagicMock()

        mock_flow = MagicMock(side_effect=flow_factory)

        await processor.on_message(mock_msg, MagicMock(), mock_flow)

        # Should have called embed for each unique text
        # 4 values: CUST001, John Doe, CUST002, Jane Smith
        assert mock_embeddings_request.embed.call_count == 4

        # Should have sent output
        mock_output.send.assert_called()


if __name__ == '__main__':
    pytest.main([__file__])
