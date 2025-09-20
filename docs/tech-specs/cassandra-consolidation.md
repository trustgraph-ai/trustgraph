# Tech Spec: Cassandra Configuration Consolidation

**Status:** Draft  
**Author:** Assistant  
**Date:** 2024-09-03  

## Overview

This specification addresses the inconsistent naming and configuration patterns for Cassandra connection parameters across the TrustGraph codebase. Currently, two different parameter naming schemes exist (`cassandra_*` vs `graph_*`), leading to confusion and maintenance complexity.

## Problem Statement

The codebase currently uses two distinct sets of Cassandra configuration parameters:

1. **Knowledge/Config/Library modules** use:
   - `cassandra_host` (list of hosts)
   - `cassandra_user` 
   - `cassandra_password`

2. **Graph/Storage modules** use:
   - `graph_host` (single host, sometimes converted to list)
   - `graph_username`
   - `graph_password`

3. **Inconsistent command-line exposure**:
   - Some processors (e.g., `kg-store`) don't expose Cassandra settings as command-line arguments
   - Other processors expose them with different names and formats
   - Help text doesn't reflect environment variable defaults

Both parameter sets connect to the same Cassandra cluster but with different naming conventions, causing:
- Configuration confusion for users
- Increased maintenance burden
- Inconsistent documentation
- Potential for misconfiguration
- Inability to override settings via command-line in some processors

## Proposed Solution

### 1. Standardize Parameter Names

All modules will use consistent `cassandra_*` parameter names:
- `cassandra_host` - List of hosts (internally stored as list)
- `cassandra_username` - Username for authentication  
- `cassandra_password` - Password for authentication

### 2. Command-Line Arguments

All processors MUST expose Cassandra configuration via command-line arguments:
- `--cassandra-host` - Comma-separated list of hosts
- `--cassandra-username` - Username for authentication
- `--cassandra-password` - Password for authentication

### 3. Environment Variable Fallback

If command-line parameters are not explicitly provided, the system will check environment variables:
- `CASSANDRA_HOST` - Comma-separated list of hosts
- `CASSANDRA_USERNAME` - Username for authentication
- `CASSANDRA_PASSWORD` - Password for authentication

### 4. Default Values

If neither command-line parameters nor environment variables are specified:
- `cassandra_host` defaults to `["cassandra"]`
- `cassandra_username` defaults to `None` (no authentication)
- `cassandra_password` defaults to `None` (no authentication)

### 5. Help Text Requirements

The `--help` output must:
- Show environment variable values as defaults when set
- Never display password values (show `****` or `<set>` instead)
- Clearly indicate the resolution order in help text

Example help output:
```
--cassandra-host HOST
    Cassandra host list, comma-separated (default: prod-cluster-1,prod-cluster-2)
    [from CASSANDRA_HOST environment variable]

--cassandra-username USERNAME
    Cassandra username (default: cassandra_user)
    [from CASSANDRA_USERNAME environment variable]
    
--cassandra-password PASSWORD  
    Cassandra password (default: <set from environment>)
```

## Implementation Details

### Parameter Resolution Order

For each Cassandra parameter, the resolution order will be:
1. Command-line argument value
2. Environment variable (`CASSANDRA_*`)
3. Default value

### Host Parameter Handling

The `cassandra_host` parameter:
- Command-line accepts comma-separated string: `--cassandra-host "host1,host2,host3"`
- Environment variable accepts comma-separated string: `CASSANDRA_HOST="host1,host2,host3"`
- Internally always stored as list: `["host1", "host2", "host3"]`
- Single host: `"localhost"` → converted to `["localhost"]`
- Already a list: `["host1", "host2"]` → used as-is

### Authentication Logic

Authentication will be used when both `cassandra_username` and `cassandra_password` are provided:
```python
if cassandra_username and cassandra_password:
    # Use SSL context and PlainTextAuthProvider
else:
    # Connect without authentication
```

## Files to Modify

### Modules using `graph_*` parameters (to be changed):
- `trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`
- `trustgraph-flow/trustgraph/storage/objects/cassandra/write.py`
- `trustgraph-flow/trustgraph/storage/rows/cassandra/write.py`
- `trustgraph-flow/trustgraph/query/triples/cassandra/service.py`

### Modules using `cassandra_*` parameters (to be updated with env fallback):
- `trustgraph-flow/trustgraph/tables/config.py`
- `trustgraph-flow/trustgraph/tables/knowledge.py`
- `trustgraph-flow/trustgraph/tables/library.py`
- `trustgraph-flow/trustgraph/storage/knowledge/store.py`
- `trustgraph-flow/trustgraph/cores/knowledge.py`
- `trustgraph-flow/trustgraph/librarian/librarian.py`
- `trustgraph-flow/trustgraph/librarian/service.py`
- `trustgraph-flow/trustgraph/config/service/service.py`
- `trustgraph-flow/trustgraph/cores/service.py`

### Test Files to Update:
- `tests/unit/test_cores/test_knowledge_manager.py`
- `tests/unit/test_storage/test_triples_cassandra_storage.py`
- `tests/unit/test_query/test_triples_cassandra_query.py`
- `tests/integration/test_objects_cassandra_integration.py`

## Implementation Strategy

### Phase 1: Create Common Configuration Helper
Create utility functions to standardize Cassandra configuration across all processors:

