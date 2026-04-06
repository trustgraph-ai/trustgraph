# TrustGraph Configurator Test Strategy

## Executive Summary

The TrustGraph configurator's primary risk is shipping broken configurations that fail to deploy properly. Unlike application crashes (which are obvious and easily fixable), configuration errors can cause silent failures, deployment issues, or runtime problems that are difficult to debug and significantly impact user experience.

This test strategy prioritizes **configuration correctness** and **deployability** over code coverage metrics.

## Risk Assessment

### High Impact Risks
1. **Template Syntax Errors**: Jsonnet compilation failures that prevent configuration generation
2. **Invalid Configuration Structure**: Generated configs that don't match expected schemas
3. **Missing Dependencies**: Component configurations that reference non-existent services
4. **Platform-Specific Issues**: Configurations that work on one platform but fail on another
5. **Version Incompatibilities**: Template changes that break existing user configurations

### Medium Impact Risks
1. **Performance Issues**: Inefficient template processing
2. **Resource Misconfigurations**: Incorrect memory/CPU limits
3. **Security Misconfigurations**: Missing security settings or exposed secrets

### Low Impact Risks
1. **CLI Argument Parsing**: Easily debuggable and obvious failures
2. **Logging Issues**: Don't affect configuration correctness
3. **API Error Handling**: Obvious failures with clear error messages

## Testing Strategy

### 1. Configuration Validation Tests (Critical)

#### Template Compilation Tests
- **Objective**: Ensure all Jsonnet templates compile without errors
- **Scope**: All templates in all versions (0.21, 0.22, 0.23, 1.0, 1.1)
- **Implementation**:
  ```bash
  # Test all platform configurations for each template version
  for version in 0.21 0.22 0.23 1.0 1.1; do
    for platform in docker-compose podman-compose minikube-k8s gcp-k8s aks-k8s eks-k8s scw-k8s; do
      ./scripts/tg-build-deployment --template $version --platform $platform --input test-configs/minimal.json -O > /dev/null
    done
  done
  ```

#### Schema Validation Tests
- **Objective**: Validate generated configurations against expected schemas
- **Docker Compose**: Validate against docker-compose schema
- **Kubernetes**: Validate against Kubernetes resource schemas
- **TrustGraph Config**: Validate against TrustGraph configuration schema

#### Component Integration Tests
- **Objective**: Ensure component dependencies are correctly resolved
- **Test Cases**:
  - LLM + Embeddings combinations (OpenAI + HF, Ollama + Ollama, etc.)
  - RAG pipelines with all storage backends
  - Graph databases with different embedding stores
  - OCR + document processing chains

### 2. Platform-Specific Deployment Tests (Critical)

#### Docker Compose Validation
- **Objective**: Ensure generated docker-compose.yaml files are valid and deployable
- **Test Environment**: Local Docker daemon
- **Test Process**:
  ```bash
  # Generate configuration
  ./scripts/tg-build-deployment --template 1.1 --platform docker-compose --input test-config.json -R > docker-compose.yaml
  
  # Validate syntax
  docker-compose config -q
  
  # Test deployment (dry-run)
  docker-compose up --no-start
  
  # Test actual deployment with minimal config
  docker-compose up -d
  timeout 60 docker-compose ps
  docker-compose down
  ```

#### Kubernetes Validation
- **Objective**: Ensure generated Kubernetes manifests are valid and deployable
- **Test Environment**: Minikube or kind cluster
- **Test Process**:
  ```bash
  # Generate configuration
  ./scripts/tg-build-deployment --template 1.1 --platform gcp-k8s --input test-config.json -R > resources.yaml
  
  # Validate syntax
  kubectl apply --dry-run=client -f resources.yaml
  
  # Test deployment
  kubectl apply -f resources.yaml
  kubectl wait --for=condition=Ready pod --all --timeout=300s
  kubectl delete -f resources.yaml
  ```

### 3. Configuration Matrix Tests (High Priority)

#### Test Configuration Profiles
Create comprehensive test configurations covering:

1. **Minimal Configuration**
   ```json
   {
     "llm": {"engine": "openai", "model": "gpt-3.5-turbo"},
     "embeddings": {"engine": "hf", "model": "sentence-transformers/all-MiniLM-L6-v2"}
   }
   ```

2. **Complex RAG Configuration**
   ```json
   {
     "llm": {"engine": "openai"},
     "embeddings": {"engine": "hf"},
     "vector_store": {"engine": "qdrant"},
     "graph_store": {"engine": "neo4j"},
     "document_store": {"engine": "cassandra"},
     "rag": {"enabled": true, "chunking": "recursive"}
   }
   ```

3. **Multi-Service Configuration**
   ```json
   {
     "llm": [
       {"engine": "openai", "model": "gpt-4"},
       {"engine": "ollama", "model": "llama2"}
     ],
     "embeddings": {"engine": "fastembed"},
     "vector_store": {"engine": "milvus"},
     "monitoring": {"grafana": true, "prometheus": true}
   }
   ```

4. **Cloud-Specific Configurations**
   - AWS Bedrock + EKS
   - Azure OpenAI + AKS
   - Google Vertex AI + GKE

#### Cross-Platform Matrix
Test each configuration profile against all supported platforms:
- docker-compose
- podman-compose
- minikube-k8s
- gcp-k8s
- aks-k8s
- eks-k8s
- scw-k8s

