"""
Unit tests for run module (CLI entry point).
"""

import pytest
import sys


@pytest.mark.unit
class TestRun:
    """Tests for the run module."""

    def test_run_without_args_fails(self, run_configurator):
        """Test that running without required args fails."""
        stdout, stderr, code = run_configurator([])
        assert code != 0

    def test_run_with_help_succeeds(self, run_configurator):
        """Test that help flag works."""
        stdout, stderr, code = run_configurator(['-h'])
        assert code == 0

    def test_run_with_invalid_platform_fails(self, run_configurator, test_config_dir, primary_version):
        """Test that invalid platform fails during resource generation."""
        config_file = str(test_config_dir / "minimal.json")
        stdout, stderr, code = run_configurator([
            '-t', primary_version,
            '-p', 'invalid-platform',
            '-i', config_file,
            '--latest-stable',
            '-R'  # Use -R to trigger platform-specific generation
        ])
        assert code == 1

    def test_run_with_nonexistent_config_fails(self, run_configurator, primary_version):
        """Test that nonexistent config file fails."""
        stdout, stderr, code = run_configurator([
            '-t', primary_version,
            '-p', 'docker-compose',
            '-i', '/nonexistent/config.json',
            '--latest-stable',
            '-O'
        ])
        assert code == 1

    def test_exit_code_propagates(self, monkeypatch):
        """Test that exit codes are properly set."""
        from trustgraph_configurator import run

        # Test successful exit (no exception)
        # This would require a valid config, so we'll just test the error path

        # Test error exit
        monkeypatch.setattr(sys, 'argv', [
            'tg-build-deployment',
            '-i', '/nonexistent/config.json'
        ])

        with pytest.raises(SystemExit) as exc_info:
            run()  # run is already the function

        assert exc_info.value.code == 1
