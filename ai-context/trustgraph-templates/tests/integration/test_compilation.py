"""
Integration tests for template compilation across all combinations.
"""

import pytest
import json
import yaml

from conftest import TESTED_VERSIONS


@pytest.mark.integration
@pytest.mark.parametrize("version", TESTED_VERSIONS)
@pytest.mark.parametrize("platform", [
    "docker-compose",
    "podman-compose",
    "minikube-k8s",
    "gcp-k8s",
    "aks-k8s",
    "eks-k8s",
    "scw-k8s",
    "ovh-k8s",
])
@pytest.mark.parametrize("config", [
    "minimal.json",
    "complex-rag.json",
    "multi-service.json",
    "cloud-aws.json",
])
def test_tg_config_generation(version, platform, config, run_configurator, test_config_dir):
    """Test TrustGraph config generation for all combinations."""
    config_file = str(test_config_dir / config)

    stdout, stderr, code = run_configurator([
        '-t', version,
        '-p', platform,
        '-i', config_file,
        '--latest-stable',
        '-O'
    ])

    # Should succeed
    assert code == 0, f"Failed for {version}/{platform}/{config}: {stderr}"

    # Should output valid JSON
    try:
        tg_config = json.loads(stdout)
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON output for {version}/{platform}/{config}: {e}")

    # Basic structure checks
    assert isinstance(tg_config, (dict, list)), "TrustGraph config should be dict or list"


@pytest.mark.integration
@pytest.mark.parametrize("version", TESTED_VERSIONS)
@pytest.mark.parametrize("platform", [
    "docker-compose",
    "podman-compose",
    "minikube-k8s",
    "gcp-k8s",
    "aks-k8s",
    "eks-k8s",
    "scw-k8s",
    "ovh-k8s",
])
@pytest.mark.parametrize("config", [
    "minimal.json",
    "complex-rag.json",
    "multi-service.json",
    "cloud-aws.json",
])
def test_resources_generation(version, platform, config, run_configurator, test_config_dir):
    """Test platform resources generation for all combinations."""
    config_file = str(test_config_dir / config)

    stdout, stderr, code = run_configurator([
        '-t', version,
        '-p', platform,
        '-i', config_file,
        '--latest-stable',
        '-R'
    ])

    # Should succeed
    assert code == 0, f"Failed for {version}/{platform}/{config}: {stderr}"

    # Should output valid YAML
    try:
        resources = yaml.safe_load(stdout)
    except yaml.YAMLError as e:
        pytest.fail(f"Invalid YAML output for {version}/{platform}/{config}: {e}")

    # Basic structure checks
    if platform in ["docker-compose", "podman-compose"]:
        assert "services" in resources, "Docker Compose should have services"
    else:
        # Kubernetes resources
        assert resources is not None, "K8s resources should not be empty"


@pytest.mark.integration
def test_compilation_minimal_docker_compose(run_configurator, test_config_dir, primary_version):
    """Smoke test: minimal config on docker-compose."""
    config_file = str(test_config_dir / "minimal.json")

    # Test TG config
    stdout, stderr, code = run_configurator([
        '-t', primary_version,
        '-p', 'docker-compose',
        '-i', config_file,
        '--latest-stable',
        '-O'
    ])

    assert code == 0
    tg_config = json.loads(stdout)
    assert tg_config is not None

    # Test resources
    stdout, stderr, code = run_configurator([
        '-t', primary_version,
        '-p', 'docker-compose',
        '-i', config_file,
        '--latest-stable',
        '-R'
    ])

    assert code == 0
    resources = yaml.safe_load(stdout)
    assert "services" in resources


@pytest.mark.integration
def test_compilation_minimal_k8s(run_configurator, test_config_dir, primary_version):
    """Smoke test: minimal config on k8s."""
    config_file = str(test_config_dir / "minimal.json")

    # Test TG config
    stdout, stderr, code = run_configurator([
        '-t', primary_version,
        '-p', 'minikube-k8s',
        '-i', config_file,
        '--latest-stable',
        '-O'
    ])

    assert code == 0
    tg_config = json.loads(stdout)
    assert tg_config is not None

    # Test resources
    stdout, stderr, code = run_configurator([
        '-t', primary_version,
        '-p', 'minikube-k8s',
        '-i', config_file,
        '--latest-stable',
        '-R'
    ])

    assert code == 0
    resources = yaml.safe_load(stdout)
    assert resources is not None
