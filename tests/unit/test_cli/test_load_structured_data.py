"""
Unit tests for tg-load-structured-data CLI command.
Tests all modes: suggest-schema, generate-descriptor, parse-only, full pipeline.
"""

import pytest
import json
import tempfile
import os
import csv
import xml.etree.ElementTree as ET
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
from io import StringIO
import asyncio

# Import the function we're testing
from trustgraph.cli.load_structured_data import (
    load_structured_data,
    parse_csv_data,
    parse_json_data, 
    parse_xml_data,
    apply_transformations
)


class TestLoadStructuredDataUnit:
    """Unit tests for load_structured_data functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.test_csv_data = """name,email,age,country
John Smith,john@email.com,35,US
Jane Doe,jane@email.com,28,CA
Bob Johnson,bob@company.org,42,UK"""
        
        self.test_json_data = [
            {"name": "John Smith", "email": "john@email.com", "age": 35, "country": "US"},
            {"name": "Jane Doe", "email": "jane@email.com", "age": 28, "country": "CA"}
        ]
        
        self.test_xml_data = """<?xml version="1.0"?>
<ROOT>
    <data>
        <record>
            <field name="name">John Smith</field>
            <field name="email">john@email.com</field>
            <field name="age">35</field>
        </record>
        <record>
            <field name="name">Jane Doe</field>
            <field name="email">jane@email.com</field>
            <field name="age">28</field>
        </record>
    </data>
</ROOT>"""
        
        self.test_descriptor = {
            "version": "1.0",
            "format": {"type": "csv", "encoding": "utf-8", "options": {"header": True}},
            "mappings": [
                {"source_field": "name", "target_field": "name", "transforms": [{"type": "trim"}]},
                {"source_field": "email", "target_field": "email", "transforms": [{"type": "lower"}]}
            ],
            "output": {
                "format": "trustgraph-objects",
                "schema_name": "customer",
                "options": {"confidence": 0.9, "batch_size": 100}
            }
        }
    
    # CSV Parsing Tests
    def test_csv_parsing_with_header(self):
        """Test CSV parsing with header row"""
        format_info = {"type": "csv", "encoding": "utf-8", "options": {"header": True, "delimiter": ","}}
        
        records = parse_csv_data(self.test_csv_data, format_info)
        
        assert len(records) == 3
        assert records[0]["name"] == "John Smith"
        assert records[0]["email"] == "john@email.com"
        assert records[1]["country"] == "CA"
    
    def test_csv_parsing_without_header(self):
        """Test CSV parsing without header row"""
        csv_data = """John Smith,john@email.com,35,US
Jane Doe,jane@email.com,28,CA"""
        format_info = {"type": "csv", "encoding": "utf-8", "options": {"header": False, "delimiter": ","}}
        
        records = parse_csv_data(csv_data, format_info)
        
        assert len(records) == 2
        # Should use column indices as keys
        assert records[0]["0"] == "John Smith"
        assert records[0]["1"] == "john@email.com"
    
    def test_csv_parsing_custom_delimiter(self):
        """Test CSV parsing with custom delimiter"""
        csv_data = """name;email;age
John Smith;john@email.com;35
Jane Doe;jane@email.com;28"""
        format_info = {"type": "csv", "encoding": "utf-8", "options": {"header": True, "delimiter": ";"}}
        
        records = parse_csv_data(csv_data, format_info)
        
        assert len(records) == 2
        assert records[0]["name"] == "John Smith"
        assert records[1]["email"] == "jane@email.com"
    
    # JSON Parsing Tests
    def test_json_parsing_array_format(self):
        """Test JSON parsing with array format"""
        json_data = json.dumps(self.test_json_data)
        format_info = {"type": "json", "encoding": "utf-8"}
        
        records = parse_json_data(json_data, format_info)
        
        assert len(records) == 2
        assert records[0]["name"] == "John Smith"
        assert records[1]["country"] == "CA"
    
    def test_json_parsing_newline_delimited(self):
        """Test JSON parsing with newline-delimited format"""
        json_data = '{"name": "John", "age": 35}\n{"name": "Jane", "age": 28}'
        format_info = {"type": "json", "encoding": "utf-8", "options": {"newline_delimited": True}}
        
        records = parse_json_data(json_data, format_info)
        
        assert len(records) == 2
        assert records[0]["name"] == "John"
        assert records[1]["age"] == 28
    
    def test_json_parsing_malformed_data(self):
        """Test JSON parsing with malformed data"""
        json_data = '{"name": "John", "age": 35'  # Missing closing brace
        format_info = {"type": "json", "encoding": "utf-8"}
        
        with pytest.raises(json.JSONDecodeError):
            parse_json_data(json_data, format_info)
    
    # XML Parsing Tests
    def test_xml_parsing_xpath_expressions(self):
        """Test XML parsing with XPath expressions"""
        format_info = {
            "type": "xml", 
            "encoding": "utf-8",
            "options": {
                "record_path": "/ROOT/data/record",
                "field_attribute": "name"
            }
        }
        
        records = parse_xml_data(self.test_xml_data, format_info)
        
        assert len(records) == 2
        assert records[0]["name"] == "John Smith"
        assert records[0]["email"] == "john@email.com"
        assert records[1]["name"] == "Jane Doe"
    
    def test_xml_parsing_field_attributes(self):
        """Test XML parsing with field attributes"""
        xml_data = """<?xml version="1.0"?>
