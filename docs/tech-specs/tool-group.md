# TrustGraph Tool Group System
## Technical Specification v1.0

### Executive Summary

This specification defines a tool grouping system for TrustGraph agents that allows fine-grained control over which tools are available for specific requests. The system introduces group-based tool filtering through configuration and request-level specification, enabling better security boundaries, resource management, and functional partitioning of agent capabilities.

### 1. Overview

#### 1.1 Problem Statement

Currently, TrustGraph agents have access to all configured tools regardless of request context or security requirements. This creates several challenges:

- **Security Risk**: Sensitive tools (e.g., data modification) are available even for read-only queries
- **Resource Waste**: Complex tools are loaded even when simple queries don't require them  
- **Functional Confusion**: Agents may select inappropriate tools when simpler alternatives exist
- **Multi-tenant Isolation**: Different user groups need access to different tool sets

#### 1.2 Solution Overview

The tool group system introduces:

1. **Group Classification**: Tools are tagged with group memberships during configuration
2. **Request-level Filtering**: AgentRequest specifies which tool groups are permitted
3. **Runtime Enforcement**: Agents only have access to tools matching the requested groups
4. **Flexible Grouping**: Tools can belong to multiple groups for complex scenarios

### 2. Schema Changes

#### 2.1 Tool Configuration Schema Enhancement

The existing tool configuration is enhanced with a `group` field:

**Before:**
```json
{
  "name": "knowledge-query",
  "type": "knowledge-query", 
  "description": "Query the knowledge graph"
}
```

**After:**
```json
{
  "name": "knowledge-query",
  "type": "knowledge-query",
  "description": "Query the knowledge graph",
  "group": ["read-only", "knowledge", "basic"]
}
```

**Group Field Specification:**
- `group`: Array(String) - List of groups this tool belongs to
- **Optional**: Tools without group field belong to "default" group
- **Multi-membership**: Tools can belong to multiple groups
- **Case-sensitive**: Group names are exact string matches

#### 2.2 AgentRequest Schema Enhancement

The `AgentRequest` schema in `trustgraph-base/trustgraph/schema/services/agent.py` is enhanced:

**Current AgentRequest:**
- `question`: String - User query
- `plan`: String - Execution plan  
- `state`: String - Agent state
- `history`: Array(AgentStep) - Execution history

**Enhanced AgentRequest:**
- `question`: String - User query
- `plan`: String - Execution plan
- `state`: String - Agent state  
- `history`: Array(AgentStep) - Execution history
- `group`: Array(String) - **NEW** - Tool groups allowed for this request

**Group Field Behavior:**
- **Optional**: If not specified, defaults to ["default"]
- **Intersection**: Only tools matching at least one specified group are available
- **Empty array**: No tools available (agent can only use internal reasoning)
- **Wildcard**: Special group "*" grants access to all tools

### 3. Tool Group Categories

#### 3.1 Predefined Group Categories

**Security-Based Groups:**
- `read-only`: Tools that only read data (GraphQuery, KnowledgeQuery)
- `write`: Tools that modify data (GraphUpdate, DocumentStore)
- `admin`: Administrative tools (SystemConfig, UserManagement)

**Functional Groups:**
- `knowledge`: Knowledge graph operations
- `text`: Text processing and completion
- `search`: Search and retrieval operations
- `compute`: Computation and analysis tools

**Complexity Groups:**
- `basic`: Simple, fast tools for common operations
- `advanced`: Complex tools for specialized tasks  
- `experimental`: Beta/experimental tools

**Resource Groups:**
- `local`: Tools that run locally
- `remote`: Tools that require external services
- `expensive`: Resource-intensive tools

#### 3.2 Custom Group Examples

Organizations can define domain-specific groups:

```json
{
  "financial-tools": ["stock-query", "portfolio-analysis"],
  "medical-tools": ["diagnosis-assist", "drug-interaction"],
  "legal-tools": ["contract-analysis", "case-search"]
}
```

### 4. Implementation Details

#### 4.1 Tool Loading and Filtering

**Configuration Phase:**
1. All tools are loaded from configuration with their group assignments
2. Tools without explicit groups are assigned to "default" group
3. Group membership is validated and stored in tool registry

