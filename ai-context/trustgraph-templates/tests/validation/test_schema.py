"""
Schema validation tests for generated outputs.
"""

import pytest
import json
import yaml
import jsonschema
from pathlib import Path


@pytest.fixture(scope="module")
def schemas_dir():
    """Path to schemas directory."""
    return Path(__file__).parent.parent / "schemas"


@pytest.mark.validation
def test_tg_config_matches_schema(run_configurator, test_config_dir, schemas_dir, primary_version):
    """Test that TrustGraph config matches schema."""
    config_file = str(test_config_dir / "minimal.json")

    stdout, stderr, code = run_configurator([
        '-t', primary_version,
        '-p', 'docker-compose',
        '-i', config_file,
        '--latest-stable',
        '-O'
    ])

    assert code == 0

    tg_config = json.loads(stdout)
    schema_file = schemas_dir / "trustgraph-config.schema.json"

    with open(schema_file) as f:
        schema = json.load(f)

    try:
        jsonschema.validate(instance=tg_config, schema=schema)
    except jsonschema.ValidationError as e:
        pytest.fail(f"Schema validation failed: {e}")


@pytest.mark.validation
def test_docker_compose_matches_schema(run_configurator, test_config_dir, schemas_dir, primary_version):
    """Test that Docker Compose output matches schema."""
    config_file = str(test_config_dir / "minimal.json")

    stdout, stderr, code = run_configurator([
        '-t', primary_version,
        '-p', 'docker-compose',
        '-i', config_file,
        '--latest-stable',
        '-R'
    ])

    assert code == 0

    compose_data = yaml.safe_load(stdout)
    schema_file = schemas_dir / "docker-compose.schema.json"

    with open(schema_file) as f:
        schema = json.load(f)

    try:
        jsonschema.validate(instance=compose_data, schema=schema)
    except jsonschema.ValidationError as e:
        pytest.fail(f"Schema validation failed: {e}")


@pytest.mark.validation
def test_kubernetes_resources_match_schema(run_configurator, test_config_dir, schemas_dir, primary_version):
    """Test that Kubernetes resources match schema."""
    config_file = str(test_config_dir / "minimal.json")

    stdout, stderr, code = run_configurator([
        '-t', primary_version,
        '-p', 'minikube-k8s',
        '-i', config_file,
        '--latest-stable',
        '-R'
    ])

    assert code == 0

    resources = yaml.safe_load(stdout)
    schema_file = schemas_dir / "kubernetes-resource.schema.json"

    with open(schema_file) as f:
        schema = json.load(f)

    # Validate the resource (which might be a single resource, list, or K8s List)
    if isinstance(resources, dict):
        # Check if it's a Kubernetes List resource
        if resources.get('kind') == 'List' and 'items' in resources:
            resources_to_validate = resources['items']
        else:
            resources_to_validate = [resources]
    elif isinstance(resources, list):
        resources_to_validate = resources
    else:
        pytest.fail(f"Unexpected resources type: {type(resources)}")

    for resource in resources_to_validate:
        if not isinstance(resource, dict):
            continue  # Skip non-dict items
        try:
            jsonschema.validate(instance=resource, schema=schema)
        except jsonschema.ValidationError as e:
            pytest.fail(f"Schema validation failed for resource: {e}")
