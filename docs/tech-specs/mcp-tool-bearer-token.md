# MCP Tool Bearer Token Authentication Specification

> **⚠️ IMPORTANT: SINGLE-TENANT ONLY**
>
> This specification describes a **basic, service-level authentication mechanism** for MCP tools. It is **NOT** a complete authentication solution and is **NOT suitable** for:
> - Multi-user environments
> - Multi-tenant deployments
> - Federated authentication
> - User context propagation
> - Per-user authorization
>
> This feature provides **one static token per MCP tool**, shared across all users and sessions. If you need per-user or per-tenant authentication, this is not the right solution.

## Overview
**Feature Name**: MCP Tool Bearer Token Authentication Support
**Author**: Claude Code Assistant
**Date**: 2025-11-11
**Status**: In Development

### Executive Summary

Enable MCP tool configurations to specify optional bearer tokens for authenticating with protected MCP servers. This allows TrustGraph to securely invoke MCP tools hosted on servers that require authentication, without modifying the agent or tool invocation interfaces.

**IMPORTANT**: This is a basic authentication mechanism designed for single-tenant, service-to-service authentication scenarios. It is **NOT** suitable for:
- Multi-user environments where different users need different credentials
- Multi-tenant deployments requiring per-tenant isolation
- Federated authentication scenarios
- User-level authentication or authorization
- Dynamic credential management or token refresh

This feature provides a static, system-wide bearer token per MCP tool configuration, shared across all users and invocations of that tool.

### Problem Statement

Currently, MCP tools can only connect to publicly accessible MCP servers. Many production MCP deployments require authentication via bearer tokens for security. Without authentication support:
- MCP tools cannot connect to secured MCP servers
- Users must either expose MCP servers publicly or implement reverse proxies
- No standardized way to pass credentials to MCP connections
- Security best practices cannot be enforced on MCP endpoints

### Goals

- [ ] Allow MCP tool configurations to specify optional `auth-token` parameter
- [ ] Update MCP tool service to use bearer tokens when connecting to MCP servers
- [ ] Update CLI tools to support setting/displaying auth tokens
- [ ] Maintain backward compatibility with unauthenticated MCP configurations
- [ ] Document security considerations for token storage

### Non-Goals
- Dynamic token refresh or OAuth flows (static tokens only)
- Encryption of stored tokens (configuration system security is out of scope)
- Alternative authentication methods (Basic auth, API keys, etc.)
- Token validation or expiration checking
- **Per-user authentication**: This feature does NOT support user-specific credentials
- **Multi-tenant isolation**: This feature does NOT provide per-tenant token management
- **Federated authentication**: This feature does NOT integrate with identity providers (SSO, OAuth, SAML, etc.)
- **Context-aware authentication**: Tokens are not passed based on user context or session

## Background and Context

### Current State
MCP tool configurations are stored in the `mcp` configuration group with this structure:
```json
{
  "remote-name": "tool_name",
  "url": "http://mcp-server:3000/api"
}
```

The MCP tool service connects to servers using `streamablehttp_client(url)` without any authentication headers.

### Limitations

**Current System Limitations:**
1. **No authentication support**: Cannot connect to secured MCP servers
2. **Security exposure**: MCP servers must be publicly accessible or use network-level security only
3. **Production deployment issues**: Cannot follow security best practices for API endpoints

**Limitations of This Solution:**
1. **Single-tenant only**: One static token per MCP tool, shared across all users
2. **No per-user credentials**: Cannot authenticate as different users or pass user context
3. **No multi-tenant support**: Cannot isolate credentials by tenant or organization
4. **Static tokens only**: No support for token refresh, rotation, or expiration handling
5. **Service-level authentication**: Authenticates the TrustGraph service, not individual users
6. **Shared security context**: All invocations of an MCP tool use the same credential

### Use Case Applicability

**✅ Appropriate Use Cases:**
- Single-tenant TrustGraph deployments
- Service-to-service authentication (TrustGraph → MCP Server)
- Development and testing environments
- Internal MCP tools accessed by the TrustGraph system
- Scenarios where all users share the same MCP tool access level
- Static, long-lived service credentials

