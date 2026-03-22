"""
Unit tests for universal decoder section grouping strategies.
"""

import pytest
from unittest.mock import MagicMock


from trustgraph.decoding.universal.strategies import (
    group_whole_document,
    group_by_heading,
    group_by_element_type,
    group_by_count,
    group_by_size,
    get_strategy,
    STRATEGIES,
)


def make_element(category="NarrativeText", text="Some text"):
    """Create a mock unstructured element."""
    el = MagicMock()
    el.category = category
    el.text = text
    return el


class TestGroupWholeDocument:

    def test_empty_input(self):
        assert group_whole_document([]) == []

    def test_returns_single_group(self):
        elements = [make_element() for _ in range(5)]
        result = group_whole_document(elements)
        assert len(result) == 1
        assert len(result[0]) == 5

    def test_preserves_all_elements(self):
        elements = [make_element(text=f"text-{i}") for i in range(3)]
        result = group_whole_document(elements)
        assert result[0] == elements


class TestGroupByHeading:

    def test_empty_input(self):
        assert group_by_heading([]) == []

    def test_no_headings_falls_back(self):
        elements = [make_element("NarrativeText") for _ in range(3)]
        result = group_by_heading(elements)
        assert len(result) == 1
        assert len(result[0]) == 3

    def test_splits_at_headings(self):
        elements = [
            make_element("Title", "Heading 1"),
            make_element("NarrativeText", "Paragraph 1"),
            make_element("NarrativeText", "Paragraph 2"),
            make_element("Title", "Heading 2"),
            make_element("NarrativeText", "Paragraph 3"),
        ]
        result = group_by_heading(elements)
        assert len(result) == 2
        assert len(result[0]) == 3  # Heading 1 + 2 paragraphs
        assert len(result[1]) == 2  # Heading 2 + 1 paragraph

    def test_leading_content_before_first_heading(self):
        elements = [
            make_element("NarrativeText", "Preamble"),
            make_element("Title", "Heading 1"),
            make_element("NarrativeText", "Content"),
        ]
        result = group_by_heading(elements)
        assert len(result) == 2
        assert len(result[0]) == 1  # Preamble
        assert len(result[1]) == 2  # Heading + content

    def test_consecutive_headings(self):
        elements = [
            make_element("Title", "H1"),
            make_element("Title", "H2"),
            make_element("NarrativeText", "Content"),
        ]
        result = group_by_heading(elements)
        assert len(result) == 2


class TestGroupByElementType:

    def test_empty_input(self):
        assert group_by_element_type([]) == []

    def test_all_same_type(self):
        elements = [make_element("NarrativeText") for _ in range(3)]
        result = group_by_element_type(elements)
        assert len(result) == 1

    def test_splits_at_table_boundary(self):
        elements = [
            make_element("NarrativeText", "Intro"),
            make_element("NarrativeText", "More text"),
            make_element("Table", "Table data"),
            make_element("NarrativeText", "After table"),
        ]
        result = group_by_element_type(elements)
        assert len(result) == 3
        assert len(result[0]) == 2  # Two narrative elements
        assert len(result[1]) == 1  # One table
        assert len(result[2]) == 1  # One narrative

    def test_consecutive_tables_stay_grouped(self):
        elements = [
            make_element("Table", "Table 1"),
            make_element("Table", "Table 2"),
        ]
        result = group_by_element_type(elements)
        assert len(result) == 1
        assert len(result[0]) == 2


class TestGroupByCount:

    def test_empty_input(self):
        assert group_by_count([]) == []

    def test_exact_multiple(self):
        elements = [make_element() for _ in range(6)]
        result = group_by_count(elements, element_count=3)
        assert len(result) == 2
        assert all(len(g) == 3 for g in result)

    def test_remainder_group(self):
        elements = [make_element() for _ in range(7)]
        result = group_by_count(elements, element_count=3)
        assert len(result) == 3
        assert len(result[0]) == 3
        assert len(result[1]) == 3
        assert len(result[2]) == 1

    def test_fewer_than_count(self):
        elements = [make_element() for _ in range(2)]
        result = group_by_count(elements, element_count=10)
        assert len(result) == 1
        assert len(result[0]) == 2


class TestGroupBySize:

    def test_empty_input(self):
        assert group_by_size([]) == []

    def test_small_elements_grouped(self):
        elements = [make_element(text="Hi") for _ in range(5)]
        result = group_by_size(elements, max_size=100)
        assert len(result) == 1

    def test_splits_at_size_limit(self):
        elements = [make_element(text="x" * 100) for _ in range(5)]
        result = group_by_size(elements, max_size=250)
        # 2 elements per group (200 chars), then split
        assert len(result) == 3
        assert len(result[0]) == 2
        assert len(result[1]) == 2
        assert len(result[2]) == 1

    def test_large_element_own_group(self):
        elements = [
            make_element(text="small"),
            make_element(text="x" * 5000),  # Exceeds max
            make_element(text="small"),
        ]
        result = group_by_size(elements, max_size=100)
        assert len(result) == 3

    def test_respects_element_boundaries(self):
        # Each element is 50 chars, max is 120
        # Should get 2 per group, not split mid-element
        elements = [make_element(text="x" * 50) for _ in range(5)]
        result = group_by_size(elements, max_size=120)
        assert len(result) == 3
        assert len(result[0]) == 2
        assert len(result[1]) == 2
        assert len(result[2]) == 1


class TestGetStrategy:

    def test_all_strategies_accessible(self):
        for name in STRATEGIES:
            fn = get_strategy(name)
            assert callable(fn)

    def test_unknown_strategy_raises(self):
        with pytest.raises(ValueError, match="Unknown section strategy"):
            get_strategy("nonexistent")

    def test_returns_correct_function(self):
        assert get_strategy("whole-document") is group_whole_document
        assert get_strategy("heading") is group_by_heading
        assert get_strategy("element-type") is group_by_element_type
        assert get_strategy("count") is group_by_count
        assert get_strategy("size") is group_by_size
