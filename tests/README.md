# TrustGraph Configurator Test Suite

Comprehensive pytest-based test suite for trustgraph-configurator.

## Installation

Install with development dependencies:

```bash
pip install -e .[dev]
```

## Running Tests

```bash
# All tests
pytest

# Specific category
pytest tests/unit/
pytest tests/integration/
pytest tests/validation/

# By marker
pytest -m unit
pytest -m integration
pytest -m validation

# Specific test file
pytest tests/unit/test_generator.py

# Parallel execution (faster)
pytest -n auto

# Verbose output
pytest -v

# Stop on first failure
pytest -x

# With coverage
pytest --cov=trustgraph_configurator --cov-report=html
```

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── unit/                    # Unit tests for Python modules
│   ├── test_generator.py
│   ├── test_packager.py
│   ├── test_api.py
│   └── test_run.py
├── integration/             # Full workflow tests
│   ├── test_compilation.py  # Template compilation matrix
│   ├── test_cli.py          # CLI interface tests
│   └── test_errors.py       # Error handling tests
├── validation/              # Output validation tests
│   ├── test_syntax.py       # Syntax validation
│   ├── test_schema.py       # Schema validation
│   ├── test_semantics_k8s.py
│   ├── test_semantics_docker.py
│   └── test_semantics_tg.py
├── validators/              # Validation helper modules
│   ├── kubernetes.py
│   ├── docker_compose.py
│   └── trustgraph.py
├── schemas/                 # JSON schemas
│   ├── trustgraph-config.schema.json
│   ├── kubernetes-resource.schema.json
│   └── docker-compose.schema.json
└── configs/                 # Test input configs
    ├── minimal.json
    ├── complex-rag.json
    ├── multi-service.json
    └── cloud-aws.json
```

## Test Categories

### Unit Tests (`tests/unit/`)
Test individual Python modules in isolation:
- Generator: Jsonnet template processing
- Packager: Configuration assembly and zip creation
- API: Template listing and version resolution
- Run: CLI entry point and argument parsing

### Integration Tests (`tests/integration/`)
Test full workflow end-to-end:
- **Compilation**: Template compilation across all version/platform/config combinations (192 tests)
- **CLI**: Command line interface functionality
- **Errors**: Error handling and reporting

### Validation Tests (`tests/validation/`)
Verify correctness of generated outputs:
- **Syntax**: JSON/YAML parsing validation
- **Schema**: JSON Schema compliance
- **Semantics**: Cross-references, consistency checks

## Test Matrix

Integration tests cover:
- **Versions**: 1.6, 1.7, 1.8
- **Platforms**: docker-compose, podman-compose, minikube-k8s, gcp-k8s, aks-k8s, eks-k8s, scw-k8s, ovh-k8s
- **Configs**: minimal, complex-rag, multi-service, cloud-aws

Total: 3 versions × 8 platforms × 4 configs × 2 outputs = 192 test combinations

## Validation Layers

### Syntax Validation
- JSON parsing with `json.loads()`
- YAML parsing with `yaml.safe_load()`

### Schema Validation
- TrustGraph config against `trustgraph-config.schema.json`
- Docker Compose against `docker-compose.schema.json`
- Kubernetes resources against `kubernetes-resource.schema.json`

### Semantic Validation

**Kubernetes:**
- Deployment selectors match pod labels
- Service selectors match deployment labels
- volumeMounts reference defined volumes
- ConfigMap/Secret references exist
- Service targetPorts match container ports

**Docker Compose:**
- depends_on references valid services
- Volume names are defined
- Network references are valid
- No port conflicts

**TrustGraph Config:**
- Service references are valid
- Parameter types are reasonable
- Storage backends are consistent
- LLM configuration is present

## Fixtures

Available in `conftest.py`:
- `test_config_dir`: Path to test configs
- `test_configs`: Loaded test configurations
- `temp_output_dir`: Temporary directory for outputs
- `run_configurator`: Function to execute configurator
- `mock_config_file`: Create temporary config files

## CI/CD

Tests run automatically on pull requests via GitHub Actions.

See `.github/workflows/pull-request.yaml` for CI configuration.

## Development

### Adding New Tests

1. Create test file in appropriate directory
2. Use appropriate markers (`@pytest.mark.unit`, etc.)
3. Use fixtures from `conftest.py`
4. Follow naming convention: `test_*.py`, `test_*()` functions

### Adding New Validation

1. Add validation logic to `tests/validators/`
2. Create corresponding tests in `tests/validation/`
3. Update schemas in `tests/schemas/` if needed

## Troubleshooting

**Test failures:**
- Check stderr output for error messages
- Run with `-v` for verbose output
- Run with `--tb=long` for full tracebacks

**Import errors:**
- Ensure package is installed: `pip install -e .[dev]`
- Check PYTHONPATH includes project root

**Slow tests:**
- Use `-n auto` for parallel execution
- Run specific test subsets instead of full suite

## Documentation

See `docs/tech-specs/tests.md` for detailed test specification.
