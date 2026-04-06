"""
Unit tests for Index class.
"""

import pytest
from trustgraph_configurator import Index


@pytest.mark.unit
class TestAPI:
    """Tests for the Index class."""

    def test_get_templates_returns_list(self):
        """Test that get_templates returns a list."""
        templates = Index.get_templates()
        assert isinstance(templates, list)
        assert len(templates) > 0

    def test_templates_have_required_fields(self):
        """Test that templates have name and version fields."""
        templates = Index.get_templates()
        for template in templates:
            assert hasattr(template, 'name')
            assert hasattr(template, 'version')

    def test_get_latest_returns_template(self):
        """Test that get_latest returns a template."""
        latest = Index.get_latest()
        assert latest is not None
        assert hasattr(latest, 'name')
        assert hasattr(latest, 'version')

    def test_get_latest_stable_returns_template(self):
        """Test that get_latest_stable returns a template."""
        latest_stable = Index.get_latest_stable()
        assert latest_stable is not None
        assert hasattr(latest_stable, 'name')
        assert hasattr(latest_stable, 'version')
