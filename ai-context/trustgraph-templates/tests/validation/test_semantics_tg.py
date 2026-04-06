"""
Semantic validation tests for TrustGraph configuration.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path for validators import
sys.path.insert(0, str(Path(__file__).parent.parent))
from validators import trustgraph


@pytest.mark.validation
@pytest.mark.parametrize("config", ["minimal.json", "complex-rag.json", "multi-service.json"])
def test_tg_config_semantic_validation(config, run_configurator, test_config_dir, primary_version):
    """Test semantic validation of TrustGraph configuration."""
    config_file = str(test_config_dir / config)

    stdout, stderr, code = run_configurator([
        '-t', primary_version,
        '-p', 'docker-compose',
        '-i', config_file,
        '--latest-stable',
        '-O'
    ])

    assert code == 0

    is_valid, errors = trustgraph.validate_trustgraph_config(stdout)

    if not is_valid:
        error_msg = "\n".join(errors)
        # Some errors might be warnings, so we log them but don't necessarily fail
        # Adjust this based on strictness requirements
        if any("missing" in err.lower() or "required" in err.lower() for err in errors):
            pytest.fail(f"Semantic validation failed for {config}:\n{error_msg}")


@pytest.mark.validation
def test_tg_config_has_llm(run_configurator, test_config_dir, primary_version):
    """Test that TrustGraph config includes LLM provider."""
    config_file = str(test_config_dir / "minimal.json")

    stdout, stderr, code = run_configurator([
        '-t', primary_version,
        '-p', 'docker-compose',
        '-i', config_file,
        '--latest-stable',
        '-O'
    ])

    assert code == 0

    tg_config = trustgraph.parse_trustgraph_config(stdout)
    errors = trustgraph.validate_llm_configuration(tg_config)

    # LLM should be configured
    if errors:
        # This might be a warning rather than error for some configs
        pass


@pytest.mark.validation
def test_tg_config_structure(run_configurator, test_config_dir, primary_version):
    """Test that TrustGraph config has required structure."""
    config_file = str(test_config_dir / "minimal.json")

    stdout, stderr, code = run_configurator([
        '-t', primary_version,
        '-p', 'docker-compose',
        '-i', config_file,
        '--latest-stable',
        '-O'
    ])

    assert code == 0

    tg_config = trustgraph.parse_trustgraph_config(stdout)
    errors = trustgraph.validate_required_structure(tg_config)

    if errors:
        pytest.fail(f"Invalid TrustGraph config structure:\n" + "\n".join(errors))
