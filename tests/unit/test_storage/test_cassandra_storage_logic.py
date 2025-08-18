"""
Standalone unit tests for Cassandra Storage Logic

Tests core Cassandra storage logic without requiring full package imports.
This focuses on testing the business logic that would be used by the
Cassandra object storage processor components.
"""

import pytest
import json
import re
from unittest.mock import Mock
from typing import Dict, Any, List


class MockField:
    """Mock implementation of Field for testing"""
    
    def __init__(self, name: str, type: str, primary: bool = False, 
                 required: bool = False, indexed: bool = False, 
                 enum_values: List[str] = None, size: int = 0):
        self.name = name
        self.type = type
        self.primary = primary
        self.required = required
        self.indexed = indexed
        self.enum_values = enum_values or []
        self.size = size


class MockRowSchema:
    """Mock implementation of RowSchema for testing"""
    
    def __init__(self, name: str, description: str, fields: List[MockField]):
        self.name = name
        self.description = description
        self.fields = fields


class MockCassandraStorageLogic:
    """Mock implementation of Cassandra storage logic for testing"""
    
    def __init__(self):
        self.known_keyspaces = set()
        self.known_tables = {}  # keyspace -> set of table names
    
    def sanitize_name(self, name: str) -> str:
        """Sanitize names for Cassandra compatibility (keyspaces)"""
        # Replace non-alphanumeric characters with underscore
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        # Ensure it starts with a letter
        if safe_name and not safe_name[0].isalpha():
            safe_name = 'o_' + safe_name
        return safe_name.lower()
    
    def sanitize_table(self, name: str) -> str:
        """Sanitize table names for Cassandra compatibility"""
        # Replace non-alphanumeric characters with underscore
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        # Always prefix tables with o_
        safe_name = 'o_' + safe_name
        return safe_name.lower()
    
    def get_cassandra_type(self, field_type: str, size: int = 0) -> str:
        """Convert schema field type to Cassandra type"""
        # Handle None size
        if size is None:
            size = 0
        
        type_mapping = {
            "string": "text",
            "integer": "bigint" if size > 4 else "int",
            "float": "double" if size > 4 else "float",
            "boolean": "boolean",
            "timestamp": "timestamp",
            "date": "date",
            "time": "time",
            "uuid": "uuid"
        }
        
        return type_mapping.get(field_type, "text")
    
    def convert_value(self, value: Any, field_type: str) -> Any:
        """Convert value to appropriate type for Cassandra"""
        if value is None:
            return None
        
        try:
            if field_type == "integer":
                return int(value)
            elif field_type == "float":
                return float(value)
            elif field_type == "boolean":
                if isinstance(value, str):
                    return value.lower() in ('true', '1', 'yes')
                return bool(value)
            elif field_type == "timestamp":
                # Handle timestamp conversion if needed
                return value
            else:
                return str(value)
        except Exception:
            # Fallback to string conversion
            return str(value)
    
    def generate_table_cql(self, keyspace: str, table_name: str, schema: MockRowSchema) -> str:
        """Generate CREATE TABLE CQL statement"""
        safe_keyspace = self.sanitize_name(keyspace)
        safe_table = self.sanitize_table(table_name)
        
        # Build column definitions
        columns = ["collection text"]  # Collection is always part of table
        primary_key_fields = []
        
        for field in schema.fields:
            safe_field_name = self.sanitize_name(field.name)
            cassandra_type = self.get_cassandra_type(field.type, field.size)
            columns.append(f"{safe_field_name} {cassandra_type}")
            
            if field.primary:
                primary_key_fields.append(safe_field_name)
        
        # Build primary key - collection is always first in partition key
        if primary_key_fields:
            primary_key = f"PRIMARY KEY ((collection, {', '.join(primary_key_fields)}))"
        else:
            # If no primary key defined, use collection and a synthetic id
            columns.append("synthetic_id uuid")
            primary_key = "PRIMARY KEY ((collection, synthetic_id))"
        
        # Create table CQL
        create_table_cql = f"""
        CREATE TABLE IF NOT EXISTS {safe_keyspace}.{safe_table} (
            {', '.join(columns)},
            {primary_key}
        )
        """
        
        return create_table_cql.strip()
    
    def generate_index_cql(self, keyspace: str, table_name: str, schema: MockRowSchema) -> List[str]:
        """Generate CREATE INDEX CQL statements for indexed fields"""
        safe_keyspace = self.sanitize_name(keyspace)
        safe_table = self.sanitize_table(table_name)
        
        index_statements = []
        
        for field in schema.fields:
            if field.indexed and not field.primary:
                safe_field_name = self.sanitize_name(field.name)
                index_name = f"{safe_table}_{safe_field_name}_idx"
                create_index_cql = f"""
                CREATE INDEX IF NOT EXISTS {index_name}
                ON {safe_keyspace}.{safe_table} ({safe_field_name})
                """
                index_statements.append(create_index_cql.strip())
        
        return index_statements
    
    def generate_insert_cql(self, keyspace: str, table_name: str, schema: MockRowSchema, 
                          values: Dict[str, Any], collection: str) -> tuple[str, tuple]:
        """Generate INSERT CQL statement and values tuple"""
        safe_keyspace = self.sanitize_name(keyspace)
        safe_table = self.sanitize_table(table_name)
        
        # Build column names and values
        columns = ["collection"]
        value_list = [collection]
        placeholders = ["%s"]
        
        # Check if we need a synthetic ID
        has_primary_key = any(field.primary for field in schema.fields)
        if not has_primary_key:
            import uuid
            columns.append("synthetic_id")
            value_list.append(uuid.uuid4())
            placeholders.append("%s")
        
        # Process fields
        for field in schema.fields:
            safe_field_name = self.sanitize_name(field.name)
            raw_value = values.get(field.name)
            
            # Convert value to appropriate type
            converted_value = self.convert_value(raw_value, field.type)
            
            columns.append(safe_field_name)
            value_list.append(converted_value)
            placeholders.append("%s")
        
        # Build insert query
        insert_cql = f"""
        INSERT INTO {safe_keyspace}.{safe_table} ({', '.join(columns)})
        VALUES ({', '.join(placeholders)})
        """
        
        return insert_cql.strip(), tuple(value_list)
    
    def validate_object_for_storage(self, obj_values: Dict[str, Any], schema: MockRowSchema) -> Dict[str, str]:
        """Validate object values for storage, return errors if any"""
        errors = {}
        
        # Check for missing required fields
        for field in schema.fields:
            if field.required and field.name not in obj_values:
                errors[field.name] = f"Required field '{field.name}' is missing"
            
            # Check primary key fields are not None/empty
            if field.primary and field.name in obj_values:
                value = obj_values[field.name]
                if value is None or str(value).strip() == "":
                    errors[field.name] = f"Primary key field '{field.name}' cannot be empty"
            
            # Check enum constraints
            if field.enum_values and field.name in obj_values:
                value = obj_values[field.name]
                if value and value not in field.enum_values:
                    errors[field.name] = f"Value '{value}' not in allowed enum values: {field.enum_values}"
        
        return errors


