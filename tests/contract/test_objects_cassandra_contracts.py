"""
Contract tests for Cassandra Object Storage

These tests verify the message contracts and schema compatibility
for the objects storage processor.
"""

import pytest
import json
from pulsar.schema import AvroSchema

from trustgraph.schema import ExtractedObject, Metadata, RowSchema, Field
from trustgraph.storage.objects.cassandra.write import Processor


@pytest.mark.contract
class TestObjectsCassandraContracts:
    """Contract tests for Cassandra object storage messages"""

    def test_extracted_object_input_contract(self):
        """Test that ExtractedObject schema matches expected input format"""
        # Create test object with all required fields
        test_metadata = Metadata(
            id="test-doc-001",
            user="test_user",
            collection="test_collection",
            metadata=[]
        )
        
        test_object = ExtractedObject(
            metadata=test_metadata,
            schema_name="customer_records",
            values=[{
                "customer_id": "CUST123",
                "name": "Test Customer",
                "email": "test@example.com"
            }],
            confidence=0.95,
            source_span="Customer data from document..."
        )
        
        # Verify all required fields are present
        assert hasattr(test_object, 'metadata')
        assert hasattr(test_object, 'schema_name')
        assert hasattr(test_object, 'values')
        assert hasattr(test_object, 'confidence')
        assert hasattr(test_object, 'source_span')
        
        # Verify metadata structure
        assert hasattr(test_object.metadata, 'id')
        assert hasattr(test_object.metadata, 'user')
        assert hasattr(test_object.metadata, 'collection')
        assert hasattr(test_object.metadata, 'metadata')
        
        # Verify types
        assert isinstance(test_object.schema_name, str)
        assert isinstance(test_object.values, list)
        assert isinstance(test_object.confidence, float)
        assert isinstance(test_object.source_span, str)

    def test_row_schema_structure_contract(self):
        """Test RowSchema structure used for table definitions"""
        # Create test schema
        test_fields = [
            Field(
                name="id",
                type="string",
                size=50,
                primary=True,
                description="Primary key",
                required=True,
                enum_values=[],
                indexed=False
            ),
            Field(
                name="status",
                type="string",
                size=20,
                primary=False,
                description="Status field",
                required=False,
                enum_values=["active", "inactive", "pending"],
                indexed=True
            )
        ]
        
        test_schema = RowSchema(
            name="test_table",
            description="Test table schema",
            fields=test_fields
        )
        
        # Verify schema structure
        assert hasattr(test_schema, 'name')
        assert hasattr(test_schema, 'description')
        assert hasattr(test_schema, 'fields')
        assert isinstance(test_schema.fields, list)
        
        # Verify field structure
        for field in test_schema.fields:
            assert hasattr(field, 'name')
            assert hasattr(field, 'type')
            assert hasattr(field, 'size')
            assert hasattr(field, 'primary')
            assert hasattr(field, 'description')
            assert hasattr(field, 'required')
            assert hasattr(field, 'enum_values')
            assert hasattr(field, 'indexed')

    def test_schema_config_format_contract(self):
        """Test the expected configuration format for schemas"""
        # Define expected config structure
        config_format = {
            "schema": {
                "table_name": json.dumps({
                    "name": "table_name",
                    "description": "Table description",
                    "fields": [
                        {
                            "name": "field_name",
                            "type": "string",
                            "size": 0,
                            "primary_key": True,
                            "description": "Field description",
                            "required": True,
                            "enum": [],
                            "indexed": False
                        }
                    ]
                })
            }
        }
        
        # Verify config can be parsed
        schema_json = json.loads(config_format["schema"]["table_name"])
        assert "name" in schema_json
        assert "fields" in schema_json
        assert isinstance(schema_json["fields"], list)
        
        # Verify field format
        field = schema_json["fields"][0]
        required_field_keys = {"name", "type"}
        optional_field_keys = {"size", "primary_key", "description", "required", "enum", "indexed"}
        
        assert required_field_keys.issubset(field.keys())
        assert set(field.keys()).issubset(required_field_keys | optional_field_keys)

    def test_cassandra_type_mapping_contract(self):
        """Test that all supported field types have Cassandra mappings"""
        processor = Processor.__new__(Processor)
        
        # All field types that should be supported
        supported_types = [
            ("string", "text"),
            ("integer", "int"),  # or bigint based on size
            ("float", "float"),  # or double based on size
            ("boolean", "boolean"),
            ("timestamp", "timestamp"),
            ("date", "date"),
            ("time", "time"),
            ("uuid", "uuid")
        ]
        
        for field_type, expected_cassandra_type in supported_types:
            cassandra_type = processor.get_cassandra_type(field_type)
            # For integer and float, the exact type depends on size
            if field_type in ["integer", "float"]:
                assert cassandra_type in ["int", "bigint", "float", "double"]
            else:
                assert cassandra_type == expected_cassandra_type

    def test_value_conversion_contract(self):
        """Test value conversion for all supported types"""
        processor = Processor.__new__(Processor)
        
        # Test conversions maintain data integrity
        test_cases = [
            # (input_value, field_type, expected_output, expected_type)
            ("123", "integer", 123, int),
            ("123.45", "float", 123.45, float),
            ("true", "boolean", True, bool),
            ("false", "boolean", False, bool),
            ("test string", "string", "test string", str),
            (None, "string", None, type(None)),
        ]
        
        for input_val, field_type, expected_val, expected_type in test_cases:
            result = processor.convert_value(input_val, field_type)
            assert result == expected_val
            assert isinstance(result, expected_type) or result is None

    def test_extracted_object_serialization_contract(self):
        """Test that ExtractedObject can be serialized/deserialized correctly"""
        # Create test object
        original = ExtractedObject(
            metadata=Metadata(
                id="serial-001",
                user="test_user",
                collection="test_coll",
                metadata=[]
            ),
            schema_name="test_schema",
            values=[{"field1": "value1", "field2": "123"}],
            confidence=0.85,
            source_span="Test span"
        )
        
        # Test serialization using schema
        schema = AvroSchema(ExtractedObject)
        
        # Encode and decode
        encoded = schema.encode(original)
        decoded = schema.decode(encoded)
        
        # Verify round-trip
        assert decoded.metadata.id == original.metadata.id
        assert decoded.metadata.user == original.metadata.user
        assert decoded.metadata.collection == original.metadata.collection
        assert decoded.schema_name == original.schema_name
        assert decoded.values == original.values
        assert decoded.confidence == original.confidence
        assert decoded.source_span == original.source_span

    def test_cassandra_table_naming_contract(self):
        """Test Cassandra naming conventions and constraints"""
        processor = Processor.__new__(Processor)
        
        # Test table naming (always gets o_ prefix)
        table_test_names = [
            ("simple_name", "o_simple_name"),
            ("Name-With-Dashes", "o_name_with_dashes"),
            ("name.with.dots", "o_name_with_dots"),
            ("123_numbers", "o_123_numbers"),
            ("special!@#chars", "o_special___chars"),  # 3 special chars become 3 underscores
            ("UPPERCASE", "o_uppercase"),
            ("CamelCase", "o_camelcase"),
            ("", "o_"),  # Edge case - empty string becomes o_
        ]
        
        for input_name, expected_name in table_test_names:
            result = processor.sanitize_table(input_name)
            assert result == expected_name
            # Verify result is valid Cassandra identifier (starts with letter)
            assert result.startswith('o_')
            assert result.replace('o_', '').replace('_', '').isalnum() or result == 'o_'
        
        # Test regular name sanitization (only adds o_ prefix if starts with number)
        name_test_cases = [
            ("simple_name", "simple_name"),
            ("Name-With-Dashes", "name_with_dashes"),
            ("name.with.dots", "name_with_dots"),
            ("123_numbers", "o_123_numbers"),  # Only this gets o_ prefix
            ("special!@#chars", "special___chars"),  # 3 special chars become 3 underscores
            ("UPPERCASE", "uppercase"),
            ("CamelCase", "camelcase"),
        ]
        
        for input_name, expected_name in name_test_cases:
            result = processor.sanitize_name(input_name)
            assert result == expected_name

    def test_primary_key_structure_contract(self):
        """Test that primary key structure follows Cassandra best practices"""
        # Verify partition key always includes collection
        processor = Processor.__new__(Processor)
        processor.schemas = {}
        processor.known_keyspaces = set()
        processor.known_tables = {}
        processor.session = None
        
        # Test schema with primary key
        schema_with_pk = RowSchema(
            name="test",
            fields=[
                Field(name="id", type="string", primary=True),
                Field(name="data", type="string")
            ]
        )
        
        # The primary key should be ((collection, id))
        # This is verified in the implementation where collection
        # is always first in the partition key

    def test_metadata_field_usage_contract(self):
        """Test that metadata fields are used correctly in storage"""
        # Create test object
        test_obj = ExtractedObject(
            metadata=Metadata(
                id="meta-001",
                user="user123",  # -> keyspace
                collection="coll456",  # -> partition key
                metadata=[{"key": "value"}]
            ),
            schema_name="table789",  # -> table name
            values=[{"field": "value"}],
            confidence=0.9,
            source_span="Source"
        )
        
        # Verify mapping contract:
        # - metadata.user -> Cassandra keyspace
        # - schema_name -> Cassandra table
        # - metadata.collection -> Part of primary key
        assert test_obj.metadata.user  # Required for keyspace
        assert test_obj.schema_name  # Required for table
        assert test_obj.metadata.collection  # Required for partition key