**Request Processing Phase:**
1. AgentRequest arrives with optional group specification
2. Agent filters available tools based on group intersection
3. Only matching tools are passed to agent execution context
4. Agent operates with filtered tool set throughout request lifecycle

#### 4.2 Group Resolution Logic

```
For each configured tool:
  tool_groups = tool.group || ["default"]
  
For each request:
  requested_groups = request.group || ["default"]
  
Tool is available if:
  intersection(tool_groups, requested_groups) is not empty
  OR
  "*" in requested_groups
```

#### 4.3 Agent Integration Points

**ReAct Agent:**
- Tool filtering occurs in agent_manager.py during tool registry creation
- Available tools list is pre-filtered before plan generation
- No changes to execution logic required

**Confidence-Based Agent:**
- Tool filtering occurs in planner.py during plan generation
- ExecutionStep validation ensures only available tools are used
- Flow controller enforces tool availability at runtime

### 5. Configuration Examples

#### 5.1 Tool Configuration with Groups

```yaml
tool:
  knowledge-query:
    type: knowledge-query
    name: "Knowledge Graph Query"
    description: "Query the knowledge graph for entities and relationships"
    group: ["read-only", "knowledge", "basic"]
    
  graph-update:
    type: graph-update
    name: "Graph Update"
    description: "Add or modify entities in the knowledge graph"
    group: ["write", "knowledge", "admin"]
    
  text-completion:
    type: text-completion
    name: "Text Completion"
    description: "Generate text using language models"
    group: ["read-only", "text", "basic"]
    
  complex-analysis:
    type: mcp-tool
    name: "Complex Analysis Tool"
    description: "Perform complex data analysis"
    group: ["advanced", "compute", "expensive"]
    mcp_tool_id: "analysis-server"
```

#### 5.2 Request Examples

**Read-only Knowledge Query:**
```json
{
  "question": "What entities are connected to Company X?",
  "group": ["read-only", "knowledge"]
}
```
*Available tools: knowledge-query only*

**Administrative Task:**
```json
{
  "question": "Update the company profile and analyze impact",
  "group": ["write", "knowledge", "compute"]
}
```
*Available tools: graph-update, complex-analysis*

**Unrestricted Access:**
```json
{
  "question": "Perform comprehensive analysis",
  "group": ["*"]
}
```
*Available tools: All configured tools*

**Basic Operations Only:**
```json
{
  "question": "Simple information lookup",
  "group": ["basic"]
}
```
*Available tools: knowledge-query, text-completion*

### 6. Security Considerations

#### 6.1 Access Control Integration

**Gateway-Level Filtering:**
- Gateway can enforce group restrictions based on user permissions
- Prevent elevation of privileges through request manipulation
- Audit trail includes requested and granted tool groups

**Example Gateway Logic:**
```
user_permissions = get_user_permissions(request.user_id)
allowed_groups = user_permissions.tool_groups
requested_groups = request.group

# Validate request doesn't exceed permissions
if not is_subset(requested_groups, allowed_groups):
    reject_request("Insufficient permissions for requested tool groups")
```

#### 6.2 Audit and Monitoring

**Enhanced Audit Trail:**
- Log requested tool groups per request
- Track tool usage by group membership
- Monitor unauthorized group access attempts
- Alert on unusual group usage patterns

### 7. Migration Strategy

#### 7.1 Backward Compatibility

**Phase 1: Additive Changes**
- Add optional `group` field to tool configurations
- Add optional `group` field to AgentRequest schema
- Default behavior: All existing tools belong to "default" group
- Existing requests without group field use "default" group

**Existing Behavior Preserved:**
- Tools without group configuration continue to work
- Requests without group specification access all tools
- No breaking changes to existing deployments

#### 7.2 Migration Path

**Step 1: Schema Deployment**
- Deploy enhanced schemas with optional fields
- Verify existing tools and requests continue to work

**Step 2: Tool Classification**
- Gradually add group classifications to tool configurations
- Start with security-critical tools (read-only vs write)
- Expand to functional and complexity groups

**Step 3: Request Integration**
- Update client applications to specify appropriate groups
- Implement gateway-level access control
- Monitor usage patterns and refine groups