### 4. Version Compatibility Tests (Medium Priority)

#### Backward Compatibility
- **Objective**: Ensure new template versions don't break existing configurations
- **Process**:
  1. Collect real-world configuration examples
  2. Test against new template versions
  3. Validate that outputs remain functionally equivalent

#### Forward Compatibility
- **Objective**: Ensure template changes don't break when new features are added
- **Process**:
  1. Test configurations with unknown/future parameters
  2. Verify graceful degradation or clear error messages

### 5. Integration Tests (Medium Priority)

#### End-to-End Deployment Tests
- **Objective**: Verify complete deployment workflows
- **Test Cases**:
  - Generate config → Deploy → Verify services start → Run basic functionality test
  - Test with monitoring enabled (Grafana/Prometheus accessible)
  - Test with different storage backends

#### Resource Generation Tests
- **Objective**: Verify auxiliary resources are correctly generated
- **Test Cases**:
  - Grafana dashboards are valid JSON
  - Prometheus config is valid YAML
  - All required secrets/configmaps are created

### 6. Regression Tests (High Priority)

#### Template Change Validation
- **Objective**: Detect when template changes break existing configurations
- **Process**:
  1. Maintain golden configurations for each version
  2. Generate outputs before and after changes
  3. Compare outputs for breaking changes
  4. Flag any structural differences for manual review

#### Component Regression Tests
- **Objective**: Ensure component updates don't break integrations
- **Test Cases**:
  - Component parameter changes
  - New component additions
  - Component deprecations

## Test Implementation Framework

### Test Infrastructure

#### Test Configuration Repository
```
tests/
├── configs/
│   ├── minimal.json
│   ├── complex-rag.json
│   ├── multi-service.json
│   └── cloud-specific/
├── golden/
│   ├── 1.1/
│   │   ├── docker-compose/
│   │   └── k8s/
│   └── 1.0/
├── schemas/
│   ├── docker-compose.json
│   ├── k8s-resources.json
│   └── trustgraph-config.json
└── scripts/
    ├── test-all-platforms.sh
    ├── validate-schemas.sh
    └── deploy-test.sh
```

#### Automated Test Pipeline
```bash
#!/bin/bash
# test-all-platforms.sh

set -e

VERSIONS="0.21 0.22 0.23 1.0 1.1"
PLATFORMS="docker-compose podman-compose minikube-k8s gcp-k8s aks-k8s eks-k8s scw-k8s"
CONFIGS="minimal.json complex-rag.json multi-service.json"

echo "Testing configuration generation..."
for version in $VERSIONS; do
  for platform in $PLATFORMS; do
    for config in $CONFIGS; do
      echo "Testing $version/$platform/$config"
      
      # Test TrustGraph config generation
      ./scripts/tg-build-deployment --template $version --platform $platform \
        --input tests/configs/$config -O > /tmp/tg-config.json
      
      # Validate TrustGraph config
      ./tests/scripts/validate-tg-config.sh /tmp/tg-config.json
      
      # Test resource generation
      ./scripts/tg-build-deployment --template $version --platform $platform \
        --input tests/configs/$config -R > /tmp/resources.yaml
      
      # Validate resources
      ./tests/scripts/validate-resources.sh /tmp/resources.yaml $platform
      
      echo "✓ $version/$platform/$config passed"
    done
  done
done
```

### Test Execution Strategy

#### Continuous Integration
1. **Pre-commit**: Template syntax validation
2. **Pull Request**: Full configuration matrix tests
3. **Release**: Deployment tests + regression tests

#### Performance Testing
- Template processing time benchmarks
- Memory usage during large configuration generation
- Concurrent API request handling

#### Security Testing
- Validate no secrets are exposed in generated configs
- Test secret injection mechanisms
- Validate security-related component configurations

## Test Metrics and Success Criteria

### Primary Success Metrics
1. **Configuration Validity**: 100% of generated configurations must be syntactically valid
2. **Deployment Success**: 95% of generated configurations must deploy successfully
3. **Regression Prevention**: Zero breaking changes to existing configurations without explicit versioning

### Secondary Success Metrics
1. **Test Coverage**: All template versions × all platforms × all major components
2. **Performance**: Configuration generation < 10 seconds for complex configs
3. **Documentation**: All test failures must have clear error messages and remediation steps

## Maintenance and Updates

### Test Maintenance
- Update test configurations when new features are added
- Refresh golden configurations when intentional changes are made
- Review and update schemas when component APIs change

### Test Infrastructure Updates
- Add new platforms when supported
- Update validation tools when dependencies change
- Maintain test environments (Docker, Kubernetes clusters)

## Risk Mitigation

### High-Risk Changes
Any changes to the following require full test suite execution:
- Jsonnet template files
- Component definitions
- Engine implementations
- Version configuration changes

### Emergency Procedures
- Rollback plan for broken template releases
- Hotfix process for critical configuration issues
- Communication plan for notifying users of breaking changes

## Conclusion

This test strategy prioritizes what matters most: ensuring users receive working, deployable configurations. By focusing on configuration correctness over code coverage, we can prevent the high-impact failures that would significantly affect user experience while maintaining development velocity for lower-risk changes.