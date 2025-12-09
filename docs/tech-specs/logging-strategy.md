# TrustGraph Logging Strategy

## Overview

TrustGraph uses Python's built-in `logging` module for all logging operations, with centralized configuration and optional Loki integration for log aggregation. This provides a standardized, flexible approach to logging across all components of the system.

## Default Configuration

### Logging Level
- **Default Level**: `INFO`
- **Configurable via**: `--log-level` command-line argument
- **Choices**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

### Output Destinations
1. **Console (stdout)**: Always enabled - ensures compatibility with containerized environments
2. **Loki**: Optional centralized log aggregation (enabled by default, can be disabled)

## Centralized Logging Module

All logging configuration is managed by `trustgraph.base.logging` module, which provides:
- `add_logging_args(parser)` - Adds standard logging CLI arguments
- `setup_logging(args)` - Configures logging from parsed arguments

This module is used by all server-side components:
- AsyncProcessor-based services
- API Gateway
- MCP Server

## Implementation Guidelines

### 1. Logger Initialization

Each module should create its own logger using the module's `__name__`:

```python
import logging

logger = logging.getLogger(__name__)
```

The logger name is automatically used as a label in Loki for filtering and searching.

### 2. Service Initialization

All server-side services automatically get logging configuration through the centralized module:

```python
from trustgraph.base import add_logging_args, setup_logging
import argparse

def main():
    parser = argparse.ArgumentParser()

    # Add standard logging arguments (includes Loki configuration)
    add_logging_args(parser)

    # Add your service-specific arguments
    parser.add_argument('--port', type=int, default=8080)

    args = parser.parse_args()
    args = vars(args)

    # Setup logging early in startup
    setup_logging(args)

    # Rest of your service initialization
    logger = logging.getLogger(__name__)
    logger.info("Service starting...")
```

### 3. Command-Line Arguments

All services support these logging arguments:

**Log Level:**
```bash
--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
```

**Loki Configuration:**
```bash
--loki-enabled              # Enable Loki (default)
--no-loki-enabled           # Disable Loki
--loki-url URL              # Loki push URL (default: http://loki:3100/loki/api/v1/push)
--loki-username USERNAME    # Optional authentication
--loki-password PASSWORD    # Optional authentication
```

**Examples:**
```bash
# Default - INFO level, Loki enabled
./my-service

# Debug mode, console only
./my-service --log-level DEBUG --no-loki-enabled

# Custom Loki server with auth
./my-service --loki-url http://loki.prod:3100/loki/api/v1/push \
             --loki-username admin --loki-password secret
```

### 4. Environment Variables

Loki configuration supports environment variable fallbacks:

```bash
export LOKI_URL=http://loki.prod:3100/loki/api/v1/push
export LOKI_USERNAME=admin
export LOKI_PASSWORD=secret
```

Command-line arguments take precedence over environment variables.

### 5. Logging Best Practices

#### Log Levels Usage
- **DEBUG**: Detailed information for diagnosing problems (variable values, function entry/exit)
- **INFO**: General informational messages (service started, configuration loaded, processing milestones)
- **WARNING**: Warning messages for potentially harmful situations (deprecated features, recoverable errors)
- **ERROR**: Error messages for serious problems (failed operations, exceptions)
- **CRITICAL**: Critical messages for system failures requiring immediate attention

#### Message Format
```python
# Good - includes context
logger.info(f"Processing document: {doc_id}, size: {doc_size} bytes")
logger.error(f"Failed to connect to database: {error}", exc_info=True)

# Avoid - lacks context
logger.info("Processing document")
logger.error("Connection failed")
```

#### Performance Considerations
```python
# Use lazy formatting for expensive operations
logger.debug("Expensive operation result: %s", expensive_function())

# Check log level for very expensive debug operations
if logger.isEnabledFor(logging.DEBUG):
    debug_data = compute_expensive_debug_info()
    logger.debug(f"Debug data: {debug_data}")
```

### 6. Structured Logging with Loki

For complex data, use structured logging with extra tags for Loki:

```python
logger.info("Request processed", extra={
    'tags': {
        'request_id': request_id,
        'user_id': user_id,
        'status': 'success'
    }
})
```

These tags become searchable labels in Loki, in addition to automatic labels:
- `severity` - Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `logger` - Module name (from `__name__`)

### 7. Exception Logging

Always include stack traces for exceptions:

```python
try:
    process_data()
except Exception as e:
    logger.error(f"Failed to process data: {e}", exc_info=True)
    raise
```

