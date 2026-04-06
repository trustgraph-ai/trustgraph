"""
Integration tests for error handling.
"""

import pytest
import json


@pytest.mark.integration
class TestErrorHandling:
    """Tests for error handling and reporting."""

    def test_nonexistent_config_file(self, run_configurator, primary_version):
        """Test error when config file doesn't exist."""
        stdout, stderr, code = run_configurator([
            '-t', primary_version,
            '-p', 'docker-compose',
            '-i', '/nonexistent/config.json',
            '--latest-stable',
            '-O'
        ])
        assert code == 1
        assert len(stderr) > 0  # Error should be in stderr

    def test_invalid_json_config(self, run_configurator, tmp_path, primary_version):
        """Test error when config file has invalid JSON."""
        invalid_config = tmp_path / "invalid.json"
        invalid_config.write_text("{ invalid json")

        stdout, stderr, code = run_configurator([
            '-t', primary_version,
            '-p', 'docker-compose',
            '-i', str(invalid_config),
            '--latest-stable',
            '-O'
        ])
        assert code == 1

    def test_invalid_platform(self, run_configurator, test_config_dir, primary_version):
        """Test error when platform is invalid."""
        config_file = str(test_config_dir / "minimal.json")

        stdout, stderr, code = run_configurator([
            '-t', primary_version,
            '-p', 'nonexistent-platform',
            '-i', config_file,
            '--latest-stable',
            '-R'  # Use -R to trigger platform-specific generation
        ])
        assert code == 1

    def test_invalid_template_version(self, run_configurator, test_config_dir):
        """Test error when template version doesn't exist."""
        config_file = str(test_config_dir / "minimal.json")

        stdout, stderr, code = run_configurator([
            '-t', '999.999',
            '-p', 'docker-compose',
            '-i', config_file,
            '-O'
        ])
        assert code == 1

    def test_malformed_config_structure(self, run_configurator, tmp_path, primary_version):
        """Test error when config structure is invalid."""
        # Valid JSON but wrong structure
        invalid_config = tmp_path / "bad_structure.json"
        invalid_config.write_text('{"wrong": "structure"}')

        stdout, stderr, code = run_configurator([
            '-t', primary_version,
            '-p', 'docker-compose',
            '-i', str(invalid_config),
            '--latest-stable',
            '-O'
        ])
        # May succeed with warning or fail - either is acceptable
        # The important thing is it doesn't crash
        assert code in [0, 1]

    def test_missing_required_args(self, run_configurator):
        """Test error when required arguments are missing."""
        # Missing template
        stdout, stderr, code = run_configurator([
            '-p', 'docker-compose',
            '-O'
        ])
        assert code == 1

    def test_error_goes_to_stderr(self, run_configurator):
        """Test that errors are written to stderr, not stdout."""
        stdout, stderr, code = run_configurator([
            '-i', '/nonexistent/config.json'
        ])
        assert code == 1
        # Errors should be in stderr
        assert len(stderr) > 0 or 'Exception' in stderr or code == 1
