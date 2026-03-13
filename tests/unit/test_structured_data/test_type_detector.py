"""
Tests for structured data type detection: CSV, JSON, XML format detection,
CSV option detection (delimiter, header), and helper functions.
"""

import pytest

from trustgraph.retrieval.structured_diag.type_detector import (
    detect_data_type,
    _check_json_format,
    _check_xml_format,
    _check_csv_format,
    _check_csv_with_delimiter,
    detect_csv_options,
    _is_numeric,
)


# ---------------------------------------------------------------------------
# detect_data_type (top-level dispatcher)
# ---------------------------------------------------------------------------

class TestDetectDataType:

    def test_empty_string_returns_none(self):
        detected, confidence = detect_data_type("")
        assert detected is None
        assert confidence == 0.0

    def test_whitespace_only_returns_none(self):
        detected, confidence = detect_data_type("   \n  \t  ")
        assert detected is None
        assert confidence == 0.0

    def test_none_returns_none(self):
        detected, confidence = detect_data_type(None)
        assert detected is None
        assert confidence == 0.0

    def test_json_object_detected(self):
        detected, confidence = detect_data_type('{"name": "Alice"}')
        assert detected == "json"
        assert confidence > 0.5

    def test_json_array_detected(self):
        detected, confidence = detect_data_type('[{"id": 1}, {"id": 2}]')
        assert detected == "json"
        assert confidence > 0.5

    def test_xml_with_declaration_detected(self):
        detected, confidence = detect_data_type('<?xml version="1.0"?><root></root>')
        assert detected == "xml"
        assert confidence > 0.5

    def test_xml_without_declaration_detected(self):
        detected, confidence = detect_data_type('<root><item>val</item></root>')
        assert detected == "xml"
        assert confidence > 0.5

    def test_csv_detected(self):
        data = "name,age,city\nAlice,30,NYC\nBob,25,LA"
        detected, confidence = detect_data_type(data)
        assert detected == "csv"
        assert confidence > 0.5

    def test_plain_text_falls_through_to_csv(self):
        """Non-JSON/XML text defaults to CSV detection."""
        detected, confidence = detect_data_type("just some text")
        assert detected == "csv"


# ---------------------------------------------------------------------------
# _check_json_format
# ---------------------------------------------------------------------------

class TestCheckJsonFormat:

    def test_valid_json_object(self):
        assert _check_json_format('{"key": "value"}') > 0.9

    def test_valid_json_array_of_objects(self):
        assert _check_json_format('[{"id": 1}, {"id": 2}]') >= 0.9

    def test_valid_json_array_of_primitives(self):
        score = _check_json_format('[1, 2, 3]')
        assert score > 0.5
        assert score < 0.9  # Lower confidence for non-object arrays

    def test_empty_json_object(self):
        assert _check_json_format('{}') > 0.5

    def test_invalid_json(self):
        assert _check_json_format('{invalid json}') == 0.0

    def test_non_json_starting_char(self):
        assert _check_json_format('hello world') == 0.0

    def test_empty_array(self):
        score = _check_json_format('[]')
        assert score > 0.0  # Parsed successfully but empty


# ---------------------------------------------------------------------------
# _check_xml_format
# ---------------------------------------------------------------------------

class TestCheckXmlFormat:

    def test_valid_xml(self):
        assert _check_xml_format('<root><item>val</item></root>') == 0.9

    def test_xml_with_declaration(self):
        xml = '<?xml version="1.0"?><root><item>test</item></root>'
        assert _check_xml_format(xml) == 0.9

    def test_malformed_xml(self):
        score = _check_xml_format('<root><unclosed>')
        # Has < and </ check fails since no closing tag
        assert score < 0.9

    def test_not_xml(self):
        assert _check_xml_format('just text') == 0.0

    def test_incomplete_xml_tag(self):
        score = _check_xml_format('<root>')
        # Starts with < but no closing tag
        assert score <= 0.1


# ---------------------------------------------------------------------------
# _check_csv_format and _check_csv_with_delimiter
# ---------------------------------------------------------------------------

class TestCheckCsvFormat:

    def test_valid_csv_comma(self):
        data = "name,age,city\nAlice,30,NYC\nBob,25,LA"
        assert _check_csv_format(data) > 0.7

    def test_valid_csv_semicolon(self):
        data = "name;age;city\nAlice;30;NYC\nBob;25;LA"
        assert _check_csv_format(data) > 0.7

    def test_valid_csv_tab(self):
        data = "name\tage\tcity\nAlice\t30\tNYC\nBob\t25\tLA"
        assert _check_csv_format(data) > 0.7

    def test_valid_csv_pipe(self):
        data = "name|age|city\nAlice|30|NYC\nBob|25|LA"
        assert _check_csv_format(data) > 0.7

    def test_single_line_not_csv(self):
        assert _check_csv_format("just one line") == 0.0

    def test_single_column_not_csv(self):
        data = "a\nb\nc"
        assert _check_csv_with_delimiter(data, ",") == 0.0

    def test_inconsistent_columns_low_score(self):
        data = "a,b,c\n1,2\n3,4,5,6"
        score = _check_csv_with_delimiter(data, ",")
        assert score < 0.7

    def test_many_rows_higher_score(self):
        rows = ["name,age,city"] + [f"person{i},{20+i},city{i}" for i in range(20)]
        data = "\n".join(rows)
        score = _check_csv_format(data)
        assert score > 0.8


# ---------------------------------------------------------------------------
# detect_csv_options
# ---------------------------------------------------------------------------

class TestDetectCsvOptions:

    def test_comma_delimiter_detected(self):
        data = "name,age,city\nAlice,30,NYC\nBob,25,LA"
        options = detect_csv_options(data)
        assert options["delimiter"] == ","

    def test_semicolon_delimiter_detected(self):
        data = "name;age;city\nAlice;30;NYC\nBob;25;LA"
        options = detect_csv_options(data)
        assert options["delimiter"] == ";"

    def test_tab_delimiter_detected(self):
        data = "name\tage\tcity\nAlice\t30\tNYC\nBob\t25\tLA"
        options = detect_csv_options(data)
        assert options["delimiter"] == "\t"

    def test_header_detected_when_first_row_text(self):
        data = "name,age,salary\nAlice,30,50000\nBob,25,45000"
        options = detect_csv_options(data)
        assert options["has_header"] is True

    def test_no_header_when_all_numeric(self):
        data = "1,2,3\n4,5,6\n7,8,9"
        options = detect_csv_options(data)
        assert options["has_header"] is False

    def test_single_line_returns_defaults(self):
        options = detect_csv_options("just one line")
        assert options["delimiter"] == ","
        assert options["has_header"] is True

    def test_encoding_default(self):
        data = "a,b\n1,2"
        options = detect_csv_options(data)
        assert options["encoding"] == "utf-8"


# ---------------------------------------------------------------------------
# _is_numeric helper
# ---------------------------------------------------------------------------

class TestIsNumeric:

    def test_integer(self):
        assert _is_numeric("42") is True

    def test_float(self):
        assert _is_numeric("3.14") is True

    def test_negative(self):
        assert _is_numeric("-10") is True

    def test_text(self):
        assert _is_numeric("hello") is False

    def test_empty(self):
        assert _is_numeric("") is False

    def test_whitespace_padded(self):
        assert _is_numeric("  42  ") is True
