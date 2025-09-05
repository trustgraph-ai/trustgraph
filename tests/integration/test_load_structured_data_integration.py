"""
Integration tests for tg-load-structured-data with actual TrustGraph instance.
Tests end-to-end functionality including WebSocket connections and data storage.
"""

import pytest
import asyncio
import json
import tempfile
import os
import csv
import time
from unittest.mock import Mock, patch, AsyncMock
from websockets.asyncio.client import connect

from trustgraph.cli.load_structured_data import load_structured_data


@pytest.mark.integration
class TestLoadStructuredDataIntegration:
    """Integration tests for complete pipeline"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.api_url = "http://localhost:8088"
        self.test_schema_name = "integration_test_schema"
        
        self.test_csv_data = """name,email,age,country,status
John Smith,john@email.com,35,US,active
Jane Doe,jane@email.com,28,CA,active
Bob Johnson,bob@company.org,42,UK,inactive
Alice Brown,alice@email.com,31,AU,active
Charlie Davis,charlie@email.com,39,DE,inactive"""
        
        self.test_json_data = [
            {"name": "John Smith", "email": "john@email.com", "age": 35, "country": "US", "status": "active"},
            {"name": "Jane Doe", "email": "jane@email.com", "age": 28, "country": "CA", "status": "active"},
            {"name": "Bob Johnson", "email": "bob@company.org", "age": 42, "country": "UK", "status": "inactive"}
        ]
        
        self.test_xml_data = """<?xml version="1.0"?>
<ROOT>
    <data>
        <record>
            <field name="name">John Smith</field>
            <field name="email">john@email.com</field>
            <field name="age">35</field>
            <field name="country">US</field>
            <field name="status">active</field>
        </record>
        <record>
            <field name="name">Jane Doe</field>
            <field name="email">jane@email.com</field>
            <field name="age">28</field>
            <field name="country">CA</field>
            <field name="status">active</field>
        </record>
        <record>
            <field name="name">Bob Johnson</field>
            <field name="email">bob@company.org</field>
            <field name="age">42</field>
            <field name="country">UK</field>
            <field name="status">inactive</field>
        </record>
    </data>
