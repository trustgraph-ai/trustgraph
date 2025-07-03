# tg-init-pulsar-manager

Initializes Pulsar Manager with default superuser credentials for TrustGraph.

## Synopsis

```bash
tg-init-pulsar-manager
```

## Description

The `tg-init-pulsar-manager` command is a setup utility that creates a default superuser account in Pulsar Manager. This is typically run once during initial TrustGraph deployment to establish administrative access to the Pulsar message queue management interface.

The command configures a superuser with predefined credentials that can be used to access the Pulsar Manager web interface for monitoring and managing Pulsar topics, namespaces, and tenants.

## Default Configuration

The command creates a superuser with these default credentials:

- **Username**: `admin`
- **Password**: `apachepulsar`
- **Description**: `test`
- **Email**: `username@test.org`

## Prerequisites

### Pulsar Manager Service
Pulsar Manager must be running and accessible at `http://localhost:7750` before running this command.

### Network Connectivity
The command requires network access to the Pulsar Manager API endpoint.

## Examples

### Basic Initialization
```bash
tg-init-pulsar-manager
```

### Verify Initialization
```bash
# Run the initialization
tg-init-pulsar-manager

# Check if Pulsar Manager is accessible
curl -s http://localhost:7750/pulsar-manager/ | grep -q "Pulsar Manager"
echo "Pulsar Manager status: $?"
```

### Integration with Setup Scripts
```bash
#!/bin/bash
# setup-trustgraph.sh

echo "Setting up TrustGraph infrastructure..."

# Wait for Pulsar Manager to be ready
echo "Waiting for Pulsar Manager..."
while ! curl -s http://localhost:7750/pulsar-manager/ > /dev/null; do
  echo "  Waiting for Pulsar Manager to start..."
  sleep 5
done

# Initialize Pulsar Manager
echo "Initializing Pulsar Manager..."
tg-init-pulsar-manager

if [ $? -eq 0 ]; then
  echo "✓ Pulsar Manager initialized successfully"
  echo "  You can access it at: http://localhost:7750/pulsar-manager/"
  echo "  Username: admin"
  echo "  Password: apachepulsar"
else
  echo "✗ Failed to initialize Pulsar Manager"
  exit 1
fi
```

## What It Does

The command performs the following operations:

1. **Retrieves CSRF Token**: Gets a CSRF token from Pulsar Manager for secure API access
2. **Creates Superuser**: Makes an authenticated API call to create the superuser account
3. **Sets Permissions**: Configures the user with administrative privileges

### HTTP Operations
```bash
# Equivalent manual operations:
CSRF_TOKEN=$(curl http://localhost:7750/pulsar-manager/csrf-token)

curl \
    -H "X-XSRF-TOKEN: $CSRF_TOKEN" \
    -H "Cookie: XSRF-TOKEN=$CSRF_TOKEN;" \
    -H 'Content-Type: application/json' \
    -X PUT \
    http://localhost:7750/pulsar-manager/users/superuser \
    -d '{"name": "admin", "password": "apachepulsar", "description": "test", "email": "username@test.org"}'
```

## Use Cases

### Initial Deployment
```bash
# Part of TrustGraph deployment sequence
deploy_trustgraph() {
  echo "Deploying TrustGraph..."
  
  # Start services
  docker-compose up -d pulsar pulsar-manager
  
  # Wait for services
  wait_for_service "http://localhost:7750/pulsar-manager/" "Pulsar Manager"
  wait_for_service "http://localhost:8080/admin/v2/clusters" "Pulsar"
  
  # Initialize Pulsar Manager
  echo "Initializing Pulsar Manager..."
  tg-init-pulsar-manager
  
  # Initialize TrustGraph
  echo "Initializing TrustGraph..."
  tg-init-trustgraph
  
  echo "Deployment complete!"
}
```

### Development Environment Setup
```bash
# Development setup script
setup_dev_environment() {
  echo "Setting up development environment..."
  
  # Start local services
  docker-compose -f docker-compose.dev.yml up -d
  
  # Wait for readiness
  echo "Waiting for services to start..."
  sleep 30
  
  # Initialize components
  tg-init-pulsar-manager
  tg-init-trustgraph
  
  echo "Development environment ready!"
  echo "Pulsar Manager: http://localhost:7750/pulsar-manager/"
  echo "Credentials: admin / apachepulsar"
}
```

