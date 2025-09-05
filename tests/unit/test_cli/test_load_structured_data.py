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
from trustgraph.cli.load_structured_data import load_structured_data


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
    
    # CLI Dry-Run Tests - Test CLI behavior without actual connections
    def test_csv_dry_run_processing(self):
        """Test CSV processing in dry-run mode"""
        input_file = self.create_temp_file(self.test_csv_data, '.csv')
        descriptor_file = self.create_temp_file(json.dumps(self.test_descriptor), '.json')
        
        try:
            # Dry run should complete without errors
            result = load_structured_data(
                api_url="http://localhost:8088",
                input_file=input_file,
                descriptor_file=descriptor_file,
                dry_run=True,
                batch_size=2
            )
            
            # Dry run returns None
            assert result is None
            
        finally:
            self.cleanup_temp_file(input_file)
            self.cleanup_temp_file(descriptor_file)
    
    def test_parse_only_mode(self):
        """Test parse-only mode functionality"""
        input_file = self.create_temp_file(self.test_csv_data, '.csv')
        descriptor_file = self.create_temp_file(json.dumps(self.test_descriptor), '.json')
        output_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        output_file.close()
        
        try:
            result = load_structured_data(
                api_url="http://localhost:8088",
                input_file=input_file,
                descriptor_file=descriptor_file,
                parse_only=True,
                output_file=output_file.name
            )
            
            # Check output file was created
            assert os.path.exists(output_file.name)
            
            # Check it contains parsed data
            with open(output_file.name, 'r') as f:
                parsed_data = json.load(f)
                assert isinstance(parsed_data, list)
                assert len(parsed_data) > 0
                
        finally:
            self.cleanup_temp_file(input_file)
            self.cleanup_temp_file(descriptor_file)
            self.cleanup_temp_file(output_file.name)
    
    def test_batch_size_parameter(self):
        """Test batch size parameter is accepted"""
        input_file = self.create_temp_file(self.test_csv_data, '.csv')
        descriptor_file = self.create_temp_file(json.dumps(self.test_descriptor), '.json')
        
        try:
            # Should accept batch_size parameter without error
            result = load_structured_data(
                api_url="http://localhost:8088",
                input_file=input_file,
                descriptor_file=descriptor_file,
                batch_size=5,
                dry_run=True
            )
            
            assert result is None
            
        finally:
            self.cleanup_temp_file(input_file)
            self.cleanup_temp_file(descriptor_file)
    
    def create_temp_file(self, content, suffix='.txt'):
        """Create a temporary file with given content"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False)
        temp_file.write(content)
        temp_file.flush()
        temp_file.close()
        return temp_file.name
    
    def cleanup_temp_file(self, file_path):
        """Clean up temporary file"""
        try:
            os.unlink(file_path)
        except:
            pass
    
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