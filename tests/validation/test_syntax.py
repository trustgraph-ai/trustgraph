"""
Syntax validation tests for generated outputs.
"""

import pytest
import json
import yaml


@pytest.mark.validation
@pytest.mark.parametrize("platform", ["docker-compose", "minikube-k8s"])
@pytest.mark.parametrize("config", ["minimal.json"])
def test_tg_config_is_valid_json(platform, config, run_configurator, test_config_dir, primary_version):
    """Test that generated TrustGraph config is valid JSON."""
    config_file = str(test_config_dir / config)

    stdout, stderr, code = run_configurator([
        '-t', primary_version,
        '-p', platform,
        '-i', config_file,
        '--latest-stable',
        '-O'
    ])

    assert code == 0

    # Should parse as valid JSON
    try:
        parsed = json.loads(stdout)
        assert parsed is not None
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON: {e}")


@pytest.mark.validation
@pytest.mark.parametrize("platform", ["docker-compose", "minikube-k8s"])
@pytest.mark.parametrize("config", ["minimal.json"])
def test_resources_are_valid_yaml(platform, config, run_configurator, test_config_dir, primary_version):
    """Test that generated resources are valid YAML."""
    config_file = str(test_config_dir / config)

    stdout, stderr, code = run_configurator([
        '-t', primary_version,
        '-p', platform,
        '-i', config_file,
        '--latest-stable',
        '-R'
    ])

    assert code == 0

    # Should parse as valid YAML
    try:
        parsed = yaml.safe_load(stdout)
        assert parsed is not None
    except yaml.YAMLError as e:
        pytest.fail(f"Invalid YAML: {e}")