**❌ Inappropriate Use Cases:**
- Multi-user systems requiring per-user authentication
- Multi-tenant SaaS deployments with tenant isolation requirements
- Federated authentication scenarios (SSO, OAuth, SAML)
- Systems requiring user context propagation to MCP servers
- Environments needing dynamic token refresh or short-lived tokens
- Applications where different users need different permission levels
- Compliance requirements for user-level audit trails

**Example Appropriate Scenario:**
A single-organization TrustGraph deployment where all employees use the same internal MCP tool (e.g., company database lookup). The MCP server requires authentication to prevent external access, but all internal users have the same access level.

**Example Inappropriate Scenario:**
A multi-tenant TrustGraph SaaS platform where Tenant A and Tenant B each need to access their own isolated MCP servers with separate credentials. This feature does NOT support per-tenant token management.

### Related Components
- **trustgraph-flow/trustgraph/agent/mcp_tool/service.py**: MCP tool invocation service
- **trustgraph-cli/trustgraph/cli/set_mcp_tool.py**: CLI tool for creating/updating MCP configurations
- **trustgraph-cli/trustgraph/cli/show_mcp_tools.py**: CLI tool for displaying MCP configurations
- **MCP Python SDK**: `streamablehttp_client` from `mcp.client.streamable_http`

## Requirements

### Functional Requirements

1. **MCP Configuration Auth Token**: MCP tool configurations MUST support an optional `auth-token` field
2. **Bearer Token Usage**: MCP tool service MUST send `Authorization: Bearer {token}` header when auth-token is configured
3. **CLI Support**: `tg-set-mcp-tool` MUST accept optional `--auth-token` parameter
4. **Token Display**: `tg-show-mcp-tools` MUST indicate when auth-token is configured (masked for security)
5. **Backward Compatibility**: Existing MCP tool configurations without auth-token MUST continue to work

### Non-Functional Requirements
1. **Backward Compatibility**: Zero breaking changes for existing MCP tool configurations
2. **Performance**: No significant performance impact on MCP tool invocation
3. **Security**: Tokens stored in configuration (document security implications)

### User Stories

1. As a **DevOps engineer**, I want to configure bearer tokens for MCP tools so that I can secure MCP server endpoints
2. As a **CLI user**, I want to set auth tokens when creating MCP tools so that I can connect to protected servers
3. As a **system administrator**, I want to see which MCP tools have authentication configured so that I can audit security settings

## Design

### High-Level Architecture
Extend MCP tool configuration and service to support bearer token authentication:
1. Add optional `auth-token` field to MCP tool configuration schema
2. Modify MCP tool service to read auth-token and pass to HTTP client
3. Update CLI tools to support setting and displaying auth tokens
4. Document security considerations and best practices

### Configuration Schema

**Current Schema**:
```json
{
  "remote-name": "tool_name",
  "url": "http://mcp-server:3000/api"
}
```

**New Schema** (with optional auth-token):
```json
{
  "remote-name": "tool_name",
  "url": "http://mcp-server:3000/api",
  "auth-token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Field Descriptions**:
- `remote-name` (optional): Name used by MCP server (defaults to config key)
- `url` (required): MCP server endpoint URL
- `auth-token` (optional): Bearer token for authentication

### Data Flow

1. **Configuration Storage**: User runs `tg-set-mcp-tool --id my-tool --tool-url http://server/api --auth-token xyz123`
2. **Config Loading**: MCP tool service receives config update via `on_mcp_config()` callback
3. **Tool Invocation**: When tool is invoked:
   - Service reads `auth-token` from config (if present)
   - Creates headers dict: `{"Authorization": "Bearer {token}"}`
   - Passes headers to `streamablehttp_client(url, headers=headers)`
   - MCP server validates token and processes request

### API Changes
No external API changes - configuration schema extension only.

### Component Details

#### Component 1: service.py (MCP Tool Service)
**File**: `trustgraph-flow/trustgraph/agent/mcp_tool/service.py`

**Purpose**: Invoke MCP tools on remote servers

