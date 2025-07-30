# TrustGraph Logging Strategy

## Overview

TrustGraph uses Python's built-in `logging` module for all logging operations. This provides a standardized, flexible approach to logging across all components of the system.

## Default Configuration

### Logging Level
- **Default Level**: `INFO`
- **Debug Mode**: `DEBUG` (enabled via command-line argument)
- **Production**: `WARNING` or `ERROR` as appropriate

### Output Destination
All logs should be written to **standard output (stdout)** to ensure compatibility with containerized environments and log aggregation systems.

## Implementation Guidelines

### 1. Logger Initialization

Each module should create its own logger using the module's `__name__`:

```python
import logging

logger = logging.getLogger(__name__)
```

### 2. Centralized Configuration

The logging configuration should be centralized in `async_processor.py` (or a dedicated logging configuration module) since it's inherited by much of the codebase:

```python
import logging
import argparse

def setup_logging(log_level='INFO'):
    """Configure logging for the entire application"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Set the logging level (default: INFO)'
    )
    return parser.parse_args()

# In main execution
if __name__ == '__main__':
    args = parse_args()
    setup_logging(args.log_level)
```

### 3. Logging Best Practices

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

### 4. Structured Logging

For complex data, use structured logging:

```python
logger.info("Request processed", extra={
    'request_id': request_id,
    'duration_ms': duration,
    'status_code': status_code,
    'user_id': user_id
})
```

### 5. Exception Logging

Always include stack traces for exceptions:

```python
try:
    process_data()
except Exception as e:
    logger.error(f"Failed to process data: {e}", exc_info=True)
    raise
```

### 6. Async Logging Considerations

For async code, ensure thread-safe logging:

```python
import asyncio
import logging

async def async_operation():
    logger = logging.getLogger(__name__)
    logger.info(f"Starting async operation in task: {asyncio.current_task().get_name()}")
```

## Environment Variables

Support environment-based configuration as a fallback:

```python
import os

log_level = os.environ.get('TRUSTGRAPH_LOG_LEVEL', 'INFO')
```

## Testing

During tests, consider using a different logging configuration:

```python
# In test setup
logging.getLogger().setLevel(logging.WARNING)  # Reduce noise during tests
```

## Monitoring Integration

Ensure log format is compatible with monitoring tools:
- Include timestamps in ISO format
- Use consistent field names
- Include correlation IDs where applicable
- Structure logs for easy parsing (JSON format for production)

## Security Considerations

- Never log sensitive information (passwords, API keys, personal data)
- Sanitize user input before logging
- Use placeholders for sensitive fields: `user_id=****1234`

## Migration Path

For existing code using print statements:
1. Replace `print()` with appropriate logger calls
2. Choose appropriate log levels based on message importance
3. Add context to make logs more useful
4. Test logging output at different levels