class TestCassandraStorageLogic:
    """Test cases for Cassandra storage business logic"""
    
    @pytest.fixture
    def storage_logic(self):
        return MockCassandraStorageLogic()
    
    @pytest.fixture
    def customer_schema(self):
        return MockRowSchema(
            name="customer_records",
            description="Customer information",
            fields=[
                MockField(
                    name="customer_id",
                    type="string",
                    primary=True,
                    required=True,
                    indexed=True
                ),
                MockField(
                    name="name",
                    type="string",
                    required=True
                ),
                MockField(
                    name="email",
                    type="string",
                    required=True,
                    indexed=True
                ),
                MockField(
                    name="age",
                    type="integer",
                    size=4
                ),
                MockField(
                    name="status",
                    type="string",
                    indexed=True,
                    enum_values=["active", "inactive", "suspended"]
                )
            ]
        )
    
    def test_sanitize_name_keyspace(self, storage_logic):
        """Test name sanitization for Cassandra keyspaces"""
        # Test various name patterns
        assert storage_logic.sanitize_name("simple_name") == "simple_name"
        assert storage_logic.sanitize_name("Name-With-Dashes") == "name_with_dashes"
        assert storage_logic.sanitize_name("name.with.dots") == "name_with_dots"
        assert storage_logic.sanitize_name("123_starts_with_number") == "o_123_starts_with_number"
        assert storage_logic.sanitize_name("name with spaces") == "name_with_spaces"
        assert storage_logic.sanitize_name("special!@#$%^chars") == "special______chars"
    
    def test_sanitize_table_name(self, storage_logic):
        """Test table name sanitization"""
        # Tables always get o_ prefix
        assert storage_logic.sanitize_table("simple_name") == "o_simple_name"
        assert storage_logic.sanitize_table("Name-With-Dashes") == "o_name_with_dashes"
        assert storage_logic.sanitize_table("name.with.dots") == "o_name_with_dots"
        assert storage_logic.sanitize_table("123_starts_with_number") == "o_123_starts_with_number"
    
    def test_get_cassandra_type(self, storage_logic):
        """Test field type conversion to Cassandra types"""
        # Basic type mappings
        assert storage_logic.get_cassandra_type("string") == "text"
        assert storage_logic.get_cassandra_type("boolean") == "boolean"
        assert storage_logic.get_cassandra_type("timestamp") == "timestamp"
        assert storage_logic.get_cassandra_type("uuid") == "uuid"
        
        # Integer types with size hints
        assert storage_logic.get_cassandra_type("integer", size=2) == "int"
        assert storage_logic.get_cassandra_type("integer", size=8) == "bigint"
        
        # Float types with size hints
        assert storage_logic.get_cassandra_type("float", size=2) == "float"
        assert storage_logic.get_cassandra_type("float", size=8) == "double"
        
        # Unknown type defaults to text
        assert storage_logic.get_cassandra_type("unknown_type") == "text"
    
    def test_convert_value(self, storage_logic):
        """Test value conversion for different field types"""
        # Integer conversions
        assert storage_logic.convert_value("123", "integer") == 123
        assert storage_logic.convert_value(123.5, "integer") == 123
        assert storage_logic.convert_value(None, "integer") is None
        
        # Float conversions
        assert storage_logic.convert_value("123.45", "float") == 123.45
        assert storage_logic.convert_value(123, "float") == 123.0
        
        # Boolean conversions
        assert storage_logic.convert_value("true", "boolean") is True
        assert storage_logic.convert_value("false", "boolean") is False
        assert storage_logic.convert_value("1", "boolean") is True
        assert storage_logic.convert_value("0", "boolean") is False
        assert storage_logic.convert_value("yes", "boolean") is True
        assert storage_logic.convert_value("no", "boolean") is False
        
        # String conversions
        assert storage_logic.convert_value(123, "string") == "123"
        assert storage_logic.convert_value(True, "string") == "True"
    
    def test_generate_table_cql(self, storage_logic, customer_schema):
        """Test CREATE TABLE CQL generation"""
        # Act
        cql = storage_logic.generate_table_cql("test_user", "customer_records", customer_schema)
        
        # Assert
        assert "CREATE TABLE IF NOT EXISTS test_user.o_customer_records" in cql
        assert "collection text" in cql
        assert "customer_id text" in cql
        assert "name text" in cql
        assert "email text" in cql
        assert "age int" in cql
        assert "status text" in cql
        assert "PRIMARY KEY ((collection, customer_id))" in cql
    
    def test_generate_table_cql_without_primary_key(self, storage_logic):
        """Test table creation when no primary key is defined"""
        # Arrange
        schema = MockRowSchema(
            name="events",
            description="Event log",
            fields=[
                MockField(name="event_type", type="string"),
                MockField(name="timestamp", type="timestamp")
            ]
        )
        
        # Act
        cql = storage_logic.generate_table_cql("test_user", "events", schema)
        
        # Assert
        assert "synthetic_id uuid" in cql
        assert "PRIMARY KEY ((collection, synthetic_id))" in cql
    
    def test_generate_index_cql(self, storage_logic, customer_schema):
        """Test CREATE INDEX CQL generation"""
        # Act
        index_statements = storage_logic.generate_index_cql("test_user", "customer_records", customer_schema)
        
        # Assert
        # Should create indexes for customer_id, email, and status (indexed fields)
        # But not for customer_id since it's also primary
        assert len(index_statements) == 2  # email and status
        
        # Check index creation
        index_texts = " ".join(index_statements)
        assert "o_customer_records_email_idx" in index_texts
        assert "o_customer_records_status_idx" in index_texts
        assert "CREATE INDEX IF NOT EXISTS" in index_texts
        assert "customer_id" not in index_texts  # Primary keys don't get indexes
    
    def test_generate_insert_cql(self, storage_logic, customer_schema):
        """Test INSERT CQL generation"""
        # Arrange
        values = {
            "customer_id": "CUST001",
            "name": "John Doe",
            "email": "john@example.com",
            "age": 30,
            "status": "active"
        }
        collection = "test_collection"
        
        # Act
        insert_cql, value_tuple = storage_logic.generate_insert_cql(
            "test_user", "customer_records", customer_schema, values, collection
        )
        
        # Assert
        assert "INSERT INTO test_user.o_customer_records" in insert_cql
        assert "collection" in insert_cql
        assert "customer_id" in insert_cql
        assert "VALUES" in insert_cql
        assert "%s" in insert_cql
        
        # Check values tuple
        assert value_tuple[0] == "test_collection"  # collection
        assert "CUST001" in value_tuple  # customer_id
        assert "John Doe" in value_tuple  # name
        assert 30 in value_tuple  # age (converted to int)
    
    def test_generate_insert_cql_without_primary_key(self, storage_logic):
        """Test INSERT CQL generation for schema without primary key"""
        # Arrange
        schema = MockRowSchema(
            name="events",
            description="Event log",
            fields=[MockField(name="event_type", type="string")]
        )
        values = {"event_type": "login"}
        
        # Act
        insert_cql, value_tuple = storage_logic.generate_insert_cql(
            "test_user", "events", schema, values, "test_collection"
        )
        
        # Assert
        assert "synthetic_id" in insert_cql
        assert len(value_tuple) == 3  # collection, synthetic_id, event_type
        # Check that synthetic_id is a UUID (has correct format)
        import uuid
        assert isinstance(value_tuple[1], uuid.UUID)
    
    def test_validate_object_for_storage_success(self, storage_logic, customer_schema):
        """Test successful object validation for storage"""
        # Arrange
        valid_values = {
            "customer_id": "CUST001",
            "name": "John Doe",
            "email": "john@example.com",
            "age": 30,
            "status": "active"
        }
        
        # Act
        errors = storage_logic.validate_object_for_storage(valid_values, customer_schema)
        
        # Assert
        assert len(errors) == 0
    
    def test_validate_object_missing_required_fields(self, storage_logic, customer_schema):
        """Test object validation with missing required fields"""
        # Arrange
        invalid_values = {
            "customer_id": "CUST001",
            # Missing required 'name' and 'email' fields
            "status": "active"
        }
        
        # Act
        errors = storage_logic.validate_object_for_storage(invalid_values, customer_schema)
        
        # Assert
        assert len(errors) == 2
        assert "name" in errors
        assert "email" in errors
        assert "Required field" in errors["name"]
    
    def test_validate_object_empty_primary_key(self, storage_logic, customer_schema):
        """Test object validation with empty primary key"""
        # Arrange
        invalid_values = {
            "customer_id": "",  # Empty primary key
            "name": "John Doe",
            "email": "john@example.com",
            "status": "active"
        }
        
        # Act
        errors = storage_logic.validate_object_for_storage(invalid_values, customer_schema)
        
        # Assert
        assert len(errors) == 1
        assert "customer_id" in errors
        assert "Primary key field" in errors["customer_id"]
        assert "cannot be empty" in errors["customer_id"]
    
    def test_validate_object_invalid_enum(self, storage_logic, customer_schema):
        """Test object validation with invalid enum value"""
        # Arrange
        invalid_values = {
            "customer_id": "CUST001",
            "name": "John Doe",
            "email": "john@example.com",
            "status": "invalid_status"  # Not in enum
        }
        
        # Act
        errors = storage_logic.validate_object_for_storage(invalid_values, customer_schema)
        
        # Assert
        assert len(errors) == 1
        assert "status" in errors
        assert "not in allowed enum values" in errors["status"]
    
    def test_complex_schema_with_all_features(self, storage_logic):
        """Test complex schema with all field features"""
        # Arrange
        complex_schema = MockRowSchema(
            name="complex_table",
            description="Complex table with all features",
            fields=[
                MockField(name="id", type="uuid", primary=True, required=True),
                MockField(name="name", type="string", required=True, indexed=True),
                MockField(name="count", type="integer", size=8),
                MockField(name="price", type="float", size=8),
                MockField(name="active", type="boolean"),
                MockField(name="created", type="timestamp"),
                MockField(name="category", type="string", enum_values=["A", "B", "C"], indexed=True)
            ]
        )
        
        # Act - Generate table CQL
        table_cql = storage_logic.generate_table_cql("complex_db", "complex_table", complex_schema)
        
        # Act - Generate index CQL
        index_statements = storage_logic.generate_index_cql("complex_db", "complex_table", complex_schema)
        
        # Assert table creation
        assert "complex_db.o_complex_table" in table_cql
        assert "id uuid" in table_cql
        assert "count bigint" in table_cql  # size 8 -> bigint
        assert "price double" in table_cql  # size 8 -> double
        assert "active boolean" in table_cql
        assert "created timestamp" in table_cql
        assert "PRIMARY KEY ((collection, id))" in table_cql
        
        # Assert index creation (name and category are indexed, but not id since it's primary)
        assert len(index_statements) == 2
        index_text = " ".join(index_statements)
        assert "name_idx" in index_text
        assert "category_idx" in index_text
    
    def test_storage_workflow_simulation(self, storage_logic, customer_schema):
        """Test complete storage workflow simulation"""
        keyspace = "customer_db"
        table_name = "customers"
        collection = "import_batch_1"
        
        # Step 1: Generate table creation
        table_cql = storage_logic.generate_table_cql(keyspace, table_name, customer_schema)
        assert "CREATE TABLE IF NOT EXISTS" in table_cql
        
        # Step 2: Generate indexes
        index_statements = storage_logic.generate_index_cql(keyspace, table_name, customer_schema)
        assert len(index_statements) > 0
        
        # Step 3: Validate and insert object
        customer_data = {
            "customer_id": "CUST001",
            "name": "John Doe",
            "email": "john@example.com",
            "age": 35,
            "status": "active"
        }
        
        # Validate
        errors = storage_logic.validate_object_for_storage(customer_data, customer_schema)
        assert len(errors) == 0
        
        # Generate insert
        insert_cql, values = storage_logic.generate_insert_cql(
            keyspace, table_name, customer_schema, customer_data, collection
        )
        
        assert "customer_db.o_customers" in insert_cql
        assert values[0] == collection
        assert "CUST001" in values
        assert "John Doe" in values