**Changes Required** (in `invoke_tool()` method):
1. Check for `auth-token` in `self.mcp_services[name]` config
2. Build headers dict with Authorization header if token exists
3. Pass headers to `streamablehttp_client(url, headers=headers)`

**Current Code** (lines 42-89):
```python
async def invoke_tool(self, name, parameters):
    try:
        if name not in self.mcp_services:
            raise RuntimeError(f"MCP service {name} not known")
        if "url" not in self.mcp_services[name]:
            raise RuntimeError(f"MCP service {name} URL not defined")

        url = self.mcp_services[name]["url"]

        if "remote-name" in self.mcp_services[name]:
            remote_name = self.mcp_services[name]["remote-name"]
        else:
            remote_name = name

        logger.info(f"Invoking {remote_name} at {url}")

        # Connect to a streamable HTTP server
        async with streamablehttp_client(url) as (
                read_stream,
                write_stream,
                _,
        ):
            # ... rest of method
```

**Modified Code**:
```python
async def invoke_tool(self, name, parameters):
    try:
        if name not in self.mcp_services:
            raise RuntimeError(f"MCP service {name} not known")
        if "url" not in self.mcp_services[name]:
            raise RuntimeError(f"MCP service {name} URL not defined")

        url = self.mcp_services[name]["url"]

        if "remote-name" in self.mcp_services[name]:
            remote_name = self.mcp_services[name]["remote-name"]
        else:
            remote_name = name

        # Build headers with optional bearer token
        headers = {}
        if "auth-token" in self.mcp_services[name]:
            token = self.mcp_services[name]["auth-token"]
            headers["Authorization"] = f"Bearer {token}"

        logger.info(f"Invoking {remote_name} at {url}")

        # Connect to a streamable HTTP server with headers
        async with streamablehttp_client(url, headers=headers) as (
                read_stream,
                write_stream,
                _,
        ):
            # ... rest of method (unchanged)
```

#### Component 2: set_mcp_tool.py (CLI Configuration Tool)
**File**: `trustgraph-cli/trustgraph/cli/set_mcp_tool.py`

**Purpose**: Create/update MCP tool configurations

**Changes Required**:
1. Add `--auth-token` optional argument to argparse
2. Include `auth-token` in configuration JSON when provided

**Current Arguments**:
- `--id` (required): MCP tool identifier
- `--remote-name` (optional): Remote MCP tool name
- `--tool-url` (required): MCP tool URL endpoint
- `-u, --api-url` (optional): TrustGraph API URL

**New Argument**:
- `--auth-token` (optional): Bearer token for authentication

**Modified Configuration Building**:
```python
# Build configuration object
config = {
    "url": args.tool_url,
}

if args.remote_name:
    config["remote-name"] = args.remote_name

if args.auth_token:
    config["auth-token"] = args.auth_token

# Store configuration
api.config().put([
    ConfigValue(type="mcp", key=args.id, value=json.dumps(config))
])
```

#### Component 3: show_mcp_tools.py (CLI Display Tool)
**File**: `trustgraph-cli/trustgraph/cli/show_mcp_tools.py`

**Purpose**: Display MCP tool configurations

**Changes Required**:
1. Add "Auth" column to output table
2. Display "Yes" or "No" based on presence of auth-token
3. Do not display actual token value (security)

**Current Output**:
```
ID          Remote Name    URL
----------  -------------  ------------------------
my-tool     my-tool        http://server:3000/api
```

**New Output**:
```
ID          Remote Name    URL                      Auth
----------  -------------  ------------------------ ------
my-tool     my-tool        http://server:3000/api   Yes
other-tool  other-tool     http://other:3000/api    No
```

#### Component 4: Documentation
**File**: `docs/cli/tg-set-mcp-tool.md`

**Changes Required**:
1. Document new `--auth-token` parameter
2. Provide example usage with authentication
3. Document security considerations

## Implementation Plan

### Phase 1: Create Technical Specification
- [x] Write comprehensive tech spec documenting all changes

### Phase 2: Update MCP Tool Service
- [ ] Modify `invoke_tool()` in `service.py` to read auth-token from config
- [ ] Build headers dict and pass to `streamablehttp_client`
- [ ] Test with authenticated MCP server