### CI/CD Integration
```bash
# Integration testing setup
setup_test_environment() {
  local timeout=300  # 5 minutes
  local elapsed=0
  
  echo "Setting up test environment..."
  
  # Start services
  docker-compose up -d --wait
  
  # Wait for Pulsar Manager
  while ! curl -s http://localhost:7750/pulsar-manager/ > /dev/null; do
    if [ $elapsed -ge $timeout ]; then
      echo "Timeout waiting for Pulsar Manager"
      return 1
    fi
    sleep 5
    elapsed=$((elapsed + 5))
  done
  
  # Initialize
  if tg-init-pulsar-manager; then
    echo "✓ Test environment ready"
  else
    echo "✗ Failed to initialize test environment"
    return 1
  fi
}
```

## Docker Integration

### Docker Compose Setup
```yaml
# docker-compose.yml
version: '3.8'

services:
  pulsar:
    image: apachepulsar/pulsar:latest
    ports:
      - "6650:6650"
      - "8080:8080"
    command: bin/pulsar standalone
    
  pulsar-manager:
    image: apachepulsar/pulsar-manager:latest
    ports:
      - "7750:7750"
    depends_on:
      - pulsar
    environment:
      SPRING_CONFIGURATION_FILE: /pulsar-manager/pulsar-manager/application.properties

  trustgraph-init:
    image: trustgraph/cli:latest
    depends_on:
      - pulsar-manager
    command: >
      sh -c "
        sleep 30 &&
        tg-init-pulsar-manager &&
        tg-init-trustgraph
      "
```

### Kubernetes Setup
```yaml
# k8s-init-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: trustgraph-init
spec:
  template:
    spec:
      containers:
      - name: init
        image: trustgraph/cli:latest
        command:
        - sh
        - -c
        - |
          echo "Waiting for Pulsar Manager..."
          while ! curl -s http://pulsar-manager:7750/pulsar-manager/; do
            sleep 5
          done
          
          echo "Initializing Pulsar Manager..."
          tg-init-pulsar-manager
          
          echo "Initializing TrustGraph..."
          tg-init-trustgraph
        env:
        - name: PULSAR_MANAGER_URL
          value: "http://pulsar-manager:7750"
      restartPolicy: Never
```

## Error Handling

### Connection Refused
```bash
curl: (7) Failed to connect to localhost port 7750: Connection refused
```
**Solution**: Ensure Pulsar Manager is running and accessible on port 7750.

### CSRF Token Issues
```bash
curl: (22) The requested URL returned error: 403 Forbidden
```
**Solution**: The CSRF token mechanism may have changed. Check Pulsar Manager API documentation.

### User Already Exists
```bash
HTTP 409 Conflict - User already exists
```
**Solution**: This is expected on subsequent runs. The superuser is already created.

### Network Issues
```bash
curl: (28) Operation timed out
```
**Solution**: Check network connectivity and firewall settings.

## Security Considerations

### Default Credentials
The command uses default credentials that should be changed in production:

```bash
# After initialization, change the password via Pulsar Manager UI
# Or use the API to update credentials
change_admin_password() {
  local new_password="$1"
  
  # Login to get session
  session=$(curl -s -c cookies.txt \
    -d "username=admin&password=apachepulsar" \
    http://localhost:7750/pulsar-manager/login)
  
  # Update password
  curl -s -b cookies.txt \
    -H "Content-Type: application/json" \
    -X PUT \
    -d "{\"password\": \"$new_password\"}" \
    http://localhost:7750/pulsar-manager/users/admin
  
  rm cookies.txt
}
```

### Access Control
```bash
# Restrict access to Pulsar Manager in production
configure_security() {
  echo "Configuring Pulsar Manager security..."
  
  # Change default password
  change_admin_password "$(openssl rand -base64 32)"
  
  # Configure firewall rules (example)
  # iptables -A INPUT -p tcp --dport 7750 -s 10.0.0.0/8 -j ACCEPT
  # iptables -A INPUT -p tcp --dport 7750 -j DROP
  
  echo "Security configuration complete"
}
```

