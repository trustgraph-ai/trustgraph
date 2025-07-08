# tg-init-trustgraph

Initializes Pulsar with TrustGraph tenant, namespaces, and configuration settings.

## Synopsis

```bash
tg-init-trustgraph [options]
```

## Description

The `tg-init-trustgraph` command initializes the Apache Pulsar messaging system with the required tenant, namespaces, policies, and configuration needed for TrustGraph operation. This is a foundational setup command that must be run before TrustGraph can operate properly.

The command creates the necessary Pulsar infrastructure and optionally loads initial configuration data into the system.

## Options

### Optional Arguments

- `-p, --pulsar-admin-url URL`: Pulsar admin URL (default: `http://pulsar:8080`)
- `--pulsar-host HOST`: Pulsar host for client connections (default: `pulsar://pulsar:6650`)
- `--pulsar-api-key KEY`: Pulsar API key for authentication
- `-c, --config CONFIG`: Initial configuration JSON to load
- `-t, --tenant TENANT`: Tenant name (default: `tg`)

## Examples

### Basic Initialization
```bash
tg-init-trustgraph
```

### Custom Pulsar Configuration
```bash
tg-init-trustgraph \
  --pulsar-admin-url http://localhost:8080 \
  --pulsar-host pulsar://localhost:6650
```

### With Initial Configuration
```bash
tg-init-trustgraph \
  --config '{"prompt": {"system": "You are a helpful AI assistant"}}'
```

### Custom Tenant
```bash
tg-init-trustgraph --tenant production-tg
```

### Production Setup
```bash
tg-init-trustgraph \
  --pulsar-admin-url http://pulsar-cluster:8080 \
  --pulsar-host pulsar://pulsar-cluster:6650 \
  --pulsar-api-key "your-api-key" \
  --tenant production \
  --config "$(cat production-config.json)"
```

## What It Creates

### Tenant Structure
The command creates a TrustGraph tenant with the following namespaces:

#### Flow Namespace (`tg/flow`)
- **Purpose**: Processing workflows and flow definitions
- **Retention**: Default retention policies

#### Request Namespace (`tg/request`)
- **Purpose**: Incoming API requests and commands
- **Retention**: Default retention policies

#### Response Namespace (`tg/response`)
- **Purpose**: API responses and results
- **Retention**: 3 minutes, unlimited size
- **Subscription Expiration**: 30 minutes

#### Config Namespace (`tg/config`)
- **Purpose**: System configuration and settings
- **Retention**: 10MB size limit, unlimited time
- **Subscription Expiration**: 5 minutes

### Configuration Loading

If a configuration is provided, the command also:
1. Connects to the configuration service
2. Loads the provided configuration data
3. Ensures configuration versioning is maintained

## Configuration Format

The configuration should be provided as JSON with this structure:

```json
{
  "prompt": {
    "system": "System prompt text",
    "template-index": ["template1", "template2"],
    "template.template1": {
      "id": "template1",
      "prompt": "Template text with {{variables}}",
      "response-type": "text"
    }
  },
  "token-costs": {
    "gpt-4": {
      "input_price": 0.00003,
      "output_price": 0.00006
    }
  },
  "agent": {
    "tool-index": ["tool1"],
    "tool.tool1": {
      "id": "tool1",
      "name": "Example Tool",
      "description": "Tool description",
      "arguments": []
    }
  }
}
```

## Use Cases

### Initial Deployment
```bash
# Complete TrustGraph initialization sequence
initialize_trustgraph() {
  echo "Initializing TrustGraph infrastructure..."
  
  # Wait for Pulsar to be ready
  wait_for_pulsar
  
  # Initialize Pulsar Manager (if using)
  tg-init-pulsar-manager
  
  # Initialize TrustGraph
  tg-init-trustgraph \
    --config "$(cat initial-config.json)"
  
  echo "TrustGraph initialization complete!"
}

wait_for_pulsar() {
  local timeout=300
  local elapsed=0
  
  while ! curl -s http://pulsar:8080/admin/v2/clusters > /dev/null; do
    if [ $elapsed -ge $timeout ]; then
      echo "Timeout waiting for Pulsar"
      exit 1
    fi
    echo "Waiting for Pulsar..."
    sleep 5
    elapsed=$((elapsed + 5))
  done
}
```