### Phase 3: Update CLI Tools
- [ ] Add `--auth-token` argument to `set_mcp_tool.py`
- [ ] Include auth-token in configuration JSON
- [ ] Add "Auth" column to `show_mcp_tools.py` output
- [ ] Test CLI tool changes

### Phase 4: Update Documentation
- [ ] Document `--auth-token` parameter in `tg-set-mcp-tool.md`
- [ ] Add security considerations section
- [ ] Provide example usage

### Phase 5: Testing
- [ ] Test MCP tool with auth-token connects successfully
- [ ] Test backward compatibility (tools without auth-token still work)
- [ ] Test CLI tools accept and store auth-token correctly
- [ ] Test show command displays auth status correctly

### Code Changes Summary
| File | Change Type | Lines | Description |
|------|------------|-------|-------------|
| `service.py` | Modified | ~52-66 | Add auth-token reading and header building |
| `set_mcp_tool.py` | Modified | ~30-60 | Add --auth-token argument and config storage |
| `show_mcp_tools.py` | Modified | ~40-70 | Add Auth column to display |
| `tg-set-mcp-tool.md` | Modified | Various | Document new parameter |

## Testing Strategy

### Unit Tests
- **Auth Token Reading**: Test `invoke_tool()` correctly reads auth-token from config
- **Header Building**: Test Authorization header is built correctly with Bearer prefix
- **Backward Compatibility**: Test tools without auth-token work unchanged
- **CLI Argument Parsing**: Test `--auth-token` argument is parsed correctly

### Integration Tests
- **Authenticated Connection**: Test MCP tool service connects to authenticated server
- **End-to-End**: Test CLI → config storage → service invocation with auth token
- **Token Not Required**: Test connection to unauthenticated server still works

### Manual Testing
- **Real MCP Server**: Test with actual MCP server requiring bearer token authentication
- **CLI Workflow**: Test complete workflow: set tool with auth → invoke tool → verify success
- **Display Masking**: Verify auth status shown but token value not exposed

## Migration and Rollout

### Migration Strategy
No migration required - this is purely additive functionality:
- Existing MCP tool configurations without `auth-token` continue to work unchanged
- New configurations can optionally include `auth-token` field
- CLI tools accept but don't require `--auth-token` parameter

### Rollout Plan
1. **Phase 1**: Deploy core service changes to development/staging
2. **Phase 2**: Deploy CLI tool updates
3. **Phase 3**: Update documentation
4. **Phase 4**: Production rollout with monitoring

### Rollback Plan
- Core changes are backward compatible - existing tools unaffected
- If issues arise, auth-token handling can be disabled by removing header building logic
- CLI changes are independent and can be rolled back separately

## Security Considerations

### ⚠️ Critical Limitation: Single-Tenant Authentication Only

**This authentication mechanism is NOT suitable for multi-user or multi-tenant environments.**

- **Shared credentials**: All users and invocations share the same token per MCP tool
- **No user context**: The MCP server cannot distinguish between different TrustGraph users
- **No tenant isolation**: All tenants share the same credential for each MCP tool
- **Audit trail limitation**: MCP server logs show all requests from the same credential
- **Permission scope**: Cannot enforce different permission levels for different users

**Do NOT use this feature if:**
- Your TrustGraph deployment serves multiple organizations (multi-tenant)
- You need to track which user accessed which MCP tool
- Different users require different permission levels
- You need to comply with user-level audit requirements
- Your MCP server enforces per-user rate limits or quotas

**Alternative solutions for multi-user/multi-tenant scenarios:**
- Implement user context propagation through custom headers
- Deploy separate TrustGraph instances per tenant
- Use network-level isolation (VPCs, service meshes)
- Implement a proxy layer that handles per-user authentication

### Token Storage
**Risk**: Auth tokens stored in plaintext in configuration system

**Mitigation**:
- Document that tokens are stored unencrypted
- Recommend using short-lived tokens when possible
- Recommend proper access control on configuration storage
- Consider future enhancement for encrypted token storage

### Token Exposure
**Risk**: Tokens could be exposed in logs or CLI output

