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

#### 2.1.2 Tool State Transition Enhancement

Tools can optionally specify state transitions and state-based availability:

```json
{
  "name": "knowledge-query",
  "type": "knowledge-query",
  "description": "Query the knowledge graph",
  "group": ["read-only", "knowledge", "basic"],
  "state": "analysis",
  "available_in_states": ["undefined", "research"]
}
```

**State Field Specification:**
- `state`: String - **Optional** - State to transition to after successful tool execution
- `available_in_states`: Array(String) - **Optional** - States in which this tool is available
- **Default behavior**: Tools without `available_in_states` are available in all states
- **State transition**: Only occurs after successful tool execution

#### 2.2 AgentRequest Schema Enhancement

The `AgentRequest` schema in `trustgraph-base/trustgraph/schema/services/agent.py` is enhanced:

**Current AgentRequest:**
- `question`: String - User query
- `plan`: String - Execution plan (can be removed)
- `state`: String - Agent state
- `history`: Array(AgentStep) - Execution history

**Enhanced AgentRequest:**
- `question`: String - User query
- `state`: String - Agent execution state (now actively used for tool filtering)
- `history`: Array(AgentStep) - Execution history
- `group`: Array(String) - **NEW** - Tool groups allowed for this request

**Schema Changes:**
- **Removed**: `plan` field is no longer needed and can be removed (was originally intended for tool specification)
- **Added**: `group` field for tool group specification
- **Enhanced**: `state` field now controls tool availability during execution

**Field Behaviors:**

**Group Field:**
- **Optional**: If not specified, defaults to ["default"]
- **Intersection**: Only tools matching at least one specified group are available
- **Empty array**: No tools available (agent can only use internal reasoning)
- **Wildcard**: Special group "*" grants access to all tools

**State Field:**
- **Optional**: If not specified, defaults to "undefined"
- **State-based filtering**: Only tools available in current state are eligible
- **Default state**: "undefined" state allows all tools (subject to group filtering)
- **State transitions**: Tools can change state after successful execution

### 3. Custom Group Examples

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

#### 4.2 Tool Filtering Logic

**Combined Group and State Filtering:**

```
For each configured tool:
  tool_groups = tool.group || ["default"]
  tool_states = tool.available_in_states || ["*"]  // Available in all states
  
For each request:
  requested_groups = request.group || ["default"]
  current_state = request.state || "undefined"
  
Tool is available if:
  // Group filtering
  (intersection(tool_groups, requested_groups) is not empty OR "*" in requested_groups)
  AND
  // State filtering  
  (current_state in tool_states OR "*" in tool_states)
```

**State Transition Logic:**

```
After successful tool execution:
  if tool.state is defined:
    next_request.state = tool.state
  else:
    next_request.state = current_request.state  // No change
```

#### 4.3 Agent Integration Points

**ReAct Agent:**
- Tool filtering occurs in agent_manager.py during tool registry creation
- Available tools list is filtered by both group and state before plan generation
- State transitions update AgentRequest.state field after successful tool execution
- Next iteration uses updated state for tool filtering

**Confidence-Based Agent:**
- Tool filtering occurs in planner.py during plan generation
- ExecutionStep validation ensures only group+state eligible tools are used
- Flow controller enforces tool availability at runtime
- State transitions managed by Flow Controller between steps

### 5. Configuration Examples

#### 5.1 Tool Configuration with Groups and States

```yaml
tool:
  knowledge-query:
    type: knowledge-query
    name: "Knowledge Graph Query"
    description: "Query the knowledge graph for entities and relationships"
    group: ["read-only", "knowledge", "basic"]
    state: "analysis"
    available_in_states: ["undefined", "research"]
    
  graph-update:
    type: graph-update
    name: "Graph Update"
    description: "Add or modify entities in the knowledge graph"
    group: ["write", "knowledge", "admin"]
    available_in_states: ["analysis", "modification"]
    
  text-completion:
    type: text-completion
    name: "Text Completion"
    description: "Generate text using language models"
    group: ["read-only", "text", "basic"]
    state: "undefined"
    # No available_in_states = available in all states
    
  complex-analysis:
    type: mcp-tool
    name: "Complex Analysis Tool"
    description: "Perform complex data analysis"
    group: ["advanced", "compute", "expensive"]
    state: "results"
    available_in_states: ["analysis"]
    mcp_tool_id: "analysis-server"
    
  reset-workflow:
    type: mcp-tool
    name: "Reset Workflow"
    description: "Reset to initial state"
    group: ["admin"]
    state: "undefined"
    available_in_states: ["analysis", "results"]
```

#### 5.2 Request Examples with State Workflows

**Initial Research Request:**
```json
{
  "question": "What entities are connected to Company X?",
  "group": ["read-only", "knowledge"],
  "state": "undefined"
}
```
*Available tools: knowledge-query, text-completion*
*After knowledge-query: state → "analysis"*

**Analysis Phase:**
```json
{
  "question": "Continue analysis based on previous results",
  "group": ["advanced", "compute", "write"],
  "state": "analysis"
}
```
*Available tools: complex-analysis, graph-update, reset-workflow*
*After complex-analysis: state → "results"*