### Environment-Specific Setup
```bash
# Development environment
setup_dev() {
  tg-init-trustgraph \
    --pulsar-admin-url http://localhost:8080 \
    --pulsar-host pulsar://localhost:6650 \
    --tenant dev \
    --config "$(cat dev-config.json)"
}

# Staging environment
setup_staging() {
  tg-init-trustgraph \
    --pulsar-admin-url http://staging-pulsar:8080 \
    --pulsar-host pulsar://staging-pulsar:6650 \
    --tenant staging \
    --config "$(cat staging-config.json)"
}

# Production environment
setup_production() {
  tg-init-trustgraph \
    --pulsar-admin-url http://prod-pulsar:8080 \
    --pulsar-host pulsar://prod-pulsar:6650 \
    --pulsar-api-key "$PULSAR_API_KEY" \
    --tenant production \
    --config "$(cat production-config.json)"
}
```

### Configuration Management
```bash
# Load different configurations
load_ai_config() {
  local config='{
    "prompt": {
      "system": "You are an AI assistant specialized in data analysis.",
      "template-index": ["analyze", "summarize"],
      "template.analyze": {
        "id": "analyze",
        "prompt": "Analyze this data: {{data}}",
        "response-type": "json"
      }
    },
    "token-costs": {
      "gpt-4": {"input_price": 0.00003, "output_price": 0.00006},
      "claude-3-sonnet": {"input_price": 0.000003, "output_price": 0.000015}
    }
  }'
  
  tg-init-trustgraph --config "$config"
}

load_research_config() {
  local config='{
    "prompt": {
      "system": "You are a research assistant focused on academic literature.",
      "template-index": ["research", "citation"],
      "template.research": {
        "id": "research",
        "prompt": "Research question: {{question}}\nContext: {{context}}",
        "response-type": "text"
      }
    }
  }'
  
  tg-init-trustgraph --config "$config"
}
```

## Advanced Usage

### Cluster Setup
```bash
# Multi-cluster initialization
setup_cluster() {
  local clusters=("cluster1:8080" "cluster2:8080" "cluster3:8080")
  
  for cluster in "${clusters[@]}"; do
    echo "Initializing cluster: $cluster"
    
    tg-init-trustgraph \
      --pulsar-admin-url "http://$cluster" \
      --pulsar-host "pulsar://${cluster%:*}:6650" \
      --tenant "cluster-$(echo $cluster | cut -d: -f1)" \
      --config "$(cat cluster-config.json)"
  done
}
```

### Configuration Migration
```bash
# Migrate configuration between environments
migrate_config() {
  local source_env="$1"
  local target_env="$2"
  
  echo "Migrating configuration from $source_env to $target_env"
  
  # Export existing configuration (would need a tg-export-config command)
  # For now, assume we have the config in a file
  
  tg-init-trustgraph \
    --pulsar-admin-url "http://$target_env:8080" \
    --pulsar-host "pulsar://$target_env:6650" \
    --config "$(cat ${source_env}-config.json)"
}
```

### Validation and Testing
```bash
# Validate initialization
validate_initialization() {
  local tenant="${1:-tg}"
  local admin_url="${2:-http://pulsar:8080}"
  
  echo "Validating TrustGraph initialization..."
  
  # Check tenant exists
  if curl -s "$admin_url/admin/v2/tenants/$tenant" > /dev/null; then
    echo "✓ Tenant '$tenant' exists"
  else
    echo "✗ Tenant '$tenant' missing"
    return 1
  fi
  
  # Check namespaces
  local namespaces=("flow" "request" "response" "config")
  for ns in "${namespaces[@]}"; do
    if curl -s "$admin_url/admin/v2/namespaces/$tenant/$ns" > /dev/null; then
      echo "✓ Namespace '$tenant/$ns' exists"
    else
      echo "✗ Namespace '$tenant/$ns' missing"
      return 1
    fi
  done
  
  echo "✓ TrustGraph initialization validated"
}

# Test configuration loading
test_config_loading() {
  local test_config='{
    "test": {
      "value": "test-value",
      "timestamp": "'$(date -Iseconds)'"
    }
  }'
  
  echo "Testing configuration loading..."
  
  if tg-init-trustgraph --config "$test_config"; then
    echo "✓ Configuration loading successful"
  else
    echo "✗ Configuration loading failed"
    return 1
  fi
}
```