</ROOT>"""
        
        self.test_descriptor = {
            "version": "1.0",
            "metadata": {
                "name": "IntegrationTest",
                "description": "Test descriptor for integration tests",
                "author": "Test Suite"
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
                },
                {
                    "source_field": "country",
                    "target_field": "country",
                    "transforms": [{"type": "trim"}, {"type": "upper"}],
                    "validation": [{"type": "required"}]
                },
                {
                    "source_field": "status",
                    "target_field": "status",
                    "transforms": [{"type": "trim"}, {"type": "lower"}],
                    "validation": [{"type": "required"}]
                }
            ],
            "output": {
                "format": "trustgraph-objects",
                "schema_name": self.test_schema_name,
                "options": {
                    "confidence": 0.9,
                    "batch_size": 3
                }
            }
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
    
    # End-to-end Pipeline Tests
    @pytest.mark.asyncio
    async def test_csv_to_trustgraph_pipeline(self):
        """Test complete CSV to TrustGraph pipeline"""
        input_file = self.create_temp_file(self.test_csv_data, '.csv')
        descriptor_file = self.create_temp_file(json.dumps(self.test_descriptor), '.json')
        
        try:
            # Test with dry run first
            result = load_structured_data(
                api_url=self.api_url,
                input_file=input_file,
                descriptor_file=descriptor_file,
                dry_run=True,
                batch_size=2,
                flow='obj-ex'
            )
            
            # Should complete without errors in dry run mode
            assert result is None  # dry_run returns None
            
        finally:
            self.cleanup_temp_file(input_file)
            self.cleanup_temp_file(descriptor_file)
    
    @pytest.mark.asyncio 
    async def test_xml_to_trustgraph_pipeline(self):
        """Test complete XML to TrustGraph pipeline"""
        # Create XML descriptor
        xml_descriptor = {
            **self.test_descriptor,
            "format": {
                "type": "xml",
                "encoding": "utf-8",
                "options": {
                    "record_path": "/ROOT/data/record",
                    "field_attribute": "name"
                }
            }
        }
        
        input_file = self.create_temp_file(self.test_xml_data, '.xml')
        descriptor_file = self.create_temp_file(json.dumps(xml_descriptor), '.json')
        
        try:
            # Test with dry run
            result = load_structured_data(
                api_url=self.api_url,
                input_file=input_file,
                descriptor_file=descriptor_file,
                dry_run=True,
                batch_size=2,
                flow='obj-ex'
            )
            
            assert result is None  # dry_run returns None
            
        finally:
            self.cleanup_temp_file(input_file)
            self.cleanup_temp_file(descriptor_file)
    
    @pytest.mark.asyncio
    async def test_json_to_trustgraph_pipeline(self):
        """Test complete JSON to TrustGraph pipeline"""
        json_descriptor = {
            **self.test_descriptor,
            "format": {
                "type": "json",
                "encoding": "utf-8"
            }
        }
        
        input_file = self.create_temp_file(json.dumps(self.test_json_data), '.json')
        descriptor_file = self.create_temp_file(json.dumps(json_descriptor), '.json')
        
        try:
            result = load_structured_data(
                api_url=self.api_url,
                input_file=input_file,
                descriptor_file=descriptor_file,
                dry_run=True,
                batch_size=2,
                flow='obj-ex'
            )
            
            assert result is None  # dry_run returns None
            
        finally:
            self.cleanup_temp_file(input_file)
            self.cleanup_temp_file(descriptor_file)
    
    # Batching Integration Tests
    @pytest.mark.asyncio
    async def test_large_dataset_batching(self):
        """Test batching with larger dataset"""
        # Generate larger dataset
        large_csv_data = "name,email,age,country,status\n"
        for i in range(1000):
            large_csv_data += f"User{i},user{i}@example.com,{25+i%40},US,active\n"
        
        input_file = self.create_temp_file(large_csv_data, '.csv')
        descriptor_file = self.create_temp_file(json.dumps(self.test_descriptor), '.json')
        
        try:
            start_time = time.time()
            
            result = load_structured_data(
                api_url=self.api_url,
                input_file=input_file,
                descriptor_file=descriptor_file,
                dry_run=True,
                batch_size=50,  # Test with moderate batch size
                flow='obj-ex'
            )
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Should process 1000 records reasonably quickly
            assert processing_time < 30  # Should complete in under 30 seconds
            assert result is None  # dry_run returns None
            
        finally:
            self.cleanup_temp_file(input_file)
            self.cleanup_temp_file(descriptor_file)
    
    @pytest.mark.asyncio
    async def test_batch_size_performance(self):
        """Test different batch sizes for performance"""
        # Generate test dataset
        test_csv_data = "name,email,age,country,status\n"
        for i in range(100):
            test_csv_data += f"User{i},user{i}@example.com,{25+i%40},US,active\n"
        
        input_file = self.create_temp_file(test_csv_data, '.csv')
        descriptor_file = self.create_temp_file(json.dumps(self.test_descriptor), '.json')
        
        try:
            # Test different batch sizes
            batch_sizes = [1, 10, 25, 50, 100]
            processing_times = {}
            
            for batch_size in batch_sizes:
                start_time = time.time()
                
                result = load_structured_data(
                    api_url=self.api_url,
                    input_file=input_file,
                    descriptor_file=descriptor_file,
                    dry_run=True,
                    batch_size=batch_size,
                    flow='obj-ex'
                )
                
                end_time = time.time()
                processing_times[batch_size] = end_time - start_time
                
                assert result is None  # dry_run returns None
            
            # All batch sizes should complete reasonably quickly
            for batch_size, time_taken in processing_times.items():
                assert time_taken < 10, f"Batch size {batch_size} took {time_taken}s"
            
        finally:
            self.cleanup_temp_file(input_file)
            self.cleanup_temp_file(descriptor_file)
    
    # Parse-Only Mode Tests
    @pytest.mark.asyncio
    async def test_parse_only_mode(self):
        """Test parse-only mode functionality"""
        input_file = self.create_temp_file(self.test_csv_data, '.csv')
        descriptor_file = self.create_temp_file(json.dumps(self.test_descriptor), '.json')
        output_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        output_file.close()
        
        try:
            result = load_structured_data(
                api_url=self.api_url,
                input_file=input_file,
                descriptor_file=descriptor_file,
                parse_only=True,
                output_file=output_file.name
            )
            
            # Check output file was created and contains parsed data
            assert os.path.exists(output_file.name)
            with open(output_file.name, 'r') as f:
                parsed_data = json.load(f)
                assert isinstance(parsed_data, list)
                assert len(parsed_data) == 5  # Should have 5 records
                assert parsed_data[0]["name"] == "John Smith"
            
        finally:
            self.cleanup_temp_file(input_file)
            self.cleanup_temp_file(descriptor_file)
            self.cleanup_temp_file(output_file.name)
    
    # Schema Suggestion Integration Tests
    @patch('trustgraph.cli.load_structured_data.TrustGraphAPI')
    @pytest.mark.asyncio
    async def test_schema_suggestion_integration(self, mock_api_class):
        """Test schema suggestion integration with API"""
        # Setup mock API responses
        mock_api = Mock()
        mock_api_class.return_value = mock_api
        mock_config_api = Mock()
        mock_api.config.return_value = mock_config_api
        mock_config_api.get_config_items.return_value = {
            "schema": {
                "customer": '{"name": "customer", "description": "Customer records"}',
                "product": '{"name": "product", "description": "Product catalog"}'
            }
        }
        
        mock_flow = Mock()
        mock_api.flow.return_value = mock_flow
        mock_flow.id.return_value = mock_flow
        mock_prompt_client = Mock()
        mock_flow.prompt.return_value = mock_prompt_client
        mock_prompt_client.schema_selection.return_value = "The customer schema is most appropriate for this data containing names and emails."
        
        input_file = self.create_temp_file(self.test_csv_data, '.csv')
        
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
            
            # Check that schemas were passed correctly
            call_args = mock_prompt_client.schema_selection.call_args
            assert 'schemas' in call_args.kwargs
            assert 'sample' in call_args.kwargs
            
        finally:
            self.cleanup_temp_file(input_file)
    
    # Descriptor Generation Integration Tests
    @patch('trustgraph.cli.load_structured_data.TrustGraphAPI')
    @pytest.mark.asyncio
    async def test_descriptor_generation_integration(self, mock_api_class):
        """Test descriptor generation integration"""
        # Setup mock API
        mock_api = Mock()
        mock_api_class.return_value = mock_api
        mock_config_api = Mock()
        mock_api.config.return_value = mock_config_api
        mock_config_api.get_config_items.return_value = {
            "schema": {
                "customer": '{"name": "customer", "fields": [{"name": "name", "type": "string"}]}'
            }
        }
        
        mock_flow = Mock()
        mock_api.flow.return_value = mock_flow
        mock_flow.id.return_value = mock_flow
        mock_prompt_client = Mock()
        mock_flow.prompt.return_value = mock_prompt_client
        
        # Mock descriptor generation response
        generated_descriptor = {**self.test_descriptor}
        mock_prompt_client.diagnose_structured_data.return_value = json.dumps(generated_descriptor)
        
        input_file = self.create_temp_file(self.test_csv_data, '.csv')
        
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
            
        finally:
            self.cleanup_temp_file(input_file)
    
    # Error Handling Integration Tests
    @pytest.mark.asyncio
    async def test_malformed_data_handling(self):
        """Test handling of malformed data"""
        malformed_csv = """name,email,age
