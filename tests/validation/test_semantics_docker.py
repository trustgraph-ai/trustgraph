"""
Semantic validation tests for Docker Compose resources.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path for validators import
sys.path.insert(0, str(Path(__file__).parent.parent))
from validators import docker_compose


@pytest.mark.validation
@pytest.mark.parametrize("config", ["minimal.json", "complex-rag.json"])
def test_docker_compose_semantic_validation(config, run_configurator, test_config_dir, primary_version):
    """Test semantic validation of Docker Compose resources."""
    config_file = str(test_config_dir / config)

    stdout, stderr, code = run_configurator([
        '-t', primary_version,
        '-p', 'docker-compose',
        '-i', config_file,
        '--latest-stable',
        '-R'
    ])

    assert code == 0

    is_valid, errors = docker_compose.validate_docker_compose_manifest(stdout)

    if not is_valid:
        error_msg = "\n".join(errors)
        pytest.fail(f"Semantic validation failed for {config}:\n{error_msg}")


@pytest.mark.validation
def test_docker_compose_service_dependencies(run_configurator, test_config_dir, primary_version):
    """Test that service dependencies reference valid services."""
    config_file = str(test_config_dir / "minimal.json")

    stdout, stderr, code = run_configurator([
        '-t', primary_version,
        '-p', 'docker-compose',
        '-i', config_file,
        '--latest-stable',
        '-R'
    ])

    assert code == 0

    compose_data = docker_compose.parse_docker_compose_yaml(stdout)
    errors = docker_compose.validate_service_dependencies(compose_data)

    if errors:
        pytest.fail(f"Invalid service dependencies:\n" + "\n".join(errors))


@pytest.mark.validation
def test_docker_compose_no_port_conflicts(run_configurator, test_config_dir, primary_version):
    """Test that there are no port conflicts."""
    config_file = str(test_config_dir / "minimal.json")

    stdout, stderr, code = run_configurator([
        '-t', primary_version,
        '-p', 'docker-compose',
        '-i', config_file,
        '--latest-stable',
        '-R'
    ])

    assert code == 0

    compose_data = docker_compose.parse_docker_compose_yaml(stdout)
    errors = docker_compose.validate_port_conflicts(compose_data)

    if errors:
        pytest.fail(f"Port conflicts detected:\n" + "\n".join(errors))