### Retry Logic and Error Handling
```bash
# Robust initialization with retry
robust_init() {
  local max_attempts=5
  local attempt=1
  local delay=10
  
  while [ $attempt -le $max_attempts ]; do
    echo "Initialization attempt $attempt of $max_attempts..."
    
    if tg-init-trustgraph "$@"; then
      echo "✓ Initialization successful on attempt $attempt"
      return 0
    else
      echo "✗ Attempt $attempt failed"
      
      if [ $attempt -lt $max_attempts ]; then
        echo "Waiting ${delay}s before retry..."
        sleep $delay
        delay=$((delay * 2))  # Exponential backoff
      fi
    fi
    
    attempt=$((attempt + 1))
  done
  
  echo "✗ All initialization attempts failed"
  return 1
}
```

## Docker Integration

### Docker Compose
```yaml
version: '3.8'

services:
  pulsar:
    image: apachepulsar/pulsar:latest
    ports:
      - "6650:6650"
      - "8080:8080"
    command: bin/pulsar standalone
    
  trustgraph-init:
    image: trustgraph/cli:latest
    depends_on:
      - pulsar
    volumes:
      - ./config.json:/config.json:ro
    command: >
      sh -c "
        sleep 30 &&
        tg-init-trustgraph --config '$$(cat /config.json)'
      "
    environment:
      - TRUSTGRAPH_PULSAR_ADMIN_URL=http://pulsar:8080
      - TRUSTGRAPH_PULSAR_HOST=pulsar://pulsar:6650
```

### Kubernetes Init Container
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: trustgraph-config
data:
  config.json: |
    {
      "prompt": {
        "system": "You are a helpful AI assistant."
      }
    }
---
apiVersion: batch/v1
kind: Job
metadata:
  name: trustgraph-init
spec:
  template:
    spec:
      initContainers:
      - name: wait-for-pulsar
        image: busybox
        command:
        - sh
        - -c
        - |
          until nc -z pulsar 8080; do
            echo "Waiting for Pulsar..."
            sleep 5
          done
      containers:
      - name: init
        image: trustgraph/cli:latest
        command:
        - tg-init-trustgraph
        - --pulsar-admin-url=http://pulsar:8080
        - --pulsar-host=pulsar://pulsar:6650
        - --config=$(cat /config/config.json)
        volumeMounts:
        - name: config
          mountPath: /config
      volumes:
      - name: config
        configMap:
          name: trustgraph-config
      restartPolicy: Never
```

## Error Handling

### Connection Issues
```bash
Exception: Connection refused
```
**Solution**: Verify Pulsar is running and accessible at the specified admin URL.

### Authentication Errors
```bash
Exception: 401 Unauthorized
```
**Solution**: Check Pulsar API key if authentication is enabled.

### Tenant Creation Failures
```bash
Exception: Tenant creation failed
```
**Solution**: Verify admin permissions and cluster configuration.

### Configuration Loading Errors
```bash
Exception: Invalid JSON configuration
```
**Solution**: Validate JSON syntax and structure.

## Security Considerations

### API Key Management
```bash
# Use environment variables for sensitive data
export PULSAR_API_KEY="your-secure-api-key"
tg-init-trustgraph --pulsar-api-key "$PULSAR_API_KEY"

# Or use a secure file
tg-init-trustgraph --pulsar-api-key "$(cat /secure/pulsar-key.txt)"
```

### Network Security
```bash
# Use TLS for production
tg-init-trustgraph \
  --pulsar-admin-url https://secure-pulsar:8443 \
  --pulsar-host pulsar+ssl://secure-pulsar:6651
```

## Related Commands

- [`tg-init-pulsar-manager`](tg-init-pulsar-manager.md) - Initialize Pulsar Manager
- [`tg-show-config`](tg-show-config.md) - Display current configuration
- [`tg-set-prompt`](tg-set-prompt.md) - Configure individual prompts

## Best Practices

1. **Run Once**: Typically run once per environment during initial setup
2. **Idempotent**: Safe to run multiple times - existing resources are preserved
3. **Configuration**: Always load initial configuration during setup
4. **Validation**: Verify initialization success with validation scripts
5. **Environment Variables**: Use environment variables for sensitive configuration
6. **Retry Logic**: Implement retry logic for robust deployments
7. **Monitoring**: Monitor namespace and topic creation for issues

## Troubleshooting

### Pulsar Not Ready
```bash
# Check Pulsar health
curl http://pulsar:8080/admin/v2/clusters

# Check Pulsar logs
docker logs pulsar
```

### Permission Issues
```bash
# Verify Pulsar admin access
curl http://pulsar:8080/admin/v2/tenants

# Check API key validity if using authentication
```

### Configuration Validation
```bash
# Validate JSON configuration
echo "$CONFIG" | jq .

# Test configuration loading separately
tg-init-trustgraph --config '{"test": "value"}'
```