**Step 4: Enforcement**
- Gradually tighten default permissions
- Eventually require explicit group specification for new deployments

### 8. Monitoring and Observability

#### 8.1 New Metrics

**Tool Group Usage:**
- `agent_tool_group_requests_total` - Counter of requests by group
- `agent_tool_group_availability` - Gauge of tools available per group
- `agent_filtered_tools_count` - Histogram of tool count after filtering

**Security Metrics:**
- `agent_group_access_denied_total` - Counter of unauthorized group access
- `agent_privilege_escalation_attempts_total` - Counter of suspicious requests

#### 8.2 Logging Enhancements

**Request Logging:**
```json
{
  "request_id": "req-123",
  "requested_groups": ["read-only", "knowledge"],
  "available_tools": ["knowledge-query"],
  "filtered_tools": ["graph-update", "admin-tool"],
  "execution_time": "1.2s"
}
```

### 9. Testing Strategy

#### 9.1 Unit Tests

**Tool Filtering Logic:**
- Test group intersection calculations
- Verify default group assignment
- Test wildcard group behavior
- Validate empty group handling

**Configuration Validation:**
- Test tool loading with various group configurations
- Verify schema validation for invalid group specifications
- Test backward compatibility with existing configurations

#### 9.2 Integration Tests

**Agent Behavior:**
- Verify agents only see filtered tools
- Test request execution with various group combinations
- Validate error handling when no tools are available

**Security Testing:**
- Test privilege escalation prevention
- Verify audit trail accuracy
- Test gateway integration with user permissions

#### 9.3 End-to-End Scenarios

**Multi-tenant Usage:**
```
Scenario: Different users with different tool access
Given: User A has "read-only" permissions
  And: User B has "write" permissions
When: Both request knowledge operations
Then: User A gets filtered tool set
  And: User B gets full tool set
  And: All usage is properly audited
```

### 10. Performance Considerations

#### 10.1 Tool Loading Impact

**Configuration Loading:**
- Group metadata is loaded once at startup
- Minimal memory overhead per tool
- No impact on tool initialization time

**Request Processing:**
- Tool filtering occurs once per request
- O(n) complexity where n = number of configured tools
- Negligible impact for typical tool counts (< 100)

#### 10.2 Optimization Strategies

**Pre-computed Group Sets:**
- Cache tool sets by group combination
- Avoid repeated filtering for common group patterns
- Memory vs computation tradeoff

**Lazy Loading:**
- Load tool implementations only when needed
- Reduce startup time for deployments with many tools
- Dynamic tool registration based on group requirements

### 11. Future Enhancements

#### 11.1 Dynamic Group Assignment

**Context-Aware Grouping:**
- Assign tools to groups based on request context
- Time-based group availability (business hours only)
- Load-based group restrictions (expensive tools during low usage)

#### 11.2 Group Hierarchies

**Nested Group Structure:**
```json
{
  "knowledge": {
    "read": ["knowledge-query", "entity-search"],
    "write": ["graph-update", "entity-create"]
  }
}
```

#### 11.3 Tool Recommendations

**Group-Based Suggestions:**
- Suggest optimal tool groups for request types
- Learn from usage patterns to improve recommendations
- Provide fallback groups when preferred tools are unavailable

### 12. Open Questions

1. **Group Validation**: Should invalid group names in requests cause hard failures or warnings?

2. **Group Discovery**: Should the system provide an API to list available groups and their tools?

3. **Dynamic Groups**: Should groups be configurable at runtime or only at startup?

4. **Group Inheritance**: Should tools inherit groups from their parent categories or implementations?

5. **Performance Monitoring**: What additional metrics are needed to track group-based tool usage effectively?

### 13. Conclusion

The tool group system provides:

- **Security**: Fine-grained access control over agent capabilities
- **Performance**: Reduced tool loading and selection overhead
- **Flexibility**: Multi-dimensional tool classification
- **Compatibility**: Seamless integration with existing agent architectures

This system enables TrustGraph deployments to better manage tool access, improve security boundaries, and optimize resource usage while maintaining full backward compatibility with existing configurations and requests.