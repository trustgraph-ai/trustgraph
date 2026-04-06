"""
Unit tests for Packager class.
"""

import pytest
from trustgraph_configurator.packager import Packager


@pytest.mark.unit
class TestPackager:
    """Tests for the Packager class."""

    def test_init_with_latest_stable(self):
        """Test initialization with latest_stable flag."""
        packager = Packager(
            version=None,
            template=None,
            platform="docker-compose",
            latest=False,
            latest_stable=True
        )
        assert packager.version is not None
        assert packager.template is not None

    def test_init_with_template(self):
        """Test initialization with specific template."""
        packager = Packager(
            version="1.8.12",
            template="1.8",
            platform="docker-compose",
            latest=False,
            latest_stable=False
        )
        assert packager.version == "1.8.12"
        assert packager.template == "1.8"
        assert packager.platform == "docker-compose"

    def test_invalid_platform_raises_error(self):
        """Test that invalid platform raises error during generation."""
        packager = Packager(
            version="1.8.12",
            template="1.8",
            platform="invalid-platform",
            latest=False,
            latest_stable=False
        )

        with pytest.raises(RuntimeError, match="Bad platform"):
            packager.generate('[{"name": "test", "parameters": {}}]')

    def test_init_without_template_raises_error(self):
        """Test that initialization without template/latest raises error."""
        with pytest.raises(RuntimeError, match="You must"):
            Packager(
                version=None,
                template=None,
                platform="docker-compose",
                latest=False,
                latest_stable=False
            )
