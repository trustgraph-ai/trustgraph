"""
Algorithmic data type detection for structured data.
Determines if data is CSV, JSON, or XML based on content analysis.
"""

import json
import xml.etree.ElementTree as ET
import csv
from io import StringIO
import logging
from typing import Dict, Optional, Tuple

# Module logger
logger = logging.getLogger(__name__)


def detect_data_type(sample: str) -> Tuple[Optional[str], float]:
    """
    Detect the data type (csv, json, xml) of a data sample.

    Args:
        sample: String containing data sample to analyze

    Returns:
        Tuple of (detected_type, confidence_score)
        detected_type: "csv", "json", "xml", or None if unable to determine
        confidence_score: Float between 0.0 and 1.0 indicating confidence
    """
    if not sample or not sample.strip():
        return None, 0.0

    sample = sample.strip()

    # Try each format and calculate confidence scores
    json_confidence = _check_json_format(sample)
    xml_confidence = _check_xml_format(sample)
    csv_confidence = _check_csv_format(sample)

    logger.debug(f"Format confidence scores - JSON: {json_confidence}, XML: {xml_confidence}, CSV: {csv_confidence}")

    # Find the format with highest confidence
    scores = {
        "json": json_confidence,
        "xml": xml_confidence,
        "csv": csv_confidence
    }

    best_format = max(scores, key=scores.get)
    best_confidence = scores[best_format]

    # Only return a result if confidence is above threshold
    if best_confidence < 0.3:
        return None, best_confidence

    return best_format, best_confidence


def _check_json_format(sample: str) -> float:
    """Check if sample is valid JSON format"""
    try:
        # Must start with { or [
        if not (sample.startswith('{') or sample.startswith('[')):
            return 0.0

        # Try to parse as JSON
        data = json.loads(sample)

        # Higher confidence for structured data
        if isinstance(data, dict):
            return 0.95
        elif isinstance(data, list) and len(data) > 0:
            # Check if it's an array of objects (common for structured data)
            if isinstance(data[0], dict):
                return 0.9
            else:
                return 0.7
        else:
            return 0.6

    except (json.JSONDecodeError, ValueError):
        return 0.0


def _check_xml_format(sample: str) -> float:
    """Check if sample is valid XML format"""
    try:
        # Quick heuristic checks first
        if not sample.startswith('<'):
            return 0.0

        if not ('>' in sample and '</' in sample):
            return 0.1  # Might be incomplete XML

        # Try to parse as XML
        root = ET.fromstring(sample)

        # Higher confidence for XML with multiple child elements
        child_count = len(list(root))
        if child_count > 10:
            return 0.95
        elif child_count > 5:
            return 0.9
        elif child_count > 0:
            return 0.8
        else:
            return 0.6

    except ET.ParseError:
        # Check for common XML characteristics even if not well-formed
        xml_indicators = ['</', '<?xml', 'xmlns:', '<![CDATA[']
        score = sum(0.1 for indicator in xml_indicators if indicator in sample)
        return min(score, 0.3)  # Max 0.3 for malformed XML


def _check_csv_format(sample: str) -> float:
    """Check if sample is valid CSV format"""
    try:
        lines = sample.strip().split('\n')
        if len(lines) < 2:
            return 0.0

        # Try to parse as CSV with different delimiters
        delimiters = [',', ';', '\t', '|']
        best_score = 0.0

        for delimiter in delimiters:
            score = _check_csv_with_delimiter(sample, delimiter)
            best_score = max(best_score, score)

        return best_score

    except Exception:
        return 0.0


def _check_csv_with_delimiter(sample: str, delimiter: str) -> float:
    """Check CSV format with specific delimiter"""
    try:
        reader = csv.reader(StringIO(sample), delimiter=delimiter)
        rows = list(reader)

        if len(rows) < 2:
            return 0.0

        # Check consistency of column counts
        first_row_cols = len(rows[0])
        if first_row_cols < 2:
            return 0.0

        consistent_rows = 0
        for row in rows[1:]:
            if len(row) == first_row_cols:
                consistent_rows += 1

        consistency_ratio = consistent_rows / (len(rows) - 1) if len(rows) > 1 else 0

        # Base score on consistency and structure
        if consistency_ratio > 0.8:
            # Higher score for more columns and rows
            column_bonus = min(first_row_cols * 0.05, 0.2)
            row_bonus = min(len(rows) * 0.01, 0.1)
            return min(0.7 + column_bonus + row_bonus, 0.95)
        elif consistency_ratio > 0.6:
            return 0.5
        else:
            return 0.2

    except Exception:
        return 0.0


def detect_csv_options(sample: str) -> Dict[str, any]:
    """
    Detect CSV-specific options like delimiter and header presence.

    Args:
        sample: CSV data sample

    Returns:
        Dict with detected options: delimiter, has_header, etc.
    """
    options = {
        "delimiter": ",",
        "has_header": True,
        "encoding": "utf-8"
    }

    try:
        lines = sample.strip().split('\n')
        if len(lines) < 2:
            return options

        # Detect delimiter
        delimiters = [',', ';', '\t', '|']
        best_delimiter = ","
        best_score = 0

        for delimiter in delimiters:
            score = _check_csv_with_delimiter(sample, delimiter)
            if score > best_score:
                best_score = score
                best_delimiter = delimiter

        options["delimiter"] = best_delimiter

        # Detect header (heuristic: first row has text, second row has more numbers/structured data)
        reader = csv.reader(StringIO(sample), delimiter=best_delimiter)
        rows = list(reader)

        if len(rows) >= 2:
            first_row = rows[0]
            second_row = rows[1]

            # Count numeric fields in each row
            first_numeric = sum(1 for cell in first_row if _is_numeric(cell))
            second_numeric = sum(1 for cell in second_row if _is_numeric(cell))

            # If second row has more numeric values, first row is likely header
            if second_numeric > first_numeric and first_numeric < len(first_row) * 0.7:
                options["has_header"] = True
            else:
                options["has_header"] = False

    except Exception as e:
        logger.debug(f"Error detecting CSV options: {e}")

    return options


def _is_numeric(value: str) -> bool:
    """Check if a string value represents a number"""
    try:
        float(value.strip())
        return True
    except (ValueError, AttributeError):
        return False