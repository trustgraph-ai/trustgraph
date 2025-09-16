"""
Unit tests for simplified type detection in structured-diag service
"""

import pytest
from trustgraph.retrieval.structured_diag.type_detector import detect_data_type


class TestSimplifiedTypeDetection:
    """Test the simplified type detection logic"""

    def test_xml_detection_with_declaration(self):
        """Test XML detection with XML declaration"""
        sample = '<?xml version="1.0"?><root><item>data</item></root>'
        data_type, confidence = detect_data_type(sample)
        assert data_type == "xml"
        assert confidence == 0.9

    def test_xml_detection_without_declaration(self):
        """Test XML detection without declaration but with closing tags"""
        sample = '<root><item>data</item></root>'
        data_type, confidence = detect_data_type(sample)
        assert data_type == "xml"
        assert confidence == 0.9

    def test_xml_detection_truncated(self):
        """Test XML detection with truncated XML (common with 500-byte samples)"""
        sample = '''<?xml version="1.0" encoding="UTF-8"?>
<pieDataset>
  <pies>
    <pie id="1">
      <pieType>Steak &amp; Kidney</pieType>
      <region>Yorkshire</region>
      <diameterCm>12.5</diameterCm>
      <heightCm>4.2'''  # Truncated mid-element
        data_type, confidence = detect_data_type(sample)
        assert data_type == "xml"
        assert confidence == 0.9

    def test_json_object_detection(self):
        """Test JSON object detection"""
        sample = '{"name": "John", "age": 30, "city": "New York"}'
        data_type, confidence = detect_data_type(sample)
        assert data_type == "json"
        assert confidence == 0.9

    def test_json_array_detection(self):
        """Test JSON array detection"""
        sample = '[{"id": 1}, {"id": 2}, {"id": 3}]'
        data_type, confidence = detect_data_type(sample)
        assert data_type == "json"
        assert confidence == 0.9

    def test_json_truncated(self):
        """Test JSON detection with truncated JSON"""
        sample = '{"products": [{"id": 1, "name": "Widget", "price": 19.99}, {"id": 2, "na'
        data_type, confidence = detect_data_type(sample)
        assert data_type == "json"
        assert confidence == 0.9

    def test_csv_detection(self):
        """Test CSV detection as fallback"""
        sample = '''name,age,city
John,30,New York
Jane,25,Boston
Bob,35,Chicago'''
        data_type, confidence = detect_data_type(sample)
        assert data_type == "csv"
        assert confidence == 0.8

    def test_csv_detection_single_line(self):
        """Test CSV detection with single line defaults to CSV"""
        sample = 'column1,column2,column3'
        data_type, confidence = detect_data_type(sample)
        assert data_type == "csv"
        assert confidence == 0.8

    def test_empty_input(self):
        """Test empty input handling"""
        data_type, confidence = detect_data_type("")
        assert data_type is None
        assert confidence == 0.0

    def test_whitespace_only(self):
        """Test whitespace-only input"""
        data_type, confidence = detect_data_type("   \n  \t  ")
        assert data_type is None
        assert confidence == 0.0

    def test_html_not_xml(self):
        """Test HTML is detected as XML (has closing tags)"""
        sample = '<html><body><h1>Title</h1></body></html>'
        data_type, confidence = detect_data_type(sample)
        assert data_type == "xml"  # HTML is detected as XML
        assert confidence == 0.9

    def test_malformed_xml_still_detected(self):
        """Test malformed XML is still detected as XML"""
        sample = '<root><item>data</item><unclosed>'
        data_type, confidence = detect_data_type(sample)
        assert data_type == "xml"
        assert confidence == 0.9

    def test_json_with_whitespace(self):
        """Test JSON detection with leading whitespace"""
        sample = '   \n  {"key": "value"}'
        data_type, confidence = detect_data_type(sample)
        assert data_type == "json"
        assert confidence == 0.9

    def test_priority_xml_over_csv(self):
        """Test XML takes priority over CSV when both patterns present"""
        sample = '<?xml version="1.0"?>\n<data>a,b,c</data>'
        data_type, confidence = detect_data_type(sample)
        assert data_type == "xml"
        assert confidence == 0.9

    def test_priority_json_over_csv(self):
        """Test JSON takes priority over CSV when both patterns present"""
        sample = '{"data": "a,b,c"}'
        data_type, confidence = detect_data_type(sample)
        assert data_type == "json"
        assert confidence == 0.9

    def test_text_defaults_to_csv(self):
        """Test plain text defaults to CSV"""
        sample = 'This is just plain text without any structure'
        data_type, confidence = detect_data_type(sample)
        assert data_type == "csv"
        assert confidence == 0.8


class TestRealWorldSamples:
    """Test with real-world data samples"""

    def test_uk_pies_xml_sample(self):
        """Test with actual UK pies XML sample (first 500 bytes)"""
        sample = '''<?xml version="1.0" encoding="UTF-8"?>
<pieDataset>
  <pies>
    <pie id="1">
      <pieType>Steak &amp; Kidney</pieType>
      <region>Yorkshire</region>
      <diameterCm>12.5</diameterCm>
      <heightCm>4.2</heightCm>
      <weightGrams>285</weightGrams>
      <crustType>Shortcrust</crustType>
      <fillingCategory>Meat</fillingCategory>
      <price>3.50</price>
      <currency>GBP</currency>
      <bakeryType>Traditional</bakeryType>
    </pie>
    <pie id="2">
      <pieType>Chicken &amp; Mushroom</pieType>
      <region>Lancashire</regio'''  # Cut at 500 chars
        data_type, confidence = detect_data_type(sample[:500])
        assert data_type == "xml"
        assert confidence == 0.9

    def test_product_json_sample(self):
        """Test with product catalog JSON sample"""
        sample = '''{"products": [
  {"id": "PROD001", "name": "Widget", "price": 19.99, "category": "Tools"},
  {"id": "PROD002", "name": "Gadget", "price": 29.99, "category": "Electronics"},
  {"id": "PROD003", "name": "Doohickey", "price": 9.99, "category": "Accessories"}
]}'''
        data_type, confidence = detect_data_type(sample)
        assert data_type == "json"
        assert confidence == 0.9

    def test_customer_csv_sample(self):
        """Test with customer CSV sample"""
        sample = '''customer_id,name,email,signup_date,total_orders
CUST001,John Smith,john@example.com,2023-01-15,5
CUST002,Jane Doe,jane@example.com,2023-02-20,3
CUST003,Bob Johnson,bob@example.com,2023-03-10,7'''
        data_type, confidence = detect_data_type(sample)
        assert data_type == "csv"
        assert confidence == 0.8