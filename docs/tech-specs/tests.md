# Test Specification

## Test Categories

### Unit Tests
Test Python modules in isolation:
- **Generator** - Jsonnet template processing, import callbacks
- **Packager** - Zip file creation, configuration assembly
- **API** - Template listing, version resolution
- **CLI** - Argument parsing, error handling, exit codes

### Integration Tests
Test full CLI workflow:
- Template compilation across version/platform/config matrix
- Output file generation (TrustGraph config + platform resources)
- Error propagation and reporting

### Validation Tests
Verify correctness of generated outputs:
- Syntax validation (JSON/YAML parsing)
- Schema validation (structure compliance)
- Semantic validation (cross-references, consistency)
- Regression testing (golden files)

## Test Matrix

**Dimensions:**
- Versions: 1.6, 1.7, 1.8
- Platforms: docker-compose, podman-compose, minikube-k8s, gcp-k8s, aks-k8s, eks-k8s, scw-k8s, ovh-k8s
- Configs: minimal.json, complex-rag.json, multi-service.json, cloud-aws.json

**Total combinations:** 3 versions × 8 platforms × 4 configs = 96 combinations per output type = 192 tests

## Validation Approaches

### Syntax Validation
- **JSON**: Parse with `json.loads()`, check no exceptions
- **YAML**: Parse with `yaml.safe_load()`, check no exceptions
- **Docker Compose**: Validate with `docker-compose config`
- **Kubernetes**: Validate with `kubectl apply --dry-run=client`

### Schema Validation
- **TrustGraph Config**: Define JSON schema, validate with `jsonschema`
  - Required fields: services, modules, parameters
  - Type checking for all configuration values
  - Enum validation for fixed sets (llm providers, platforms)

- **Kubernetes**: Check required fields
  - apiVersion, kind, metadata present
  - metadata.name, metadata.namespace defined
  - spec structure matches resource kind

- **Docker Compose**: Check required fields
  - services defined with image/build
  - Valid port mappings
  - Valid volume definitions

### Semantic Validation

#### Kubernetes Resources
- **Label/Selector matching**: Deployment selectors match pod labels
- **Volume references**: volumeMounts reference defined volumes
- **Service targeting**: Service selectors match deployment labels
- **Port consistency**: containerPort matches service targetPort
- **ConfigMap/Secret references**: Referenced resources exist in manifest

#### Docker Compose
- **Service dependencies**: depends_on references valid services
- **Volume references**: Volume names in bind mounts are defined
- **Network references**: Networks used by services are defined
- **Port conflicts**: No duplicate host port bindings
- **Environment variable references**: ${VAR} expansions are resolvable

#### TrustGraph Config
- **Service references**: Configured services reference valid modules
- **Parameter validation**: Module parameters match schema
- **Storage consistency**: Graph/object/vector stores configured correctly
- **LLM configuration**: Valid model IDs, API configurations

### Golden File Testing
Store reference outputs for each test case:
- **Location**: `tests/golden/{version}/{platform}/{config}/`
- **Files**:
  - `tg-config.json` - Reference TrustGraph configuration
  - `resources.yaml` - Reference platform resources
- **Comparison**: Use `pytest-golden` for automatic diff generation
- **Updates**: Explicit flag to regenerate golden files when intentional changes occur

## Test Cases

### Compilation Tests
For each (version, platform, config) combination:
1. Run `tg-build-deployment -t {version} -p {platform} -i {config} -O`
2. Assert exit code = 0
3. Assert stdout contains valid JSON
4. Parse and validate TrustGraph config structure

5. Run `tg-build-deployment -t {version} -p {platform} -i {config} -R`
6. Assert exit code = 0
7. Assert stdout contains valid YAML
8. Parse and validate resource manifest structure

### Error Handling Tests
- **Invalid config**: Malformed JSON input → exit code 1, error to stderr
- **Missing file**: Non-existent config file → exit code 1, error to stderr
- **Invalid template**: Non-existent version → exit code 1, error to stderr
- **Invalid platform**: Non-existent platform → exit code 1, error to stderr
- **Template errors**: Jsonnet compilation errors → exit code 1, error to stderr

### CLI Interface Tests
- **Argument parsing**: Valid/invalid argument combinations
- **Help output**: `-h` flag displays usage
- **Version display**: Version flag shows package version
- **Output modes**: `-O` and `-R` flags produce correct output types
- **Default values**: Missing optional args use documented defaults

### Module Unit Tests

#### Generator
- `process(config)` - Valid jsonnet → parsed JSON
- `process(config)` - Invalid jsonnet → raises exception
- Import callback mechanism works correctly
- Template loading from package resources

#### Packager
- `write(config, output)` - Creates valid zip file
- `write_tg_config(config)` - Outputs TrustGraph config to stdout
- `write_resources(config)` - Outputs platform resources to stdout
- Template version resolution (--latest, --latest-stable)
- Platform-specific template selection

## Test Execution Methods

### Direct Function Call (Primary Method)
Most tests call the Python entry point function directly rather than invoking the subprocess:

```python
from trustgraph_configurator import run
import sys
import json

def test_basic_compilation(monkeypatch, capsys):
    """Test compilation by calling run() directly"""
    # Mock sys.argv with CLI arguments
    monkeypatch.setattr(sys, 'argv', [
        'tg-build-deployment',
        '-t', '1.8',
        '-p', 'docker-compose',
        '-i', 'tests/configs/minimal.json',
        '-O'
    ])

    # Call the entry point directly
    run.run()

    # Capture and validate output
    captured = capsys.readouterr()
    config = json.loads(captured.out)
    assert 'services' in config
```

