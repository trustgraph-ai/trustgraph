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

Both parameter sets connect to the same Cassandra cluster but with different naming conventions, causing:
- Configuration confusion for users
- Increased maintenance burden
- Inconsistent documentation
- Potential for misconfiguration

## Proposed Solution

### 1. Standardize Parameter Names

All modules will use consistent `cassandra_*` parameter names:
- `cassandra_host` - Single host string or comma-separated list
- `cassandra_username` - Username for authentication  
- `cassandra_password` - Password for authentication

### 2. Environment Variable Fallback

If parameters are not explicitly provided, the system will check environment variables:
- `CASSANDRA_HOST`
- `CASSANDRA_USERNAME` 
- `CASSANDRA_PASSWORD`

### 3. Default Values

If neither parameters nor environment variables are specified:
- `cassandra_host` defaults to `"cassandra"`
- `cassandra_username` defaults to `None` (no authentication)
- `cassandra_password` defaults to `None` (no authentication)

## Implementation Details

### Parameter Resolution Order

For each Cassandra parameter, the resolution order will be:
1. Explicitly passed parameter value
2. Environment variable (`CASSANDRA_*`)
3. Default value

### Host Parameter Handling

The `cassandra_host` parameter will accept both formats:
- Single host: `"localhost"` → converted to `["localhost"]`
- Multiple hosts: `"host1,host2,host3"` → converted to `["host1", "host2", "host3"]`
- List format: `["host1", "host2"]` → used as-is

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
Create a utility function to resolve Cassandra configuration:

```python
def resolve_cassandra_config(
    host=None, username=None, password=None
) -> tuple[list[str], str|None, str|None]:
    """
    Resolve Cassandra configuration with fallback to environment variables.
    
    Returns:
        tuple: (hosts_list, username, password)
    """
    import os
    
    # Resolve host
    resolved_host = host or os.getenv('CASSANDRA_HOST', 'cassandra')
    if isinstance(resolved_host, str):
        hosts = [h.strip() for h in resolved_host.split(',')]
    else:
        hosts = resolved_host
    
    # Resolve credentials
    resolved_username = username or os.getenv('CASSANDRA_USERNAME')
    resolved_password = password or os.getenv('CASSANDRA_PASSWORD')
    
    return hosts, resolved_username, resolved_password
```

### Phase 2: Update Modules Using `graph_*` Parameters
1. Change parameter names from `graph_*` to `cassandra_*`
2. Update argument parsing in `add_args()` methods
3. Use the common configuration helper
4. Update documentation strings

### Phase 3: Update Modules Using `cassandra_*` Parameters  
1. Add environment variable fallback using the common helper
2. Ensure consistent host list handling
3. Update tests to use new configuration resolution

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
- [ ] Environment variable fallback works correctly
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