## Advanced Usage

### Custom Configuration
```bash
# Create custom initialization script
create_custom_init() {
  cat > custom-pulsar-manager-init.sh << 'EOF'
#!/bin/bash

PULSAR_MANAGER_URL=${PULSAR_MANAGER_URL:-http://localhost:7750}
ADMIN_USER=${ADMIN_USER:-admin}
ADMIN_PASS=${ADMIN_PASS:-$(openssl rand -base64 16)}
ADMIN_EMAIL=${ADMIN_EMAIL:-admin@example.com}

echo "Initializing Pulsar Manager at: $PULSAR_MANAGER_URL"

# Get CSRF token
CSRF_TOKEN=$(curl -s "$PULSAR_MANAGER_URL/pulsar-manager/csrf-token")

if [ -z "$CSRF_TOKEN" ]; then
  echo "Failed to get CSRF token"
  exit 1
fi

# Create superuser
response=$(curl -s -w "%{http_code}" \
  -H "X-XSRF-TOKEN: $CSRF_TOKEN" \
  -H "Cookie: XSRF-TOKEN=$CSRF_TOKEN;" \
  -H 'Content-Type: application/json' \
  -X PUT \
  "$PULSAR_MANAGER_URL/pulsar-manager/users/superuser" \
  -d "{\"name\": \"$ADMIN_USER\", \"password\": \"$ADMIN_PASS\", \"description\": \"Admin user\", \"email\": \"$ADMIN_EMAIL\"}")

http_code="${response: -3}"

if [ "$http_code" = "200" ] || [ "$http_code" = "409" ]; then
  echo "Pulsar Manager initialized successfully"
  echo "Username: $ADMIN_USER"
  echo "Password: $ADMIN_PASS"
else
  echo "Failed to initialize Pulsar Manager (HTTP $http_code)"
  exit 1
fi
EOF

  chmod +x custom-pulsar-manager-init.sh
}
```

### Health Checks
```bash
# Health check script
check_pulsar_manager() {
  local max_attempts=30
  local attempt=1
  
  echo "Checking Pulsar Manager health..."
  
  while [ $attempt -le $max_attempts ]; do
    if curl -s http://localhost:7750/pulsar-manager/ > /dev/null; then
      echo "✓ Pulsar Manager is healthy"
      return 0
    fi
    
    echo "Attempt $attempt/$max_attempts - Pulsar Manager not ready"
    sleep 5
    attempt=$((attempt + 1))
  done
  
  echo "✗ Pulsar Manager health check failed"
  return 1
}

# Use in deployment scripts
if check_pulsar_manager; then
  tg-init-pulsar-manager
else
  echo "Cannot initialize Pulsar Manager - service not healthy"
  exit 1
fi
```

## Related Commands

- [`tg-init-trustgraph`](tg-init-trustgraph.md) - Initialize TrustGraph with Pulsar configuration
- [`tg-show-config`](tg-show-config.md) - Display current TrustGraph configuration

## Integration Points

### Pulsar Manager UI
After initialization, access the web interface at:
- **URL**: `http://localhost:7750/pulsar-manager/`
- **Username**: `admin`
- **Password**: `apachepulsar`

### TrustGraph Integration
This command is typically run before `tg-init-trustgraph` as part of the complete TrustGraph setup process.

## Best Practices

1. **Run Once**: Only run during initial setup - subsequent runs are harmless but unnecessary
2. **Change Defaults**: Change default credentials in production environments
3. **Network Security**: Restrict access to Pulsar Manager in production
4. **Health Checks**: Always verify Pulsar Manager is running before initialization
5. **Automation**: Include in deployment automation scripts
6. **Documentation**: Document custom credentials for operations teams

## Troubleshooting

### Service Not Ready
```bash
# Check if Pulsar Manager is running
docker ps | grep pulsar-manager
netstat -tlnp | grep 7750
```

### Port Conflicts
```bash
# Check if port 7750 is in use
lsof -i :7750
```

### Docker Issues
```bash
# Check Pulsar Manager logs
docker logs pulsar-manager

# Restart if needed
docker restart pulsar-manager
```