"""
Unit tests for Object Validation Logic

Tests the validation logic for extracted objects against schemas,
including handling of nested JSON format issues and field validation.
"""

import pytest
import json
from trustgraph.schema import RowSchema, Field


@pytest.fixture
def cities_schema():
    """Cities schema matching the production schema"""
    fields = []
    
    # Create fields with proper attribute assignment
    f1 = Field()
    f1.name = "city"
    f1.type = "string"
    f1.primary = True
    f1.required = True
    f1.description = "City name"
    fields.append(f1)
    
    f2 = Field()
    f2.name = "country"
    f2.type = "string"
    f2.primary = True
    f2.required = True
    f2.description = "Country name"
    fields.append(f2)
    
    f3 = Field()
    f3.name = "population"
    f3.type = "integer"
    f3.primary = False
    f3.required = True
    f3.description = "Population count"
    fields.append(f3)
    
    f4 = Field()
    f4.name = "climate"
    f4.type = "string"
    f4.primary = False
    f4.required = True
    f4.description = "Climate type"
    fields.append(f4)
    
    f5 = Field()
    f5.name = "primary_language"
    f5.type = "string"
    f5.primary = False
    f5.required = True
    f5.description = "Primary language spoken"
    fields.append(f5)
    
    f6 = Field()
    f6.name = "currency"
    f6.type = "string"
    f6.primary = False
    f6.required = True
    f6.description = "Currency used"
    fields.append(f6)
    
    schema = RowSchema()
    schema.name = "Cities"
    schema.description = "City demographics"
    schema.fields = fields
    
    return schema


@pytest.fixture
def validator():
    """Create a mock processor with just the validation method"""
    from unittest.mock import MagicMock
    from trustgraph.extract.kg.objects.processor import Processor
    
    # Create a mock processor
    mock_processor = MagicMock()
    
    # Bind the validate_object method to the mock
    mock_processor.validate_object = Processor.validate_object.__get__(mock_processor, Processor)
    
    return mock_processor