**Advantages:**
- **Fast**: No subprocess overhead (100x+ faster)
- **Easy stdout/stderr capture**: Use pytest's `capsys` fixture
- **Easy mocking**: Use `monkeypatch` for arguments, environment, file system
- **Better debugging**: Direct code path, breakpoints work naturally
- **Exit code testing**: Catch `SystemExit` exception to verify exit codes

```python
def test_error_handling(monkeypatch):
    """Test that errors exit with code 1"""
    monkeypatch.setattr(sys, 'argv', [
        'tg-build-deployment',
        '-i', 'nonexistent.json'
    ])

    with pytest.raises(SystemExit) as exc_info:
        run.run()

    assert exc_info.value.code == 1
```

### Subprocess Invocation (Smoke Tests)
A small number of tests (1-2) should invoke the actual CLI executable to verify installation:

```python
import subprocess

def test_cli_executable_installed():
    """Verify the installed CLI entry point works"""
    result = subprocess.run(
        ['tg-build-deployment', '--help'],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert 'usage:' in result.stdout

def test_cli_version_command():
    """Verify version command works from CLI"""
    result = subprocess.run(
        ['tg-build-deployment', '--version'],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
```

**Purpose:**
- Verify `pyproject.toml` entry point configuration is correct
- Verify CLI is accessible in PATH after installation
- End-to-end smoke test

**Limitations:**
- Slower (subprocess overhead)
- Harder to mock/patch
- Less detailed error information

### Fixture for Direct Execution
Create a reusable fixture for calling configurator:

```python
# tests/conftest.py
import pytest
import sys
from io import StringIO

@pytest.fixture
def run_configurator(monkeypatch, capsys):
    """Fixture to run configurator with given arguments"""
    def _run(args):
        """
        Run configurator with args list.
        Returns (stdout, stderr, exit_code)
        """
        from trustgraph_configurator import run

        monkeypatch.setattr(sys, 'argv', ['tg-build-deployment'] + args)

        exit_code = 0
        try:
            run.run()
        except SystemExit as e:
            exit_code = e.code or 0

        captured = capsys.readouterr()
        return captured.out, captured.err, exit_code

    return _run
```

**Usage:**
```python
def test_with_fixture(run_configurator):
    stdout, stderr, code = run_configurator([
        '-t', '1.8',
        '-p', 'docker-compose',
        '-i', 'tests/configs/minimal.json',
        '-O'
    ])
    assert code == 0
    assert json.loads(stdout)
```

## Test Infrastructure

### Pytest Configuration
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "-v",
    "--strict-markers",
    "--cov=trustgraph_configurator",
    "--cov-report=term-missing",
    "--cov-report=html",
]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "validation: Output validation tests",
    "slow: Slow-running tests",
]
```

### Fixtures (`tests/conftest.py`)
- `test_config_dir` - Path to tests/configs/
- `test_configs` - Dict of loaded test configurations
- `temp_output_dir` - Temporary directory for test outputs
- `run_configurator` - Function to execute configurator CLI
- `golden_dir` - Path to golden file directory for test case

### Parametrization
Use `pytest.mark.parametrize` for matrix testing:
```python
@pytest.mark.parametrize("version", ["1.6", "1.7", "1.8"])
@pytest.mark.parametrize("platform", ["docker-compose", "minikube-k8s", ...])
@pytest.mark.parametrize("config", ["minimal.json", "complex-rag.json", ...])
def test_compilation(version, platform, config, run_configurator):
    ...
```

### Parallel Execution
Use pytest-xdist for parallel test execution:
```bash
pytest -n auto  # Use all CPU cores
```

## Test File Organization

```
tests/
├── conftest.py              # Shared fixtures
├── unit/
│   ├── test_generator.py
│   ├── test_packager.py
│   ├── test_api.py
│   └── test_run.py
├── integration/
│   ├── test_compilation.py  # Template compilation matrix
│   ├── test_cli.py          # CLI interface tests
│   └── test_errors.py       # Error handling tests
├── validation/
│   ├── test_syntax.py       # Syntax validation
│   ├── test_schema.py       # Schema validation
│   ├── test_semantics_k8s.py
│   ├── test_semantics_docker.py
│   └── test_semantics_tg.py
├── configs/                 # Test input configs (existing)
├── schemas/                 # JSON schemas for validation
│   ├── trustgraph-config.schema.json
│   ├── kubernetes-deployment.schema.json
│   └── docker-compose.schema.json
├── golden/                  # Reference outputs
│   └── {version}/{platform}/{config}/
│       ├── tg-config.json
│       └── resources.yaml
└── validators/              # Validation helper modules
    ├── kubernetes.py
    ├── docker_compose.py
    └── trustgraph.py
```

## Development Dependencies

Add to pyproject.toml:
```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-xdist>=3.0",      # Parallel execution
    "pytest-cov>=4.0",         # Coverage reporting
    "pytest-golden>=0.2",      # Golden file testing
    "jsonschema>=4.0",         # Schema validation
    "pyyaml>=6.0",             # Already in main deps
]
```

Install for development:
```bash
pip install -e .[dev]
```

## CI/CD Integration

Update `.github/workflows/pull-request.yaml`:
```yaml
- name: Install dependencies
  run: |
    python3 -m venv env
    . env/bin/activate
    pip install -e .[dev]

- name: Run tests
  run: |
    . env/bin/activate
    pytest -n auto --cov --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

## Running Tests

```bash
# All tests
pytest

# Specific category
pytest tests/unit/
pytest tests/integration/
pytest -m validation

# Specific test file
pytest tests/unit/test_generator.py

# Parallel execution
pytest -n auto

# With coverage
pytest --cov=trustgraph_configurator --cov-report=html

# Update golden files
pytest --update-golden

# Verbose output
pytest -v

# Stop on first failure
pytest -x
```
