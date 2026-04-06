"""
Semantic validation tests for Kubernetes resources.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path for validators import
sys.path.insert(0, str(Path(__file__).parent.parent))
from validators import kubernetes


@pytest.mark.validation
@pytest.mark.parametrize("config", ["minimal.json", "complex-rag.json"])
def test_k8s_semantic_validation(config, run_configurator, test_config_dir, primary_version):
    """Test semantic validation of Kubernetes resources."""
    config_file = str(test_config_dir / config)

    stdout, stderr, code = run_configurator([
        '-t', primary_version,
        '-p', 'minikube-k8s',
        '-i', config_file,
        '--latest-stable',
        '-R'
    ])

    assert code == 0

    is_valid, errors = kubernetes.validate_kubernetes_manifest(stdout)

    if not is_valid:
        error_msg = "\n".join(errors)
        pytest.fail(f"Semantic validation failed for {config}:\n{error_msg}")


@pytest.mark.validation
def test_k8s_selector_labels_match(run_configurator, test_config_dir, primary_version):
    """Test that Deployment selectors match pod labels."""
    config_file = str(test_config_dir / "minimal.json")

    stdout, stderr, code = run_configurator([
        '-t', primary_version,
        '-p', 'minikube-k8s',
        '-i', config_file,
        '--latest-stable',
        '-R'
    ])

    assert code == 0

    resources = kubernetes.parse_kubernetes_yaml(stdout)
    errors = kubernetes.validate_selector_labels_match(resources)

    if errors:
        pytest.fail(f"Selector/label mismatch:\n" + "\n".join(errors))


@pytest.mark.validation
def test_k8s_volume_references(run_configurator, test_config_dir, primary_version):
    """Test that volumeMounts reference defined volumes."""
    config_file = str(test_config_dir / "minimal.json")

    stdout, stderr, code = run_configurator([
        '-t', primary_version,
        '-p', 'minikube-k8s',
        '-i', config_file,
        '--latest-stable',
        '-R'
    ])

    assert code == 0

    resources = kubernetes.parse_kubernetes_yaml(stdout)
    errors = kubernetes.validate_volume_references(resources)

    if errors:
        pytest.fail(f"Invalid volume references:\n" + "\n".join(errors))