```python
import os
import argparse

def get_cassandra_defaults():
    """Get default values from environment variables or fallback."""
    return {
        'host': os.getenv('CASSANDRA_HOST', 'cassandra'),
        'username': os.getenv('CASSANDRA_USERNAME'),
        'password': os.getenv('CASSANDRA_PASSWORD')
    }

def add_cassandra_args(parser: argparse.ArgumentParser):
    """
    Add standardized Cassandra arguments to an argument parser.
    Shows environment variable values in help text.
    """
    defaults = get_cassandra_defaults()
    
    # Format help text with env var indication
    host_help = f"Cassandra host list, comma-separated (default: {defaults['host']})"
    if 'CASSANDRA_HOST' in os.environ:
        host_help += " [from CASSANDRA_HOST]"
    
    username_help = f"Cassandra username"
    if defaults['username']:
        username_help += f" (default: {defaults['username']})"
        if 'CASSANDRA_USERNAME' in os.environ:
            username_help += " [from CASSANDRA_USERNAME]"
    
    password_help = "Cassandra password"
    if defaults['password']:
        password_help += " (default: <set>)"
        if 'CASSANDRA_PASSWORD' in os.environ:
            password_help += " [from CASSANDRA_PASSWORD]"
    
    parser.add_argument(
        '--cassandra-host',
        default=defaults['host'],
        help=host_help
    )
    
    parser.add_argument(
        '--cassandra-username',
        default=defaults['username'],
        help=username_help
    )
    
    parser.add_argument(
        '--cassandra-password',
        default=defaults['password'],
        help=password_help
    )

def resolve_cassandra_config(args) -> tuple[list[str], str|None, str|None]:
    """
    Convert argparse args to Cassandra configuration.
    
    Returns:
        tuple: (hosts_list, username, password)
    """
    # Convert host string to list
    if isinstance(args.cassandra_host, str):
        hosts = [h.strip() for h in args.cassandra_host.split(',')]
    else:
        hosts = args.cassandra_host
    
    return hosts, args.cassandra_username, args.cassandra_password
```

### Phase 2: Update Modules Using `graph_*` Parameters
1. Change parameter names from `graph_*` to `cassandra_*`
2. Replace custom `add_args()` methods with standardized `add_cassandra_args()`
3. Use the common configuration helper functions
4. Update documentation strings

Example transformation:
```python
# OLD CODE
@staticmethod
def add_args(parser):
    parser.add_argument(
        '-g', '--graph-host',
        default="localhost",
        help=f'Graph host (default: localhost)'
    )
    parser.add_argument(
        '--graph-username',
        default=None,
        help=f'Cassandra username'
    )

# NEW CODE  
@staticmethod
def add_args(parser):
    FlowProcessor.add_args(parser)
    add_cassandra_args(parser)  # Use standard helper
```

### Phase 3: Update Modules Using `cassandra_*` Parameters  
1. Add command-line argument support where missing (e.g., `kg-store`)
2. Replace existing argument definitions with `add_cassandra_args()`
3. Use `resolve_cassandra_config()` for consistent resolution
4. Ensure consistent host list handling

### Phase 4: Update Tests and Documentation
1. Update all test files to use new parameter names
2. Update CLI documentation
3. Update API documentation
4. Add environment variable documentation

## Backward Compatibility

To maintain backward compatibility during transition:

1. **Deprecation warnings** for `graph_*` parameters
2. **Parameter aliasing** - accept both old and new names initially
3. **Phased rollout** over multiple releases
4. **Documentation updates** with migration guide

Example backward compatibility code:
```python
def __init__(self, **params):
    # Handle deprecated graph_* parameters
    if 'graph_host' in params:
        warnings.warn("graph_host is deprecated, use cassandra_host", DeprecationWarning)
        params.setdefault('cassandra_host', params.pop('graph_host'))
    
    if 'graph_username' in params:
        warnings.warn("graph_username is deprecated, use cassandra_username", DeprecationWarning)
        params.setdefault('cassandra_username', params.pop('graph_username'))
    
    # ... continue with standard resolution
```

## Testing Strategy

1. **Unit tests** for configuration resolution logic
2. **Integration tests** with various configuration combinations
3. **Environment variable tests** 
4. **Backward compatibility tests** with deprecated parameters
5. **Docker compose tests** with environment variables

## Documentation Updates

1. Update all CLI command documentation
2. Update API documentation
3. Create migration guide
4. Update Docker compose examples
5. Update configuration reference documentation

## Risks and Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking changes for users | High | Implement backward compatibility period |
| Configuration confusion during transition | Medium | Clear documentation and deprecation warnings |
| Test failures | Medium | Comprehensive test updates |
| Docker deployment issues | High | Update all Docker compose examples |

## Success Criteria

- [ ] All modules use consistent `cassandra_*` parameter names
- [ ] All processors expose Cassandra settings via command-line arguments
- [ ] Command-line help text shows environment variable defaults
- [ ] Password values are never displayed in help text
- [ ] Environment variable fallback works correctly
- [ ] `cassandra_host` is consistently handled as a list internally
- [ ] Backward compatibility maintained for at least 2 releases
- [ ] All tests pass with new configuration system
- [ ] Documentation fully updated
- [ ] Docker compose examples work with environment variables

## Timeline

- **Week 1:** Implement common configuration helper and update `graph_*` modules
- **Week 2:** Add environment variable support to existing `cassandra_*` modules  
- **Week 3:** Update tests and documentation
- **Week 4:** Integration testing and bug fixes

## Future Considerations

- Consider extending this pattern to other database configurations (e.g., Elasticsearch)
- Implement configuration validation and better error messages
- Add support for Cassandra connection pooling configuration
- Consider adding configuration file support (.env files)