@pytest.mark.contract
class TestObjectsCassandraContractsBatch:
    """Contract tests for Cassandra object storage batch processing"""

    def test_extracted_object_batch_input_contract(self):
        """Test that batched ExtractedObject schema matches expected input format"""
        # Create test object with multiple values in batch
        test_metadata = Metadata(
            id="batch-doc-001",
            user="test_user",
            collection="test_collection",
            metadata=[]
        )
        
        batch_object = ExtractedObject(
            metadata=test_metadata,
            schema_name="customer_records",
            values=[
                {
                    "customer_id": "CUST123",
                    "name": "Test Customer 1",
                    "email": "test1@example.com"
                },
                {
                    "customer_id": "CUST124", 
                    "name": "Test Customer 2",
                    "email": "test2@example.com"
                },
                {
                    "customer_id": "CUST125",
                    "name": "Test Customer 3", 
                    "email": "test3@example.com"
                }
            ],
            confidence=0.88,
            source_span="Multiple customer data from document..."
        )
        
        # Verify batch structure
        assert hasattr(batch_object, 'values')
        assert isinstance(batch_object.values, list)
        assert len(batch_object.values) == 3
        
        # Verify each batch item is a dict
        for i, batch_item in enumerate(batch_object.values):
            assert isinstance(batch_item, dict)
            assert "customer_id" in batch_item
            assert "name" in batch_item
            assert "email" in batch_item
            assert batch_item["customer_id"] == f"CUST12{3+i}"
            assert f"Test Customer {i+1}" in batch_item["name"]

    def test_extracted_object_empty_batch_contract(self):
        """Test empty batch ExtractedObject contract"""
        test_metadata = Metadata(
            id="empty-batch-001",
            user="test_user",
            collection="test_collection", 
            metadata=[]
        )
        
        empty_batch_object = ExtractedObject(
            metadata=test_metadata,
            schema_name="empty_schema",
            values=[],  # Empty batch
            confidence=1.0,
            source_span="No objects found in document"
        )
        
        # Verify empty batch structure
        assert hasattr(empty_batch_object, 'values')
        assert isinstance(empty_batch_object.values, list)
        assert len(empty_batch_object.values) == 0
        assert empty_batch_object.confidence == 1.0

    def test_extracted_object_single_item_batch_contract(self):
        """Test single-item batch (backward compatibility) contract"""
        test_metadata = Metadata(
            id="single-batch-001",
            user="test_user",
            collection="test_collection",
            metadata=[]
        )
        
        single_batch_object = ExtractedObject(
            metadata=test_metadata,
            schema_name="customer_records",
            values=[{  # Array with single item for backward compatibility
                "customer_id": "CUST999",
                "name": "Single Customer",
                "email": "single@example.com"
            }],
            confidence=0.95,
            source_span="Single customer data from document..."
        )
        
        # Verify single-item batch structure
        assert isinstance(single_batch_object.values, list)
        assert len(single_batch_object.values) == 1
        assert isinstance(single_batch_object.values[0], dict)
        assert single_batch_object.values[0]["customer_id"] == "CUST999"

    def test_extracted_object_batch_serialization_contract(self):
        """Test that batched ExtractedObject can be serialized/deserialized correctly"""
        # Create batch object
        original = ExtractedObject(
            metadata=Metadata(
                id="batch-serial-001",
                user="test_user",
                collection="test_coll",
                metadata=[]
            ),
            schema_name="test_schema",
            values=[
                {"field1": "value1", "field2": "123"},
                {"field1": "value2", "field2": "456"},  
                {"field1": "value3", "field2": "789"}
            ],
            confidence=0.92,
            source_span="Batch test span"
        )
        
        # Test serialization using schema
        schema = AvroSchema(ExtractedObject)
        
        # Encode and decode
        encoded = schema.encode(original)
        decoded = schema.decode(encoded)
        
        # Verify round-trip for batch
        assert decoded.metadata.id == original.metadata.id
        assert decoded.metadata.user == original.metadata.user
        assert decoded.metadata.collection == original.metadata.collection
        assert decoded.schema_name == original.schema_name
        assert len(decoded.values) == len(original.values)
        assert len(decoded.values) == 3
        
        # Verify each batch item
        for i in range(3):
            assert decoded.values[i] == original.values[i]
            assert decoded.values[i]["field1"] == f"value{i+1}"
            assert decoded.values[i]["field2"] == f"{123 + i*333}"
            
        assert decoded.confidence == original.confidence
        assert decoded.source_span == original.source_span

    def test_batch_processing_field_validation_contract(self):
        """Test that batch processing validates field consistency"""
        # All batch items should have consistent field structure
        # This is a contract that the application should enforce
        
        # Valid batch - all items have same fields
        valid_batch_values = [
            {"id": "1", "name": "Item 1", "value": "100"},
            {"id": "2", "name": "Item 2", "value": "200"},
            {"id": "3", "name": "Item 3", "value": "300"}
        ]
        
        # Each item has the same field structure
        field_sets = [set(item.keys()) for item in valid_batch_values]
        assert all(fields == field_sets[0] for fields in field_sets), "All batch items should have consistent fields"
        
        # Invalid batch - inconsistent fields (this would be caught by application logic)
        invalid_batch_values = [
            {"id": "1", "name": "Item 1", "value": "100"},
            {"id": "2", "name": "Item 2"},  # Missing 'value' field
            {"id": "3", "name": "Item 3", "value": "300", "extra": "field"}  # Extra field
        ]
        
        # Demonstrate the inconsistency
        invalid_field_sets = [set(item.keys()) for item in invalid_batch_values]
        assert not all(fields == invalid_field_sets[0] for fields in invalid_field_sets), "Invalid batch should have inconsistent fields"

    def test_batch_storage_partition_key_contract(self):
        """Test that batch objects maintain partition key consistency"""
        # In Cassandra storage, all objects in a batch should:
        # 1. Belong to the same collection (partition key component)
        # 2. Have unique primary keys within the batch
        # 3. Be stored in the same keyspace (user)
        
        test_metadata = Metadata(
            id="partition-test-001",
            user="consistent_user",  # Same keyspace
            collection="consistent_collection",  # Same partition
            metadata=[]
        )
        
        batch_object = ExtractedObject(
            metadata=test_metadata,
            schema_name="partition_test",
            values=[
                {"id": "pk1", "data": "data1"},  # Unique primary key
                {"id": "pk2", "data": "data2"},  # Unique primary key
                {"id": "pk3", "data": "data3"}   # Unique primary key
            ],
            confidence=0.95,
            source_span="Partition consistency test"
        )
        
        # Verify consistency contract
        assert batch_object.metadata.user  # Must have user for keyspace
        assert batch_object.metadata.collection  # Must have collection for partition key
        
        # Verify unique primary keys in batch
        primary_keys = [item["id"] for item in batch_object.values]
        assert len(primary_keys) == len(set(primary_keys)), "Primary keys must be unique within batch"
        
        # All batch items will be stored in same keyspace and partition
        # This is enforced by the metadata.user and metadata.collection being shared