John Smith,john@email.com,35
Jane Doe,jane@email.com  # Missing age field
Bob Johnson,bob@company.org,not_a_number"""
        
        input_file = self.create_temp_file(malformed_csv, '.csv')
        descriptor_file = self.create_temp_file(json.dumps(self.test_descriptor), '.json')
        
        try:
            # Should handle malformed data gracefully
            result = load_structured_data(
                api_url=self.api_url,
                input_file=input_file,
                descriptor_file=descriptor_file,
                dry_run=True,
                max_errors=5  # Allow some errors
            )
            
            # Should complete even with some malformed records
            assert result is None  # dry_run returns None
            
        finally:
            self.cleanup_temp_file(input_file)
            self.cleanup_temp_file(descriptor_file)
    
    # WebSocket Connection Tests
    @pytest.mark.asyncio
    async def test_websocket_connection_handling(self):
        """Test WebSocket connection behavior"""
        input_file = self.create_temp_file(self.test_csv_data, '.csv')
        descriptor_file = self.create_temp_file(json.dumps(self.test_descriptor), '.json')
        
        try:
            # Test with invalid API URL (should fail gracefully)
            with pytest.raises(Exception):  # Connection error expected
                result = load_structured_data(
                    api_url="http://invalid-url:9999",
                    input_file=input_file,
                    descriptor_file=descriptor_file,
                    batch_size=2,
                    flow='obj-ex'
                )
                
        finally:
            self.cleanup_temp_file(input_file)
            self.cleanup_temp_file(descriptor_file)
    
    # Flow Parameter Tests
    @pytest.mark.asyncio
    async def test_flow_parameter_integration(self):
        """Test flow parameter functionality"""
        input_file = self.create_temp_file(self.test_csv_data, '.csv')
        descriptor_file = self.create_temp_file(json.dumps(self.test_descriptor), '.json')
        
        try:
            # Test with different flow values
            flows = ['default', 'obj-ex', 'custom-flow']
            
            for flow in flows:
                result = load_structured_data(
                    api_url=self.api_url,
                    input_file=input_file,
                    descriptor_file=descriptor_file,
                    dry_run=True,
                    flow=flow
                )
                
                assert result is None  # dry_run returns None
                
        finally:
            self.cleanup_temp_file(input_file)
            self.cleanup_temp_file(descriptor_file)
    
    # Mixed Format Tests
    @pytest.mark.asyncio
    async def test_encoding_variations(self):
        """Test different encoding variations"""
        # Test UTF-8 with BOM
        utf8_bom_data = '\ufeff' + self.test_csv_data
        
        input_file = self.create_temp_file(utf8_bom_data, '.csv')
        descriptor_file = self.create_temp_file(json.dumps(self.test_descriptor), '.json')
        
        try:
            result = load_structured_data(
                api_url=self.api_url,
                input_file=input_file,
                descriptor_file=descriptor_file,
                dry_run=True
            )
            
            assert result is None  # Should handle BOM correctly
            
        finally:
            self.cleanup_temp_file(input_file)
            self.cleanup_temp_file(descriptor_file)