class TestObjectValidation:
    """Test cases for object validation logic"""
    
    def test_valid_object_passes_validation(self, validator, cities_schema):
        """Test that a valid object passes validation"""
        valid_obj = {
            "city": "Shanghai",
            "country": "China",
            "population": "30482140",
            "climate": "Humid subtropical",
            "primary_language": "Mandarin Chinese",
            "currency": "Chinese Yuan (CNY)"
        }
        
        result = validator.validate_object(valid_obj, cities_schema, "Cities")
        assert result is True
    
    def test_nested_json_format_fails_validation(self, validator, cities_schema):
        """Test that nested JSON format is detected and fails validation"""
        nested_obj = {
            "Cities": '{"city": "Jakarta", "country": "Indonesia", "population": 11634078, "climate": "Tropical monsoon", "primary_language": "Indonesian", "currency": "Indonesian Rupiah (IDR)"}'
        }
        
        result = validator.validate_object( nested_obj, cities_schema, "Cities")
        assert result is False
    
    def test_missing_required_field_fails_validation(self, validator, cities_schema):
        """Test that missing required field fails validation"""
        missing_field_obj = {
            "city": "London",
            "country": "UK",
            "population": "9000000",
            "climate": "Temperate",
            # Missing primary_language (required)
            "currency": "GBP"
        }
        
        result = validator.validate_object( missing_field_obj, cities_schema, "Cities")
        assert result is False
    
    def test_null_primary_key_fails_validation(self, validator, cities_schema):
        """Test that null primary key field fails validation"""
        null_primary_obj = {
            "city": None,  # Primary key is null
            "country": "France",
            "population": "2000000",
            "climate": "Mediterranean",
            "primary_language": "French",
            "currency": "EUR"
        }
        
        result = validator.validate_object( null_primary_obj, cities_schema, "Cities")
        assert result is False
    
    def test_missing_primary_key_fails_validation(self, validator, cities_schema):
        """Test that missing primary key field fails validation"""
        missing_primary_obj = {
            # Missing city (primary key)
            "country": "Spain",
            "population": "3000000",
            "climate": "Mediterranean",
            "primary_language": "Spanish",
            "currency": "EUR"
        }
        
        result = validator.validate_object( missing_primary_obj, cities_schema, "Cities")
        assert result is False
    
    def test_invalid_integer_type_fails_validation(self, validator, cities_schema):
        """Test that invalid integer value fails validation"""
        invalid_type_obj = {
            "city": "Tokyo",
            "country": "Japan",
            "population": "not_a_number",  # Invalid integer
            "climate": "Humid subtropical",
            "primary_language": "Japanese",
            "currency": "JPY"
        }
        
        result = validator.validate_object( invalid_type_obj, cities_schema, "Cities")
        assert result is False
    
    def test_numeric_string_for_integer_passes_validation(self, validator, cities_schema):
        """Test that numeric string for integer field passes validation"""
        numeric_string_obj = {
            "city": "Beijing",
            "country": "China",
            "population": "21540000",  # String that can be converted to int
            "climate": "Continental",
            "primary_language": "Mandarin",
            "currency": "CNY"
        }
        
        result = validator.validate_object( numeric_string_obj, cities_schema, "Cities")
        assert result is True
    
    def test_integer_value_for_integer_field_passes_validation(self, validator, cities_schema):
        """Test that actual integer value for integer field passes validation"""
        integer_obj = {
            "city": "Mumbai",
            "country": "India",
            "population": 20185064,  # Actual integer
            "climate": "Tropical",
            "primary_language": "Hindi",
            "currency": "INR"
        }
        
        result = validator.validate_object( integer_obj, cities_schema, "Cities")
        assert result is True
    
    def test_non_dict_object_fails_validation(self, validator, cities_schema):
        """Test that non-dictionary object fails validation"""
        non_dict_obj = "This is not a dictionary"
        
        result = validator.validate_object( non_dict_obj, cities_schema, "Cities")
        assert result is False
    
    def test_optional_field_missing_passes_validation(self, validator):
        """Test that missing optional field passes validation"""
        # Create schema with optional field
        fields = [
            Field(name="id", type="string", primary=True, required=True),
            Field(name="name", type="string", required=True),
            Field(name="description", type="string", required=False),  # Optional
        ]
        schema = RowSchema(name="TestSchema", fields=fields)
        
        obj = {
            "id": "123",
            "name": "Test Name",
            # description is missing but optional
        }
        
        result = validator.validate_object( obj, schema, "TestSchema")
        assert result is True
    
    def test_float_type_validation(self, validator):
        """Test float type validation"""
        fields = [
            Field(name="id", type="string", primary=True, required=True),
            Field(name="price", type="float", required=True),
        ]
        schema = RowSchema(name="Product", fields=fields)
        
        # Valid float as string
        obj1 = {"id": "1", "price": "19.99"}
        assert validator.validate_object( obj1, schema, "Product") is True
        
        # Valid float
        obj2 = {"id": "2", "price": 19.99}
        assert validator.validate_object( obj2, schema, "Product") is True
        
        # Valid integer (can be float)
        obj3 = {"id": "3", "price": 20}
        assert validator.validate_object( obj3, schema, "Product") is True
        
        # Invalid float
        obj4 = {"id": "4", "price": "not_a_float"}
        assert validator.validate_object( obj4, schema, "Product") is False
    
    def test_boolean_type_validation(self, validator):
        """Test boolean type validation"""
        fields = [
            Field(name="id", type="string", primary=True, required=True),
            Field(name="active", type="boolean", required=True),
        ]
        schema = RowSchema(name="User", fields=fields)
        
        # Valid boolean
        obj1 = {"id": "1", "active": True}
        assert validator.validate_object( obj1, schema, "User") is True
        
        # Valid boolean as string
        obj2 = {"id": "2", "active": "true"}
        assert validator.validate_object( obj2, schema, "User") is True
        
        # Valid boolean as integer
        obj3 = {"id": "3", "active": 1}
        assert validator.validate_object( obj3, schema, "User") is True
        
        # Invalid boolean type
        obj4 = {"id": "4", "active": []}
        assert validator.validate_object( obj4, schema, "User") is False