**Mitigation**:
- Do not log token values (only log "auth configured: yes/no")
- CLI show command displays masked status only, not actual token
- Do not include tokens in error messages

### Network Security
**Risk**: Tokens transmitted over unencrypted connections

**Mitigation**:
- Document recommendation to use HTTPS URLs for MCP servers
- Warn users about plaintext transmission risk with HTTP

### Configuration Access
**Risk**: Unauthorized access to configuration system exposes tokens

**Mitigation**:
- Document importance of securing configuration system access
- Recommend principle of least privilege for configuration access
- Consider audit logging for configuration changes (future enhancement)

### Multi-User Environments
**Risk**: In multi-user deployments, all users share the same MCP credentials

**Understanding the Risk**:
- User A and User B both use the same token when accessing an MCP tool
- MCP server cannot distinguish between different TrustGraph users
- No way to enforce per-user permissions or rate limits
- Audit logs on MCP server show all requests from same credential
- If one user's session is compromised, attacker has same MCP access as all users

**This is NOT a bug - it's a fundamental limitation of this design.**

## Performance Impact
- **Minimal overhead**: Header building adds negligible processing time
- **Network impact**: Additional HTTP header adds ~50-200 bytes per request
- **Memory usage**: Negligible increase for storing token string in config

## Documentation

### User Documentation
- [ ] Update `tg-set-mcp-tool.md` with `--auth-token` parameter
- [ ] Add security considerations section
- [ ] Provide example usage with bearer token
- [ ] Document token storage implications

### Developer Documentation
- [ ] Add inline comments for auth token handling in `service.py`
- [ ] Document header building logic
- [ ] Update MCP tool configuration schema documentation

## Open Questions
1. **Token encryption**: Should we implement encrypted token storage in configuration system?
2. **Token refresh**: Future support for OAuth refresh flows or token rotation?
3. **Alternative auth methods**: Should we support Basic auth, API keys, or other methods?

## Alternatives Considered

1. **Environment variables for tokens**: Store tokens in env vars instead of config
   - **Rejected**: Complicates deployment and configuration management

2. **Separate secrets store**: Use dedicated secrets management system
   - **Deferred**: Out of scope for initial implementation, consider future enhancement

3. **Multiple auth methods**: Support Basic, API key, OAuth, etc.
   - **Rejected**: Bearer tokens cover most use cases, keep initial implementation simple

4. **Encrypted token storage**: Encrypt tokens in configuration system
   - **Deferred**: Configuration system security is broader concern, defer to future work

5. **Per-invocation tokens**: Allow tokens to be passed at invocation time
   - **Rejected**: Violates separation of concerns, agent shouldn't handle credentials

## References
- [MCP Protocol Specification](https://github.com/modelcontextprotocol/spec)
- [HTTP Bearer Authentication (RFC 6750)](https://tools.ietf.org/html/rfc6750)
- [Current MCP Tool Service](../trustgraph-flow/trustgraph/agent/mcp_tool/service.py)
- [MCP Tool Arguments Specification](./mcp-tool-arguments.md)

## Appendix

### Example Usage

**Setting MCP tool with authentication**:
```bash
tg-set-mcp-tool \
  --id secure-tool \
  --tool-url https://secure-server.example.com/mcp \
  --auth-token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Showing MCP tools**:
```bash
tg-show-mcp-tools

ID            Remote Name   URL                                    Auth
-----------   -----------   ------------------------------------   ------
secure-tool   secure-tool   https://secure-server.example.com/mcp  Yes
public-tool   public-tool   http://localhost:3000/mcp              No
```

### Configuration Example

**Stored in configuration system**:
```json
{
  "type": "mcp",
  "key": "secure-tool",
  "value": "{\"url\": \"https://secure-server.example.com/mcp\", \"auth-token\": \"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...\"}"
}
```

### Security Best Practices

1. **Use HTTPS**: Always use HTTPS URLs for MCP servers with authentication
2. **Short-lived tokens**: Use tokens with expiration when possible
3. **Least privilege**: Grant tokens minimum required permissions
4. **Access control**: Restrict access to configuration system
5. **Token rotation**: Rotate tokens regularly
6. **Audit logging**: Monitor configuration changes for security events