<records>
    <item id="1" name="Product A" price="19.99"/>
    <item id="2" name="Product B" price="29.99"/>
</records>"""
        
        format_info = {
            "type": "xml",
            "encoding": "utf-8", 
            "options": {"record_path": "//item"}
        }
        
        records = parse_xml_data(xml_data, format_info)
        
        assert len(records) == 2
        assert records[0]["id"] == "1"
        assert records[0]["name"] == "Product A"
        assert records[1]["price"] == "29.99"
    
    # Data Transformation Tests
    def test_field_mappings_application(self):
        """Test field mapping application"""
        record = {"source_name": "John Smith", "source_email": "JOHN@EMAIL.COM"}
        mappings = [
            {"source_field": "source_name", "target_field": "name", "transforms": []},
            {"source_field": "source_email", "target_field": "email", "transforms": []}
        ]
        
        result = apply_transformations(record, mappings)
        
        assert result["name"] == "John Smith"
        assert result["email"] == "JOHN@EMAIL.COM"
    
    def test_data_transforms_trim(self):
        """Test trim transformation"""
        record = {"name": "  John Smith  ", "email": "john@email.com"}
        mappings = [
            {"source_field": "name", "target_field": "name", "transforms": [{"type": "trim"}]}
        ]
        
        result = apply_transformations(record, mappings)
        
        assert result["name"] == "John Smith"
    
    def test_data_transforms_case_conversion(self):
        """Test case conversion transformations"""
        record = {"name": "John Smith", "email": "JOHN@EMAIL.COM"}
        mappings = [
            {"source_field": "name", "target_field": "name", "transforms": [{"type": "upper"}]},
            {"source_field": "email", "target_field": "email", "transforms": [{"type": "lower"}]}
        ]
        
        result = apply_transformations(record, mappings)
        
        assert result["name"] == "JOHN SMITH"
        assert result["email"] == "john@email.com"
    
    def test_data_transforms_type_conversion(self):
        """Test type conversion transformations"""
        record = {"age": "35", "price": "19.99", "active": "true"}
        mappings = [
            {"source_field": "age", "target_field": "age", "transforms": [{"type": "to_int"}]},
            {"source_field": "price", "target_field": "price", "transforms": [{"type": "to_float"}]},
            {"source_field": "active", "target_field": "active", "transforms": [{"type": "to_bool"}]}
        ]
        
        result = apply_transformations(record, mappings)
        
        # All values should be converted to strings for ExtractedObject compatibility
        assert result["age"] == "35"
        assert result["price"] == "19.99"
        assert result["active"] == "True"
    
    # Batching Functionality Tests
    def test_batch_processing_single_object(self):
        """Test batch processing with single object"""
        records = [{"name": "John", "age": "35"}]
        batch_size = 10
        schema_name = "customer"
        
        # Simulate batching logic
        batches = []
        for i in range(0, len(records), batch_size):
            batch_records = records[i:i + batch_size]
            batch_values = [record for record in batch_records]
            batches.append({
                "schema_name": schema_name,
                "values": batch_values
            })
        
        assert len(batches) == 1
        assert len(batches[0]["values"]) == 1
        assert batches[0]["values"][0]["name"] == "John"
    
    def test_batch_processing_multiple_objects(self):
        """Test batch processing with multiple objects"""
        records = [{"name": f"User{i}", "age": str(20+i)} for i in range(5)]
        batch_size = 2
        schema_name = "customer"
        
        # Simulate batching logic
        batches = []
        for i in range(0, len(records), batch_size):
            batch_records = records[i:i + batch_size]
            batch_values = [record for record in batch_records]
            batches.append({
                "schema_name": schema_name,
                "values": batch_values
            })
        
        assert len(batches) == 3  # 5 records with batch_size=2 -> 3 batches
        assert len(batches[0]["values"]) == 2
        assert len(batches[1]["values"]) == 2
        assert len(batches[2]["values"]) == 1
        assert batches[2]["values"][0]["name"] == "User4"
    
    def test_batch_size_configuration(self):
        """Test batch size configuration"""
        records = [{"id": str(i)} for i in range(10)]
        
        for batch_size in [1, 3, 5, 10, 15]:
            batches = []
            for i in range(0, len(records), batch_size):
                batch_records = records[i:i + batch_size]
                batches.append(batch_records)
            
            expected_batches = (len(records) + batch_size - 1) // batch_size
            assert len(batches) == expected_batches
            
            # Check all records are included
            total_records = sum(len(batch) for batch in batches)
            assert total_records == len(records)
    
    # Schema Suggestion Tests
    @patch('trustgraph.cli.load_structured_data.TrustGraphAPI')
    def test_suggest_schema_api_integration(self, mock_api_class):
        """Test schema suggestion with API integration"""
        # Setup mock API
        mock_api = Mock()
        mock_api_class.return_value = mock_api
        mock_config_api = Mock()
        mock_api.config.return_value = mock_config_api
        mock_config_api.get_config_items.return_value = {"schema": {"customer": '{"name": "customer"}'}}
        
        mock_flow = Mock()
        mock_api.flow.return_value = mock_flow
        mock_flow.id.return_value = mock_flow
        mock_prompt_client = Mock()
        mock_flow.prompt.return_value = mock_prompt_client
        mock_prompt_client.schema_selection.return_value = "customer schema looks best for this data"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(self.test_csv_data)
            f.flush()
            
            try:
                # This should not raise an exception
                result = load_structured_data(
                    api_url="http://localhost:8088",
                    input_file=f.name,
                    suggest_schema=True,
                    sample_size=100,
                    sample_chars=500
                )
                
                # Verify API calls were made
                mock_config_api.get_config_items.assert_called_once()
                mock_prompt_client.schema_selection.assert_called_once()
                
            finally:
                os.unlink(f.name)
    
    # Descriptor Generation Tests  
    @patch('trustgraph.cli.load_structured_data.TrustGraphAPI')
    def test_generate_descriptor_csv_format(self, mock_api_class):
        """Test descriptor generation for CSV format"""
        # Setup mock API
        mock_api = Mock()
        mock_api_class.return_value = mock_api
        mock_config_api = Mock()
        mock_api.config.return_value = mock_config_api
        mock_config_api.get_config_items.return_value = {"schema": {"customer": '{"name": "customer"}'}}
        
        mock_flow = Mock()
        mock_api.flow.return_value = mock_flow
        mock_flow.id.return_value = mock_flow
        mock_prompt_client = Mock()
        mock_flow.prompt.return_value = mock_prompt_client
        mock_prompt_client.diagnose_structured_data.return_value = json.dumps(self.test_descriptor)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(self.test_csv_data)
            f.flush()
            
            try:
                result = load_structured_data(
                    api_url="http://localhost:8088",
                    input_file=f.name,
                    generate_descriptor=True,
                    sample_chars=500
                )
                
                # Verify API calls were made
                mock_prompt_client.diagnose_structured_data.assert_called_once()
                
            finally:
                os.unlink(f.name)
    
    # Error Handling Tests
    def test_file_not_found_error(self):
        """Test handling of file not found error"""
        with pytest.raises(FileNotFoundError):
            load_structured_data(
                api_url="http://localhost:8088",
                input_file="/nonexistent/file.csv"
            )
    
    def test_invalid_descriptor_format(self):
        """Test handling of invalid descriptor format"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as input_file:
            input_file.write(self.test_csv_data)
            input_file.flush()
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as desc_file:
                desc_file.write('{"invalid": "descriptor"}')  # Missing required fields
                desc_file.flush()
                
                try:
                    with pytest.raises((KeyError, ValueError)):
                        load_structured_data(
                            api_url="http://localhost:8088",
                            input_file=input_file.name,
                            descriptor_file=desc_file.name
                        )
                finally:
                    os.unlink(input_file.name)
                    os.unlink(desc_file.name)
    
    def test_parsing_errors_handling(self):
        """Test handling of parsing errors"""
        invalid_csv = "name,email\n\"unclosed quote,test@email.com"
        format_info = {"type": "csv", "encoding": "utf-8", "options": {"header": True}}
        
        # Should handle parsing errors gracefully
        with pytest.raises(Exception):
            parse_csv_data(invalid_csv, format_info)
    
    # Validation Tests
    def test_validation_rules_required_fields(self):
        """Test validation rules for required fields"""
        record = {"name": "John", "email": ""}  # Missing required email
        mappings = [
            {
                "source_field": "name", 
                "target_field": "name", 
                "transforms": [],
                "validation": [{"type": "required"}]
            },
            {
                "source_field": "email", 
                "target_field": "email", 
                "transforms": [],
                "validation": [{"type": "required"}]
            }
        ]
        
        result = apply_transformations(record, mappings)
        
        # Should still process but may log warnings
        assert "name" in result
        assert "email" in result