**Results Phase:**
```json
{
  "question": "What should I do with these results?",
  "group": ["admin"],
  "state": "results"
}
```
*Available tools: reset-workflow only*
*After reset-workflow: state → "undefined"*

**Workflow Example - Complete Flow:**
1. **Start (undefined)**: Use knowledge-query → transitions to "analysis"
2. **Analysis state**: Use complex-analysis → transitions to "results" 
3. **Results state**: Use reset-workflow → transitions back to "undefined"
4. **Back to start**: All initial tools available again

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
- Log requested tool groups and initial state per request
- Track state transitions and tool usage by group membership
- Monitor unauthorized group access attempts and invalid state transitions
- Alert on unusual group usage patterns or suspicious state workflows

### 7. Migration Strategy

#### 7.1 Backward Compatibility

**Phase 1: Additive Changes**
- Add optional `group` field to tool configurations
- Add optional `group` field to AgentRequest schema
- Default behavior: All existing tools belong to "default" group
- Existing requests without group field use "default" group

**Existing Behavior Preserved:**
- Tools without group configuration continue to work (default group)
- Tools without state configuration are available in all states
- Requests without group specification access all tools (default group)
- Requests without state specification use "undefined" state (all tools available)
- No breaking changes to existing deployments

### 8. Monitoring and Observability

#### 8.1 New Metrics

**Tool Group Usage:**
- `agent_tool_group_requests_total` - Counter of requests by group
- `agent_tool_group_availability` - Gauge of tools available per group
- `agent_filtered_tools_count` - Histogram of tool count after group+state filtering

**State Workflow Metrics:**
- `agent_state_transitions_total` - Counter of state transitions by tool
- `agent_workflow_duration_seconds` - Histogram of time spent in each state
- `agent_state_availability` - Gauge of tools available per state

**Security Metrics:**
- `agent_group_access_denied_total` - Counter of unauthorized group access
- `agent_invalid_state_transition_total` - Counter of invalid state transitions
- `agent_privilege_escalation_attempts_total` - Counter of suspicious requests

#### 8.2 Logging Enhancements

**Request Logging:**
```json
{
  "request_id": "req-123",
  "requested_groups": ["read-only", "knowledge"],
  "initial_state": "undefined",
  "state_transitions": [
    {"tool": "knowledge-query", "from": "undefined", "to": "analysis", "timestamp": "2024-01-01T10:00:01Z"}
  ],
  "available_tools": ["knowledge-query", "text-completion"],
  "filtered_by_group": ["graph-update", "admin-tool"],
  "filtered_by_state": [],
  "execution_time": "1.2s"
}
```

### 9. Testing Strategy

#### 9.1 Unit Tests

**Tool Filtering Logic:**
- Test group intersection calculations
- Test state-based filtering logic
- Verify default group and state assignment
- Test wildcard group behavior
- Validate empty group handling
- Test combined group+state filtering scenarios

**Configuration Validation:**
- Test tool loading with various group and state configurations
- Verify schema validation for invalid group and state specifications
- Test backward compatibility with existing configurations
- Validate state transition definitions and cycles

#### 9.2 Integration Tests

**Agent Behavior:**
- Verify agents only see group+state filtered tools
- Test request execution with various group combinations
- Test state transitions during agent execution
- Validate error handling when no tools are available
- Test workflow progression through multiple states

**Security Testing:**
- Test privilege escalation prevention
- Verify audit trail accuracy
- Test gateway integration with user permissions

#### 9.3 End-to-End Scenarios

**Multi-tenant Usage with State Workflows:**
```
Scenario: Different users with different tool access and workflow states
Given: User A has "read-only" permissions, state "undefined"
  And: User B has "write" permissions, state "analysis"
When: Both request knowledge operations
Then: User A gets read-only tools available in "undefined" state
  And: User B gets write tools available in "analysis" state
  And: State transitions are tracked per user session
  And: All usage and transitions are properly audited
```

**Workflow State Progression:**
```
Scenario: Complete workflow execution
Given: Request with groups ["knowledge", "compute"] and state "undefined"
When: Agent executes knowledge-query tool (transitions to "analysis")
  And: Agent executes complex-analysis tool (transitions to "results")
  And: Agent executes reset-workflow tool (transitions to "undefined")
Then: Each step has correctly filtered available tools
  And: State transitions are logged with timestamps
  And: Final state allows initial workflow to repeat
```

### 10. Performance Considerations

#### 10.1 Tool Loading Impact

**Configuration Loading:**
- Group and state metadata loaded once at startup
- Minimal memory overhead per tool (additional fields)
- No impact on tool initialization time

**Request Processing:**
- Combined group+state filtering occurs once per request
- O(n) complexity where n = number of configured tools
- State transitions add minimal overhead (string assignment)
- Negligible impact for typical tool counts (< 100)

#### 10.2 Optimization Strategies

**Pre-computed Tool Sets:**
- Cache tool sets by group+state combination
- Avoid repeated filtering for common group/state patterns
- Memory vs computation tradeoff for frequently used combinations

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
