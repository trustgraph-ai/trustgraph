"""
Unit tests for schema suggestion and descriptor generation functionality in tg-load-structured-data.
Tests the --suggest-schema and --generate-descriptor modes.
"""

import pytest
import json
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock

from trustgraph.cli.load_structured_data import load_structured_data


class TestSchemaDescriptorGeneration:
    """Tests for schema suggestion and descriptor generation"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.api_url = "http://localhost:8088"
        
        # Sample data for different formats
        self.customer_csv = """name,email,age,country,registration_date,status
John Smith,john@email.com,35,USA,2024-01-15,active
Jane Doe,jane@email.com,28,Canada,2024-01-20,active
Bob Johnson,bob@company.org,42,UK,2024-01-10,inactive"""

        self.product_json = [
            {
                "id": "PROD001",
                "name": "Wireless Headphones", 
                "category": "Electronics",
                "price": 99.99,
                "in_stock": True,
                "specifications": {
                    "battery_life": "24 hours",
                    "wireless": True,
                    "noise_cancellation": True
                }
            },
            {
                "id": "PROD002",
                "name": "Coffee Maker",
                "category": "Home & Kitchen", 
                "price": 129.99,
                "in_stock": False,
                "specifications": {
                    "capacity": "12 cups",
                    "programmable": True,
                    "auto_shutoff": True
                }
            }
        ]
        
        self.trade_xml = """<?xml version="1.0"?>
<ROOT>
    <data>
        <record>
            <field name="country">USA</field>
            <field name="product">Wheat</field>
            <field name="quantity">1000000</field>
            <field name="value_usd">250000000</field>
            <field name="trade_type">export</field>
        </record>
        <record>
            <field name="country">China</field>
            <field name="product">Electronics</field>
            <field name="quantity">500000</field>
            <field name="value_usd">750000000</field>
            <field name="trade_type">import</field>
        </record>
    </data>
