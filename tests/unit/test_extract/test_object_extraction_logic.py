"""
Standalone unit tests for Object Extraction Logic

Tests core object extraction logic without requiring full package imports.
This focuses on testing the business logic that would be used by the
object extraction processor components.
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any, List


class MockRowSchema:
    """Mock implementation of RowSchema for testing"""
    
    def __init__(self, name: str, description: str, fields: List['MockField']):
        self.name = name
        self.description = description
        self.fields = fields


class MockField:
    """Mock implementation of Field for testing"""
    
    def __init__(self, name: str, type: str, primary: bool = False, 
                 required: bool = False, indexed: bool = False, 
                 enum_values: List[str] = None, size: int = 0, 
                 description: str = ""):
        self.name = name
        self.type = type
        self.primary = primary
        self.required = required
        self.indexed = indexed
        self.enum_values = enum_values or []
        self.size = size
        self.description = description


class MockObjectExtractionLogic:
    """Mock implementation of object extraction logic for testing"""
    
    def __init__(self):
        self.schemas: Dict[str, MockRowSchema] = {}
    
    def convert_values_to_strings(self, obj: Dict[str, Any]) -> Dict[str, str]:
        """Convert all values in a dictionary to strings for Pulsar Map(String()) compatibility"""
        result = {}
        for key, value in obj.items():
            if value is None:
                result[key] = ""
            elif isinstance(value, str):
                result[key] = value
            elif isinstance(value, (int, float, bool)):
                result[key] = str(value)
            elif isinstance(value, (list, dict)):
                # For complex types, serialize as JSON
                result[key] = json.dumps(value)
            else:
                # For any other type, convert to string
                result[key] = str(value)
        return result
    
    def parse_schema_config(self, config: Dict[str, Dict[str, str]]) -> Dict[str, MockRowSchema]:
        """Parse schema configuration and create RowSchema objects"""
        schemas = {}
        
        if "schema" not in config:
            return schemas
        
        for schema_name, schema_json in config["schema"].items():
            try:
                schema_def = json.loads(schema_json)
                
                fields = []
                for field_def in schema_def.get("fields", []):
                    field = MockField(
                        name=field_def["name"],
                        type=field_def["type"],
                        size=field_def.get("size", 0),
                        primary=field_def.get("primary_key", False),
                        description=field_def.get("description", ""),
                        required=field_def.get("required", False),
                        enum_values=field_def.get("enum", []),
                        indexed=field_def.get("indexed", False)
                    )
                    fields.append(field)
                
                row_schema = MockRowSchema(
                    name=schema_def.get("name", schema_name),
                    description=schema_def.get("description", ""),
                    fields=fields
                )
                
                schemas[schema_name] = row_schema
                
            except Exception as e:
                # Skip invalid schemas
                continue
        
        return schemas
    
    def validate_extracted_object(self, obj_data: Dict[str, Any], schema: MockRowSchema) -> bool:
        """Validate extracted object against schema"""
        for field in schema.fields:
            # Check if required field is missing
            if field.required and field.name not in obj_data:
                return False
            
            if field.name in obj_data:
                value = obj_data[field.name]
                
                # Check required fields are not empty/None
                if field.required and (value is None or str(value).strip() == ""):
                    return False
                
                # Check enum constraints (only if value is not empty)
                if field.enum_values and value and value not in field.enum_values:
                    return False
                
                # Check primary key fields are not None/empty
                if field.primary and (value is None or str(value).strip() == ""):
                    return False
        
        return True
    
    def calculate_confidence(self, obj_data: Dict[str, Any], schema: MockRowSchema) -> float:
        """Calculate confidence score for extracted object"""
        total_fields = len(schema.fields)
        filled_fields = len([k for k, v in obj_data.items() if v and str(v).strip()])
        
        # Base confidence from field completeness
        completeness_score = filled_fields / total_fields if total_fields > 0 else 0
        
        # Bonus for primary key presence
        primary_key_bonus = 0.0
        for field in schema.fields:
            if field.primary and field.name in obj_data and obj_data[field.name]:
                primary_key_bonus = 0.1
                break
        
        # Penalty for enum violations
        enum_penalty = 0.0
        for field in schema.fields:
            if field.enum_values and field.name in obj_data:
                if obj_data[field.name] and obj_data[field.name] not in field.enum_values:
                    enum_penalty = 0.2
                    break
        
        confidence = min(1.0, completeness_score + primary_key_bonus - enum_penalty)
        return max(0.0, confidence)
    
    def generate_extracted_object_id(self, chunk_id: str, schema_name: str, obj_data: Dict[str, Any]) -> str:
        """Generate unique ID for extracted object"""
        return f"{chunk_id}:{schema_name}:{hash(str(obj_data))}"
    
    def create_source_span(self, text: str, max_length: int = 100) -> str:
        """Create source span reference from text"""
        return text[:max_length] if len(text) > max_length else text


class TestObjectExtractionLogic:
    """Test cases for object extraction business logic"""
    
    @pytest.fixture
    def extraction_logic(self):
        return MockObjectExtractionLogic()
    
    @pytest.fixture
    def sample_config(self):
        customer_schema = {
            "name": "customer_records",
            "description": "Customer information",
            "fields": [
                {
                    "name": "customer_id",
                    "type": "string",
                    "primary_key": True,
                    "required": True,
                    "indexed": True,
                    "description": "Customer ID"
                },
                {
                    "name": "name",
                    "type": "string",
                    "required": True,
                    "description": "Customer name"
                },
                {
                    "name": "email",
                    "type": "string",
                    "required": True,
                    "indexed": True,
                    "description": "Email address"
                },
                {
                    "name": "status",
                    "type": "string",
                    "required": False,
                    "indexed": True,
                    "enum": ["active", "inactive", "suspended"],
                    "description": "Account status"
                }
            ]
        }
        
        product_schema = {
            "name": "product_catalog",
            "description": "Product information",
            "fields": [
                {
                    "name": "sku",
                    "type": "string",
                    "primary_key": True,
                    "required": True,
                    "description": "Product SKU"
                },
                {
                    "name": "price",
                    "type": "float",
                    "size": 8,
                    "required": True,
                    "description": "Product price"
                }
            ]
        }
        
        return {
            "schema": {
                "customer_records": json.dumps(customer_schema),
                "product_catalog": json.dumps(product_schema)
            }
        }
    
    def test_convert_values_to_strings(self, extraction_logic):
        """Test value conversion for Pulsar compatibility"""
        # Arrange
        test_data = {
            "string_val": "hello",
            "int_val": 123,
            "float_val": 45.67,
            "bool_val": True,
            "none_val": None,
            "list_val": ["a", "b", "c"],
            "dict_val": {"nested": "value"}
        }
        
        # Act
        result = extraction_logic.convert_values_to_strings(test_data)
        
        # Assert
        assert result["string_val"] == "hello"
        assert result["int_val"] == "123"
        assert result["float_val"] == "45.67"
        assert result["bool_val"] == "True"
        assert result["none_val"] == ""
        assert result["list_val"] == '["a", "b", "c"]'
        assert result["dict_val"] == '{"nested": "value"}'
    
    def test_parse_schema_config_success(self, extraction_logic, sample_config):
        """Test successful schema configuration parsing"""
        # Act
        schemas = extraction_logic.parse_schema_config(sample_config)
        
        # Assert
        assert len(schemas) == 2
        assert "customer_records" in schemas
        assert "product_catalog" in schemas
        
        # Check customer schema details
        customer_schema = schemas["customer_records"]
        assert customer_schema.name == "customer_records"
        assert len(customer_schema.fields) == 4
        
        # Check primary key field
        primary_field = next((f for f in customer_schema.fields if f.primary), None)
        assert primary_field is not None
        assert primary_field.name == "customer_id"
        
        # Check enum field
        status_field = next((f for f in customer_schema.fields if f.name == "status"), None)
        assert status_field is not None
        assert len(status_field.enum_values) == 3
        assert "active" in status_field.enum_values
    
    def test_parse_schema_config_with_invalid_json(self, extraction_logic):
        """Test schema config parsing with invalid JSON"""
        # Arrange
        config = {
            "schema": {
                "valid_schema": json.dumps({"name": "valid", "fields": []}),
                "invalid_schema": "not valid json {"
            }
        }
        
        # Act
        schemas = extraction_logic.parse_schema_config(config)
        
        # Assert - only valid schema should be parsed
        assert len(schemas) == 1
        assert "valid_schema" in schemas
        assert "invalid_schema" not in schemas
    
    def test_validate_extracted_object_success(self, extraction_logic, sample_config):
        """Test successful object validation"""
        # Arrange
        schemas = extraction_logic.parse_schema_config(sample_config)
        customer_schema = schemas["customer_records"]
        
        valid_object = {
            "customer_id": "CUST001",
            "name": "John Doe",
            "email": "john@example.com",
            "status": "active"
        }
        
        # Act
        is_valid = extraction_logic.validate_extracted_object(valid_object, customer_schema)
        
        # Assert
        assert is_valid is True
    
    def test_validate_extracted_object_missing_required(self, extraction_logic, sample_config):
        """Test object validation with missing required fields"""
        # Arrange
        schemas = extraction_logic.parse_schema_config(sample_config)
        customer_schema = schemas["customer_records"]
        
        invalid_object = {
            "customer_id": "CUST001",
            # Missing required 'name' and 'email' fields
            "status": "active"
        }
        
        # Act
        is_valid = extraction_logic.validate_extracted_object(invalid_object, customer_schema)
        
        # Assert
        assert is_valid is False
    
    def test_validate_extracted_object_invalid_enum(self, extraction_logic, sample_config):
        """Test object validation with invalid enum value"""
        # Arrange
        schemas = extraction_logic.parse_schema_config(sample_config)
        customer_schema = schemas["customer_records"]
        
        invalid_object = {
            "customer_id": "CUST001",
            "name": "John Doe",
            "email": "john@example.com",
            "status": "invalid_status"  # Not in enum
        }
        
        # Act
        is_valid = extraction_logic.validate_extracted_object(invalid_object, customer_schema)
        
        # Assert
        assert is_valid is False
    
    def test_validate_extracted_object_empty_primary_key(self, extraction_logic, sample_config):
        """Test object validation with empty primary key"""
        # Arrange
        schemas = extraction_logic.parse_schema_config(sample_config)
        customer_schema = schemas["customer_records"]
        
        invalid_object = {
            "customer_id": "",  # Empty primary key
            "name": "John Doe",
            "email": "john@example.com",
            "status": "active"
        }
        
        # Act
        is_valid = extraction_logic.validate_extracted_object(invalid_object, customer_schema)
        
        # Assert
        assert is_valid is False
    
    def test_calculate_confidence_complete_object(self, extraction_logic, sample_config):
        """Test confidence calculation for complete object"""
        # Arrange
        schemas = extraction_logic.parse_schema_config(sample_config)
        customer_schema = schemas["customer_records"]
        
        complete_object = {
            "customer_id": "CUST001",
            "name": "John Doe",
            "email": "john@example.com",
            "status": "active"
        }
        
        # Act
        confidence = extraction_logic.calculate_confidence(complete_object, customer_schema)
        
        # Assert
        assert confidence > 0.9  # Should be high (1.0 completeness + 0.1 primary key bonus)
    
    def test_calculate_confidence_incomplete_object(self, extraction_logic, sample_config):
        """Test confidence calculation for incomplete object"""
        # Arrange
        schemas = extraction_logic.parse_schema_config(sample_config)
        customer_schema = schemas["customer_records"]
        
        incomplete_object = {
            "customer_id": "CUST001",
            "name": "John Doe"
            # Missing email and status
        }
        
        # Act
        confidence = extraction_logic.calculate_confidence(incomplete_object, customer_schema)
        
        # Assert
        assert confidence < 0.9  # Should be lower due to missing fields
        assert confidence > 0.0   # But not zero due to primary key bonus
    
    def test_calculate_confidence_invalid_enum(self, extraction_logic, sample_config):
        """Test confidence calculation with invalid enum value"""
        # Arrange
        schemas = extraction_logic.parse_schema_config(sample_config)
        customer_schema = schemas["customer_records"]
        
        invalid_enum_object = {
            "customer_id": "CUST001",
            "name": "John Doe",
            "email": "john@example.com",
            "status": "invalid_status"  # Invalid enum
        }
        
        # Act
        confidence = extraction_logic.calculate_confidence(invalid_enum_object, customer_schema)
        
        # Assert
        # Should be penalized for enum violation
        complete_confidence = extraction_logic.calculate_confidence({
            "customer_id": "CUST001",
            "name": "John Doe", 
            "email": "john@example.com",
            "status": "active"
        }, customer_schema)
        
        assert confidence < complete_confidence
    
    def test_generate_extracted_object_id(self, extraction_logic):
        """Test extracted object ID generation"""
        # Arrange
        chunk_id = "chunk-001"
        schema_name = "customer_records"
        obj_data = {"customer_id": "CUST001", "name": "John Doe"}
        
        # Act
        obj_id = extraction_logic.generate_extracted_object_id(chunk_id, schema_name, obj_data)
        
        # Assert
        assert chunk_id in obj_id
        assert schema_name in obj_id
        assert isinstance(obj_id, str)
        assert len(obj_id) > 20  # Should be reasonably long
        
        # Test consistency - same input should produce same ID
        obj_id2 = extraction_logic.generate_extracted_object_id(chunk_id, schema_name, obj_data)
        assert obj_id == obj_id2
    
    def test_create_source_span(self, extraction_logic):
        """Test source span creation"""
        # Test normal text
        short_text = "This is a short text"
        span = extraction_logic.create_source_span(short_text)
        assert span == short_text
        
        # Test long text truncation
        long_text = "x" * 200
        span = extraction_logic.create_source_span(long_text, max_length=100)
        assert len(span) == 100
        assert span == "x" * 100
        
        # Test custom max length
        span_custom = extraction_logic.create_source_span(long_text, max_length=50)
        assert len(span_custom) == 50
    
    def test_multi_schema_processing(self, extraction_logic, sample_config):
        """Test processing multiple schemas"""
        # Act
        schemas = extraction_logic.parse_schema_config(sample_config)
        
        # Test customer object
        customer_obj = {
            "customer_id": "CUST001",
            "name": "John Doe",
            "email": "john@example.com",
            "status": "active"
        }
        
        # Test product object  
        product_obj = {
            "sku": "PROD-001",
            "price": 29.99
        }
        
        # Assert both schemas work
        customer_valid = extraction_logic.validate_extracted_object(customer_obj, schemas["customer_records"])
        product_valid = extraction_logic.validate_extracted_object(product_obj, schemas["product_catalog"])
        
        assert customer_valid is True
        assert product_valid is True
        
        # Test confidence for both
        customer_confidence = extraction_logic.calculate_confidence(customer_obj, schemas["customer_records"])
        product_confidence = extraction_logic.calculate_confidence(product_obj, schemas["product_catalog"])
        
        assert customer_confidence > 0.9
        assert product_confidence > 0.9
    
    def test_edge_cases(self, extraction_logic):
        """Test edge cases in extraction logic"""
        # Empty schema config
        empty_schemas = extraction_logic.parse_schema_config({"other": {}})
        assert len(empty_schemas) == 0
        
        # Schema with no fields
        no_fields_config = {
            "schema": {
                "empty_schema": json.dumps({"name": "empty", "fields": []})
            }
        }
        schemas = extraction_logic.parse_schema_config(no_fields_config)
        assert len(schemas) == 1
        assert len(schemas["empty_schema"].fields) == 0
        
        # Confidence calculation with no fields
        confidence = extraction_logic.calculate_confidence({}, schemas["empty_schema"])
        assert confidence >= 0.0