### 8. Async Logging Considerations

The logging system uses non-blocking queued handlers for Loki:
- Console output is synchronous (fast)
- Loki output is queued with 500-message buffer
- Background thread handles Loki transmission
- No blocking of main application code

```python
import asyncio
import logging

async def async_operation():
    logger = logging.getLogger(__name__)
    # Logging is thread-safe and won't block async operations
    logger.info(f"Starting async operation in task: {asyncio.current_task().get_name()}")
```

## Loki Integration

### Architecture

The logging system uses Python's built-in `QueueHandler` and `QueueListener` for non-blocking Loki integration:

1. **QueueHandler**: Logs are placed in a 500-message queue (non-blocking)
2. **Background Thread**: QueueListener sends logs to Loki asynchronously
3. **Graceful Degradation**: If Loki is unavailable, console logging continues

### Automatic Labels

Every log sent to Loki includes:
- `severity`: Log level (DEBUG, INFO, etc.)
- `logger`: Module name (e.g., `trustgraph.gateway.service`, `trustgraph.agent.react.service`)

### Custom Labels

Add custom labels via the `extra` parameter:

```python
logger.info("User action", extra={
    'tags': {
        'user_id': user_id,
        'action': 'document_upload',
        'collection': collection_name
    }
})
```

### Querying Logs in Loki

```logql
# All logs from a specific service
{logger="trustgraph.gateway.service"}

# Error logs from all services
{severity="ERROR"}

# Logs from a specific processor
{logger="trustgraph.agent.react.service"} |= "Processing"

# Logs with custom tags
{logger="trustgraph.gateway.service"} | json | user_id="12345"
```

### Graceful Degradation

If Loki is unavailable or `python-logging-loki` is not installed:
- Warning message printed to console
- Console logging continues normally
- Application continues running
- No retry logic for Loki connection (fail fast, degrade gracefully)

## Testing

During tests, consider using a different logging configuration:

```python
# In test setup
import logging

# Reduce noise during tests
logging.getLogger().setLevel(logging.WARNING)

# Or disable Loki for tests
setup_logging({'log_level': 'WARNING', 'loki_enabled': False})
```

## Monitoring Integration

### Standard Format
All logs use consistent format:
```
2025-01-09 10:30:45,123 - trustgraph.gateway.service - INFO - Request processed
```

Format components:
- Timestamp (ISO format with milliseconds)
- Logger name (module path)
- Log level
- Message

### Loki Queries for Monitoring

Common monitoring queries:

```logql
# Error rate by service
rate({severity="ERROR"}[5m]) by (logger)

# Top error-producing services
topk(5, count_over_time({severity="ERROR"}[1h]) by (logger))

# Recent errors
{severity="ERROR"} | line_format "{{.logger}}: {{.message}}"

# Service-specific logs
{logger=~"trustgraph.agent.*"} |= "exception"
```

## Security Considerations

- **Never log sensitive information** (passwords, API keys, personal data, tokens)
- **Sanitize user input** before logging
- **Use placeholders** for sensitive fields: `user_id=****1234`
- **Loki authentication**: Use `--loki-username` and `--loki-password` for secure deployments
- **Secure transport**: Use HTTPS for Loki URL in production: `https://loki.prod:3100/loki/api/v1/push`

## Dependencies

The centralized logging module requires:
- `python-logging-loki` - For Loki integration (optional, graceful degradation if missing)

Already included in `trustgraph-base/pyproject.toml` and `requirements.txt`.

## Migration Path

For existing code:

1. **Services already using AsyncProcessor**: No changes needed, Loki support is automatic
2. **Services not using AsyncProcessor** (api-gateway, mcp-server): Already updated
3. **CLI tools**: Out of scope - continue using print() or simple logging

### From print() to logging:
```python
# Before
print(f"Processing document {doc_id}")

# After
logger = logging.getLogger(__name__)
logger.info(f"Processing document {doc_id}")
```

## Configuration Summary

| Argument | Default | Environment Variable | Description |
|----------|---------|---------------------|-------------|
| `--log-level` | `INFO` | - | Console and Loki log level |
| `--loki-enabled` | `True` | - | Enable Loki logging |
| `--loki-url` | `http://loki:3100/loki/api/v1/push` | `LOKI_URL` | Loki push endpoint |
| `--loki-username` | `None` | `LOKI_USERNAME` | Loki auth username |
| `--loki-password` | `None` | `LOKI_PASSWORD` | Loki auth password |