</ROOT>"""
        
        # Mock schema definitions
        self.mock_schemas = {
            "customer": json.dumps({
                "name": "customer",
                "description": "Customer information records",
                "fields": [
                    {"name": "name", "type": "string", "required": True},
                    {"name": "email", "type": "string", "required": True},
                    {"name": "age", "type": "integer"},
                    {"name": "country", "type": "string"},
                    {"name": "status", "type": "string"}
                ]
            }),
            "product": json.dumps({
                "name": "product", 
                "description": "Product catalog information",
                "fields": [
                    {"name": "id", "type": "string", "required": True, "primary_key": True},
                    {"name": "name", "type": "string", "required": True},
                    {"name": "category", "type": "string"},
                    {"name": "price", "type": "float"},
                    {"name": "in_stock", "type": "boolean"}
                ]
            }),
            "trade_data": json.dumps({
                "name": "trade_data",
                "description": "International trade statistics", 
                "fields": [
                    {"name": "country", "type": "string", "required": True},
                    {"name": "product", "type": "string", "required": True},
                    {"name": "quantity", "type": "integer"},
                    {"name": "value_usd", "type": "float"},
                    {"name": "trade_type", "type": "string"}
                ]
            }),
            "financial_record": json.dumps({
                "name": "financial_record",
                "description": "Financial transaction records",
                "fields": [
                    {"name": "transaction_id", "type": "string", "primary_key": True},
                    {"name": "amount", "type": "float", "required": True},
                    {"name": "currency", "type": "string"},
                    {"name": "date", "type": "timestamp"}
                ]
            })
        }
    
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
    def test_suggest_schema_csv_data(self, mock_api_class):
        """Test schema suggestion for CSV data"""
        # Setup mock API
        mock_api = Mock()
        mock_api_class.return_value = mock_api
        mock_config_api = Mock()
        mock_api.config.return_value = mock_config_api
        mock_config_api.get_config_items.return_value = {"schema": self.mock_schemas}
        
        mock_flow = Mock()
        mock_api.flow.return_value = mock_flow
        mock_flow.id.return_value = mock_flow
        mock_prompt_client = Mock()
        mock_flow.prompt.return_value = mock_prompt_client
        
        # Mock schema selection response
        mock_prompt_client.schema_selection.return_value = (
            "Based on the data containing customer names, emails, ages, and countries, "
            "the **customer** schema is the most appropriate choice. This schema includes "
            "all the necessary fields for customer information and aligns well with the "
            "structure of your data."
        )
        
        input_file = self.create_temp_file(self.customer_csv, '.csv')
        
        try:
            result = load_structured_data(
                api_url=self.api_url,
                input_file=input_file,
                suggest_schema=True,
                sample_size=100,
                sample_chars=500
            )
            
            # Verify API calls were made correctly
            mock_config_api.get_config_items.assert_called_once()
            mock_prompt_client.schema_selection.assert_called_once()
            
            # Check arguments passed to schema_selection
            call_args = mock_prompt_client.schema_selection.call_args
            assert 'schemas' in call_args.kwargs
            assert 'sample' in call_args.kwargs
            
            # Verify schemas were passed correctly
            passed_schemas = call_args.kwargs['schemas']
            assert len(passed_schemas) == len(self.mock_schemas)
            
            # Check sample data was included
            sample_data = call_args.kwargs['sample']
            assert 'John Smith' in sample_data
            assert 'jane@email.com' in sample_data
            
        finally:
            self.cleanup_temp_file(input_file)
    
    @patch('trustgraph.cli.load_structured_data.TrustGraphAPI')
    def test_suggest_schema_json_data(self, mock_api_class):
        """Test schema suggestion for JSON data"""
        mock_api = Mock()
        mock_api_class.return_value = mock_api
        mock_config_api = Mock()
        mock_api.config.return_value = mock_config_api
        mock_config_api.get_config_items.return_value = {"schema": self.mock_schemas}
        
        mock_flow = Mock()
        mock_api.flow.return_value = mock_flow
        mock_flow.id.return_value = mock_flow
        mock_prompt_client = Mock()
        mock_flow.prompt.return_value = mock_prompt_client
        
        mock_prompt_client.schema_selection.return_value = (
            "The **product** schema is ideal for this dataset containing product IDs, "
            "names, categories, prices, and stock status. This matches perfectly with "
            "the product schema structure."
        )
        
        input_file = self.create_temp_file(json.dumps(self.product_json), '.json')
        
        try:
            result = load_structured_data(
                api_url=self.api_url,
                input_file=input_file,
                suggest_schema=True,
                sample_chars=1000
            )
            
            # Verify the call was made
            mock_prompt_client.schema_selection.assert_called_once()
            
            # Check that JSON data was properly sampled
            call_args = mock_prompt_client.schema_selection.call_args
            sample_data = call_args.kwargs['sample']
            assert 'PROD001' in sample_data
            assert 'Wireless Headphones' in sample_data
            assert 'Electronics' in sample_data
            
        finally:
            self.cleanup_temp_file(input_file)
    
    @patch('trustgraph.cli.load_structured_data.TrustGraphAPI')
    def test_suggest_schema_xml_data(self, mock_api_class):
        """Test schema suggestion for XML data"""
        mock_api = Mock()
        mock_api_class.return_value = mock_api
        mock_config_api = Mock()
        mock_api.config.return_value = mock_config_api
        mock_config_api.get_config_items.return_value = {"schema": self.mock_schemas}
        
        mock_flow = Mock()
        mock_api.flow.return_value = mock_flow
        mock_flow.id.return_value = mock_flow
        mock_prompt_client = Mock()
        mock_flow.prompt.return_value = mock_prompt_client
        
        mock_prompt_client.schema_selection.return_value = (
            "The **trade_data** schema is the best fit for this XML data containing "
            "country, product, quantity, value, and trade type information. This aligns "
            "perfectly with international trade statistics."
        )
        
        input_file = self.create_temp_file(self.trade_xml, '.xml')
        
        try:
            result = load_structured_data(
                api_url=self.api_url,
                input_file=input_file,
                suggest_schema=True,
                sample_chars=800
            )
            
            mock_prompt_client.schema_selection.assert_called_once()
            
            # Verify XML content was included in sample
            call_args = mock_prompt_client.schema_selection.call_args
            sample_data = call_args.kwargs['sample']
            assert 'field name="country"' in sample_data or 'country' in sample_data
            assert 'USA' in sample_data
            assert 'export' in sample_data
            
        finally:
            self.cleanup_temp_file(input_file)
    
    @patch('trustgraph.cli.load_structured_data.TrustGraphAPI')
    def test_suggest_schema_sample_size_limiting(self, mock_api_class):
        """Test that sample size is properly limited"""
        mock_api = Mock()
        mock_api_class.return_value = mock_api
        mock_config_api = Mock()
        mock_api.config.return_value = mock_config_api
        mock_config_api.get_config_items.return_value = {"schema": self.mock_schemas}
        
        mock_flow = Mock()
        mock_api.flow.return_value = mock_flow
        mock_flow.id.return_value = mock_flow
        mock_prompt_client = Mock()
        mock_flow.prompt.return_value = mock_prompt_client
        mock_prompt_client.schema_selection.return_value = "customer schema recommended"
        
        # Create large CSV file
        large_csv = "name,email,age\n" + "\n".join([f"User{i},user{i}@example.com,{20+i}" for i in range(1000)])
        input_file = self.create_temp_file(large_csv, '.csv')
        
        try:
            result = load_structured_data(
                api_url=self.api_url,
                input_file=input_file,
                suggest_schema=True,
                sample_size=10,  # Limit to 10 records
                sample_chars=200  # Limit to 200 characters
            )
            
            # Check that sample was limited
            call_args = mock_prompt_client.schema_selection.call_args
            sample_data = call_args.kwargs['sample']
            
            # Should be limited by sample_chars
            assert len(sample_data) <= 250  # Some margin for formatting
            
            # Should not contain all 1000 users
            user_count = sample_data.count('User')
            assert user_count < 20  # Much less than 1000
            
        finally:
            self.cleanup_temp_file(input_file)
    
    # Descriptor Generation Tests
    @patch('trustgraph.cli.load_structured_data.TrustGraphAPI')
    def test_generate_descriptor_csv_format(self, mock_api_class):
        """Test descriptor generation for CSV format"""
        mock_api = Mock()
        mock_api_class.return_value = mock_api
        mock_config_api = Mock()
        mock_api.config.return_value = mock_config_api
        mock_config_api.get_config_items.return_value = {"schema": self.mock_schemas}
        
        mock_flow = Mock()
        mock_api.flow.return_value = mock_flow
        mock_flow.id.return_value = mock_flow
        mock_prompt_client = Mock()
        mock_flow.prompt.return_value = mock_prompt_client
        
        # Mock descriptor generation response
        generated_descriptor = {
            "version": "1.0",
            "metadata": {
                "name": "CustomerDataImport",
                "description": "Import customer data from CSV",
                "author": "TrustGraph"
            },
            "format": {
                "type": "csv",
                "encoding": "utf-8",
                "options": {
                    "header": True,
                    "delimiter": ","
                }
            },
            "mappings": [
                {
                    "source_field": "name",
                    "target_field": "name",
                    "transforms": [{"type": "trim"}],
                    "validation": [{"type": "required"}]
                },
                {
                    "source_field": "email", 
                    "target_field": "email",
                    "transforms": [{"type": "trim"}, {"type": "lower"}],
                    "validation": [{"type": "required"}]
                },
                {
                    "source_field": "age",
                    "target_field": "age", 
                    "transforms": [{"type": "to_int"}],
                    "validation": [{"type": "required"}]
                }
            ],
            "output": {
                "format": "trustgraph-objects",
                "schema_name": "customer",
                "options": {
                    "confidence": 0.85,
                    "batch_size": 100
                }
            }
        }
        
        mock_prompt_client.diagnose_structured_data.return_value = json.dumps(generated_descriptor)
        
        input_file = self.create_temp_file(self.customer_csv, '.csv')
        
        try:
            result = load_structured_data(
                api_url=self.api_url,
                input_file=input_file,
                generate_descriptor=True,
                sample_chars=1000
            )
            
            # Verify API calls
            mock_prompt_client.diagnose_structured_data.assert_called_once()
            
            # Check call arguments
            call_args = mock_prompt_client.diagnose_structured_data.call_args
            assert 'schemas' in call_args.kwargs
            assert 'sample' in call_args.kwargs
            
            # Verify CSV data was included
            sample_data = call_args.kwargs['sample']
            assert 'name,email,age,country' in sample_data  # Header
            assert 'John Smith' in sample_data
            
            # Verify schemas were passed
            passed_schemas = call_args.kwargs['schemas']
            assert len(passed_schemas) > 0
            
        finally:
            self.cleanup_temp_file(input_file)
    
    @patch('trustgraph.cli.load_structured_data.TrustGraphAPI')
    def test_generate_descriptor_json_format(self, mock_api_class):
        """Test descriptor generation for JSON format"""
        mock_api = Mock()
        mock_api_class.return_value = mock_api
        mock_config_api = Mock()
        mock_api.config.return_value = mock_config_api
        mock_config_api.get_config_items.return_value = {"schema": self.mock_schemas}
        
        mock_flow = Mock()
        mock_api.flow.return_value = mock_flow
        mock_flow.id.return_value = mock_flow
        mock_prompt_client = Mock()
        mock_flow.prompt.return_value = mock_prompt_client
        
        generated_descriptor = {
            "version": "1.0",
            "format": {
                "type": "json",
                "encoding": "utf-8"
            },
            "mappings": [
                {
                    "source_field": "id",
                    "target_field": "product_id",
                    "transforms": [{"type": "trim"}],
                    "validation": [{"type": "required"}]
                },
                {
                    "source_field": "name",
                    "target_field": "product_name",
                    "transforms": [{"type": "trim"}],
                    "validation": [{"type": "required"}]
                },
                {
                    "source_field": "price",
                    "target_field": "price",
                    "transforms": [{"type": "to_float"}],
                    "validation": []
                }
            ],
            "output": {
                "format": "trustgraph-objects",
                "schema_name": "product",
                "options": {"confidence": 0.9, "batch_size": 50}
            }
        }
        
        mock_prompt_client.diagnose_structured_data.return_value = json.dumps(generated_descriptor)
        
        input_file = self.create_temp_file(json.dumps(self.product_json), '.json')
        
        try:
            result = load_structured_data(
                api_url=self.api_url,
                input_file=input_file,
                generate_descriptor=True
            )
            
            mock_prompt_client.diagnose_structured_data.assert_called_once()
            
            # Verify JSON structure was analyzed
            call_args = mock_prompt_client.diagnose_structured_data.call_args
            sample_data = call_args.kwargs['sample']
            assert 'PROD001' in sample_data
            assert 'Wireless Headphones' in sample_data
            assert '99.99' in sample_data
            
        finally:
            self.cleanup_temp_file(input_file)
    
    @patch('trustgraph.cli.load_structured_data.TrustGraphAPI')
    def test_generate_descriptor_xml_format(self, mock_api_class):
        """Test descriptor generation for XML format"""
        mock_api = Mock()
        mock_api_class.return_value = mock_api
        mock_config_api = Mock()
        mock_api.config.return_value = mock_config_api
        mock_config_api.get_config_items.return_value = {"schema": self.mock_schemas}
        
        mock_flow = Mock()
        mock_api.flow.return_value = mock_flow
        mock_flow.id.return_value = mock_flow
        mock_prompt_client = Mock()
        mock_flow.prompt.return_value = mock_prompt_client
        
        # XML descriptor should include XPath configuration
        xml_descriptor = {
            "version": "1.0",
            "format": {
                "type": "xml",
                "encoding": "utf-8",
                "options": {
                    "record_path": "/ROOT/data/record",
                    "field_attribute": "name"
                }
            },
            "mappings": [
                {
                    "source_field": "country",
                    "target_field": "country",
                    "transforms": [{"type": "trim"}, {"type": "upper"}],
                    "validation": [{"type": "required"}]
                },
                {
                    "source_field": "value_usd",
                    "target_field": "trade_value",
                    "transforms": [{"type": "to_float"}],
                    "validation": []
                }
            ],
            "output": {
                "format": "trustgraph-objects",
                "schema_name": "trade_data",
                "options": {"confidence": 0.8, "batch_size": 25}
            }
        }
        
        mock_prompt_client.diagnose_structured_data.return_value = json.dumps(xml_descriptor)
        
        input_file = self.create_temp_file(self.trade_xml, '.xml')
        
        try:
            result = load_structured_data(
                api_url=self.api_url,
                input_file=input_file,
                generate_descriptor=True
            )
            
            mock_prompt_client.diagnose_structured_data.assert_called_once()
            
            # Verify XML structure was included
            call_args = mock_prompt_client.diagnose_structured_data.call_args
            sample_data = call_args.kwargs['sample']
            assert '<ROOT>' in sample_data
            assert 'field name=' in sample_data
            assert 'USA' in sample_data
            
        finally:
            self.cleanup_temp_file(input_file)
    
    # Error Handling Tests
    @patch('trustgraph.cli.load_structured_data.TrustGraphAPI')
    def test_suggest_schema_no_schemas_available(self, mock_api_class):
        """Test schema suggestion when no schemas are available"""
        mock_api = Mock()
        mock_api_class.return_value = mock_api
        mock_config_api = Mock()
        mock_api.config.return_value = mock_config_api
        mock_config_api.get_config_items.return_value = {"schema": {}}  # Empty schemas
        
        input_file = self.create_temp_file(self.customer_csv, '.csv')
        
        try:
            with pytest.raises(ValueError) as exc_info:
                result = load_structured_data(
                    api_url=self.api_url,
                    input_file=input_file,
                    suggest_schema=True
                )
            
            assert "no schemas" in str(exc_info.value).lower()
            
        finally:
            self.cleanup_temp_file(input_file)
    
    @patch('trustgraph.cli.load_structured_data.TrustGraphAPI')
    def test_generate_descriptor_api_error(self, mock_api_class):
        """Test descriptor generation when API returns error"""
        mock_api = Mock()
        mock_api_class.return_value = mock_api
        mock_config_api = Mock()
        mock_api.config.return_value = mock_config_api
        mock_config_api.get_config_items.return_value = {"schema": self.mock_schemas}
        
        mock_flow = Mock()
        mock_api.flow.return_value = mock_flow
        mock_flow.id.return_value = mock_flow
        mock_prompt_client = Mock()
        mock_flow.prompt.return_value = mock_prompt_client
        
        # Mock API error
        mock_prompt_client.diagnose_structured_data.side_effect = Exception("API connection failed")
        
        input_file = self.create_temp_file(self.customer_csv, '.csv')
        
        try:
            with pytest.raises(Exception) as exc_info:
                result = load_structured_data(
                    api_url=self.api_url,
                    input_file=input_file,
                    generate_descriptor=True
                )
            
            assert "API connection failed" in str(exc_info.value)
            
        finally:
            self.cleanup_temp_file(input_file)
    
    @patch('trustgraph.cli.load_structured_data.TrustGraphAPI')
    def test_generate_descriptor_invalid_response(self, mock_api_class):
        """Test descriptor generation with invalid API response"""
        mock_api = Mock()
        mock_api_class.return_value = mock_api
        mock_config_api = Mock()
        mock_api.config.return_value = mock_config_api
        mock_config_api.get_config_items.return_value = {"schema": self.mock_schemas}
        
        mock_flow = Mock()
        mock_api.flow.return_value = mock_flow
        mock_flow.id.return_value = mock_flow
        mock_prompt_client = Mock()
        mock_flow.prompt.return_value = mock_prompt_client
        
        # Return invalid JSON
        mock_prompt_client.diagnose_structured_data.return_value = "invalid json response"
        
        input_file = self.create_temp_file(self.customer_csv, '.csv')
        
        try:
            with pytest.raises(json.JSONDecodeError):
                result = load_structured_data(
                    api_url=self.api_url,
                    input_file=input_file,
                    generate_descriptor=True
                )
                
        finally:
            self.cleanup_temp_file(input_file)
    
    # Output Format Tests
    def test_suggest_schema_output_format(self):
        """Test that schema suggestion produces proper output format"""
        # This would be tested with actual TrustGraph instance
        # Here we verify the expected behavior structure
        pass
    
    def test_generate_descriptor_output_to_file(self):
        """Test descriptor generation with file output"""
        # Test would verify descriptor is written to specified file
        pass
    
    # Sample Data Quality Tests
    @patch('trustgraph.cli.load_structured_data.TrustGraphAPI') 
    def test_sample_data_quality_csv(self, mock_api_class):
        """Test that sample data quality is maintained for CSV"""
        mock_api = Mock()
        mock_api_class.return_value = mock_api
        mock_config_api = Mock()
        mock_api.config.return_value = mock_config_api
        mock_config_api.get_config_items.return_value = {"schema": self.mock_schemas}
        
        mock_flow = Mock()
        mock_api.flow.return_value = mock_flow
        mock_flow.id.return_value = mock_flow
        mock_prompt_client = Mock()
        mock_flow.prompt.return_value = mock_prompt_client
        mock_prompt_client.schema_selection.return_value = "customer schema recommended"
        
        # CSV with various data types and edge cases
        complex_csv = """name,email,age,salary,join_date,is_active,notes
John O'Connor,"john@company.com",35,75000.50,2024-01-15,true,"Senior Developer, Team Lead"
Jane "Smith" Doe,jane@email.com,28,65000,2024-02-01,true,"Data Scientist, ML Expert"
Bob,bob@temp.org,42,,2023-12-01,false,"Contractor, Part-time"
,missing@email.com,25,45000,2024-03-01,true,"Junior Developer, New Hire" """
        
        input_file = self.create_temp_file(complex_csv, '.csv')
        
        try:
            result = load_structured_data(
                api_url=self.api_url,
                input_file=input_file,
                suggest_schema=True,
                sample_chars=1000
            )
            
            # Check that sample preserves important characteristics
            call_args = mock_prompt_client.schema_selection.call_args
            sample_data = call_args.kwargs['sample']
            
            # Should preserve header
            assert 'name,email,age,salary' in sample_data
            
            # Should include examples of data variety
            assert "John O'Connor" in sample_data or 'John' in sample_data
            assert '@' in sample_data  # Email format
            assert '75000' in sample_data or '65000' in sample_data  # Numeric data
            
        finally:
            self.cleanup_temp_file(input_file)