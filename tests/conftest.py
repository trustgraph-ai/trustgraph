"""
Pytest configuration and shared fixtures for trustgraph-configurator tests.
"""

import pytest

# =============================================================================
# Version Configuration - Update these when adding new template versions
# =============================================================================
TESTED_VERSIONS = ["1.8", "1.9", "2.0"]
PRIMARY_VERSION = "1.9"  # Used when only one version is tested
import sys
import json
import tempfile
import shutil
from pathlib import Path


@pytest.fixture(scope="session")
def test_config_dir():
    """Path to the test configurations directory."""
    return Path(__file__).parent / "configs"


@pytest.fixture(scope="session")
def test_configs(test_config_dir):
    """Dictionary of loaded test configurations."""
    configs = {}
    for config_file in test_config_dir.glob("*.json"):
        with open(config_file) as f:
            configs[config_file.name] = json.load(f)
    return configs


@pytest.fixture
def temp_output_dir():
    """Temporary directory for test outputs."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def run_configurator(monkeypatch, capsys):
    """
    Fixture to run configurator with given arguments.

    Usage:
        stdout, stderr, exit_code = run_configurator(['-t', '1.8', '-p', 'docker-compose', ...])

    Returns:
        tuple: (stdout, stderr, exit_code)
    """
    def _run(args):
        from trustgraph_configurator import run

        # Set sys.argv with the command and arguments
        monkeypatch.setattr(sys, 'argv', ['tg-build-deployment'] + args)

        exit_code = 0
        try:
            run()  # run is already the function, not a module
        except SystemExit as e:
            exit_code = e.code if e.code is not None else 0

        # Capture output
        captured = capsys.readouterr()
        return captured.out, captured.err, exit_code

    return _run


@pytest.fixture(scope="session")
def golden_dir():
    """Path to the golden files directory."""
    return Path(__file__).parent / "golden"


@pytest.fixture(scope="session")
def test_versions():
    """List of template versions to test."""
    return TESTED_VERSIONS


@pytest.fixture(scope="session")
def primary_version():
    """Primary version for tests that only need one version."""
    return PRIMARY_VERSION


@pytest.fixture(scope="session")
def test_platforms():
    """List of platforms to test."""
    return [
        "docker-compose",
        "podman-compose",
        "minikube-k8s",
        "gcp-k8s",
        "aks-k8s",
        "eks-k8s",
        "scw-k8s",
        "ovh-k8s",
    ]


@pytest.fixture(scope="session")
def test_config_names():
    """List of test configuration file names."""
    return [
        "minimal.json",
        "complex-rag.json",
        "multi-service.json",
        "cloud-aws.json",
    ]


@pytest.fixture
def mock_config_file(tmp_path):
    """Create a temporary config file for testing."""
    def _create(config_data):
        config_file = tmp_path / "test_config.json"
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        return str(config_file)
    return _create
