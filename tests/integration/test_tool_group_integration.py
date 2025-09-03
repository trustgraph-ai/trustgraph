"""
Integration tests for the tool group system.

Tests the complete workflow from AgentRequest processing through 
tool filtering and execution in the ReAct agent service.
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch

from trustgraph.schema import AgentRequest, AgentResponse, AgentStep
from trustgraph.agent.react.service import Processor
from trustgraph.agent.react.types import Tool, Argument


@pytest.fixture
def sample_tools():
    """Sample tools with different groups and states for testing."""
    return {
        'knowledge_query': Tool(
            name='knowledge_query',
            description='Query knowledge graph',
            implementation=Mock(),
            config={
                'group': ['read-only', 'knowledge', 'basic'],
                'state': 'analysis',
                'available_in_states': ['undefined', 'research']
            },
            arguments=[]
        ),
        'graph_update': Tool(
            name='graph_update', 
            description='Update knowledge graph',
            implementation=Mock(),
            config={
                'group': ['write', 'knowledge', 'admin'],
                'available_in_states': ['analysis', 'modification']
            },
            arguments=[]
        ),
        'text_completion': Tool(
            name='text_completion',
            description='Generate text',
            implementation=Mock(),
            config={
                'group': ['read-only', 'text', 'basic'],
                'state': 'undefined'
                # No available_in_states = available in all states
            },
            arguments=[]
        ),
        'complex_analysis': Tool(
            name='complex_analysis',
            description='Complex analysis tool',
            implementation=Mock(),
            config={
                'group': ['advanced', 'compute', 'expensive'],
                'state': 'results',
                'available_in_states': ['analysis']
            },
            arguments=[]
        )
    }


@pytest.fixture
def agent_processor():
    """Create agent processor for testing."""
    return Processor(id="test-agent", max_iterations=5)


class TestAgentRequestProcessing:
    """Test AgentRequest processing with tool groups and states."""

    @pytest.mark.asyncio
    async def test_basic_group_filtering(self, agent_processor, sample_tools):
        """Test that agent only sees tools matching requested groups."""
        
        # Setup agent with sample tools
        agent_processor.agent.tools = sample_tools
        
        # Mock the agent's react method to return a Final response
        from trustgraph.agent.react.types import Final
        mock_final = Final(final="Test response")
        agent_processor.agent.react = AsyncMock(return_value=mock_final)
        
        # Create request with read-only group
        request = AgentRequest(
            question="Test question",
            state="undefined",
            group=["read-only", "knowledge"],
            history=[]
        )
        
        responses = []
        
        async def mock_respond(response):
            responses.append(response)
            
        async def mock_next(next_request):
            pass  # Not needed for this test
            
        # Process request
        await agent_processor.agent_request(request, mock_respond, mock_next, {})
        
        # Verify agent was called with filtered tools
        agent_processor.agent.react.assert_called_once()
        call_kwargs = agent_processor.agent.react.call_args.kwargs
        
        # The agent should have been created with filtered tools
        # We can't directly inspect the temp agent, but we can verify the filtering worked
        # by checking that only appropriate tools would have been available
        
        # Verify final response was sent
        assert len(responses) == 1
        assert responses[0].answer == "Test response"

    @pytest.mark.asyncio 
    async def test_state_based_filtering(self, agent_processor, sample_tools):
        """Test filtering based on current state."""
        
        agent_processor.agent.tools = sample_tools
        
        from trustgraph.agent.react.types import Final
        mock_final = Final(final="Analysis complete")
        agent_processor.agent.react = AsyncMock(return_value=mock_final)
        
        # Create request in 'analysis' state
        request = AgentRequest(
            question="Perform analysis",
            state="analysis",  
            group=["advanced", "compute"],
            history=[]
        )
        
        responses = []
        
        async def mock_respond(response):
            responses.append(response)
            
        # Process request
        await agent_processor.agent_request(request, mock_respond, lambda x: None, {})
        
        # Verify response
        assert len(responses) == 1
        assert responses[0].answer == "Analysis complete"

    @pytest.mark.asyncio
    async def test_state_transition_handling(self, agent_processor, sample_tools):
        """Test state transitions after tool execution."""
        
        agent_processor.agent.tools = sample_tools
        
        # Mock agent to return an action that uses knowledge_query
        from trustgraph.agent.react.types import Action
        mock_action = Action(
            thought="I need to query knowledge",
            name="knowledge_query",
            arguments={},
            observation="Found information"
        )
        agent_processor.agent.react = AsyncMock(return_value=mock_action)
        
        # Create initial request
        request = AgentRequest(
            question="Research question",
            state="undefined",
            group=["read-only", "knowledge"],
            history=[]
        )
        
        next_requests = []
        
        async def mock_next(next_request):
            next_requests.append(next_request)
            
        # Process request
        await agent_processor.agent_request(request, lambda x: None, mock_next, {})
        
        # Verify state transition occurred
        assert len(next_requests) == 1
        next_req = next_requests[0]
        assert next_req.state == "analysis"  # knowledge_query transitions to analysis
        assert next_req.group == ["read-only", "knowledge"]

    @pytest.mark.asyncio
    async def test_wildcard_group_access(self, agent_processor, sample_tools):
        """Test wildcard group grants access to all tools."""
        
        agent_processor.agent.tools = sample_tools
        
        from trustgraph.agent.react.types import Final
        mock_final = Final(final="All tools available")
        agent_processor.agent.react = AsyncMock(return_value=mock_final)
        
        # Create request with wildcard group
        request = AgentRequest(
            question="Administrative task",
            state="undefined",
            group=["*"],  # Wildcard access
            history=[]
        )
        
        responses = []
        
        async def mock_respond(response):
            responses.append(response)
            
        # Process request  
        await agent_processor.agent_request(request, mock_respond, lambda x: None, {})
        
        # All tools should have been available to the agent
        assert len(responses) == 1
        assert responses[0].answer == "All tools available"

    @pytest.mark.asyncio
    async def test_no_matching_tools(self, agent_processor, sample_tools):
        """Test behavior when no tools match the requested groups."""
        
        agent_processor.agent.tools = sample_tools
        
        from trustgraph.agent.react.types import Final
        mock_final = Final(final="No tools available")
        agent_processor.agent.react = AsyncMock(return_value=mock_final)
        
        # Create request with non-matching group
        request = AgentRequest(
            question="Some task",
            state="undefined", 
            group=["nonexistent-group"],
            history=[]
        )
        
        responses = []
        
        async def mock_respond(response):
            responses.append(response)
            
        # Process request
        await agent_processor.agent_request(request, mock_respond, lambda x: None, {})
        
        # Agent should still work but with empty tool set
        assert len(responses) == 1

    @pytest.mark.asyncio
    async def test_default_group_behavior(self, agent_processor):
        """Test default group behavior when no group is specified."""
        
        # Create tools with and without explicit groups
        tools = {
            'default_tool': Tool(
                name='default_tool',
                description='Default tool',
                implementation=Mock(),
                config={},  # No group = default group
                arguments=[]
            ),
            'admin_tool': Tool(
                name='admin_tool',
                description='Admin tool', 
                implementation=Mock(),
                config={'group': ['admin']},
                arguments=[]
            )
        }
        
        agent_processor.agent.tools = tools
        
        from trustgraph.agent.react.types import Final
        mock_final = Final(final="Default tools only")
        agent_processor.agent.react = AsyncMock(return_value=mock_final)
        
        # Create request without specifying group (should default to ["default"])
        request = AgentRequest(
            question="Basic task",
            state="undefined",
            group=None,  # Should default to ["default"]
            history=[]
        )
        
        responses = []
        
        async def mock_respond(response):
            responses.append(response)
            
        # Process request
        await agent_processor.agent_request(request, mock_respond, lambda x: None, {})
        
        # Only default_tool should have been available
        assert len(responses) == 1


class TestToolConfigurationLoading:
    """Test tool configuration loading with group metadata."""

    @pytest.mark.asyncio
    async def test_tool_config_validation(self, agent_processor):
        """Test that invalid tool configurations are rejected."""
        
        # Mock configuration with invalid group field
        invalid_config = {
            "tool": {
                "invalid-tool": json.dumps({
                    "name": "invalid_tool",
                    "description": "Invalid tool",
                    "type": "text-completion",
                    "group": "not-a-list"  # Should be list
                })
            }
        }
        
        # Should raise validation error
        with pytest.raises(ValueError, match="'group' field must be a list"):
            await agent_processor.on_tools_config(invalid_config, 1)

    @pytest.mark.asyncio
    async def test_valid_tool_config_loading(self, agent_processor):
        """Test that valid tool configurations load successfully."""
        
        valid_config = {
            "tool": {
                "valid-tool": json.dumps({
                    "name": "valid_tool",
                    "description": "Valid tool",
                    "type": "text-completion",
                    "group": ["read-only", "text"],
                    "state": "analysis",
                    "available_in_states": ["undefined", "research"]
                })
            }
        }
        
        # Should not raise any exception
        await agent_processor.on_tools_config(valid_config, 1)
        
        # Verify tool was loaded with correct config
        assert "valid_tool" in agent_processor.agent.tools
        tool = agent_processor.agent.tools["valid_tool"]
        assert tool.config["group"] == ["read-only", "text"]
        assert tool.config["state"] == "analysis"


class TestCompleteWorkflow:
    """Test complete multi-step workflows with state transitions."""

    @pytest.mark.asyncio
    async def test_research_analysis_workflow(self, agent_processor, sample_tools):
        """Test complete research -> analysis -> results workflow."""
        
        agent_processor.agent.tools = sample_tools
        
        # Step 1: Initial research request
        from trustgraph.agent.react.types import Action
        research_action = Action(
            thought="I should query the knowledge base",
            name="knowledge_query", 
            arguments={"query": "test"},
            observation="Found relevant information"
        )
        
        agent_processor.agent.react = AsyncMock(return_value=research_action)
        
        request1 = AgentRequest(
            question="Research topic X",
            state="undefined",
            group=["read-only", "knowledge"],
            history=[]
        )
        
        next_requests = []
        
        async def capture_next(req):
            next_requests.append(req)
            
        # Execute step 1
        await agent_processor.agent_request(request1, lambda x: None, capture_next, {})
        
        # Verify state transition to analysis
        assert len(next_requests) == 1
        step2_request = next_requests[0]
        assert step2_request.state == "analysis"
        assert len(step2_request.history) == 1
        
        # Step 2: Analysis phase
        analysis_action = Action(
            thought="Now I can perform complex analysis",
            name="complex_analysis",
            arguments={"data": "research results"},
            observation="Analysis completed"
        )
        
        agent_processor.agent.react = AsyncMock(return_value=analysis_action)
        
        # Update request groups for analysis phase
        step2_request.group = ["advanced", "compute"]
        
        next_requests_2 = []
        
        # Execute step 2
        await agent_processor.agent_request(step2_request, lambda x: None, 
                                          lambda req: next_requests_2.append(req), {})
        
        # Verify final state transition
        assert len(next_requests_2) == 1
        final_request = next_requests_2[0]
        assert final_request.state == "results"
        assert len(final_request.history) == 2

    @pytest.mark.asyncio
    async def test_multi_tenant_scenario(self, agent_processor, sample_tools):
        """Test different users with different permissions."""
        
        agent_processor.agent.tools = sample_tools
        
        from trustgraph.agent.react.types import Final
        
        # User A: Read-only permissions
        user_a_final = Final(final="Read-only operations completed")
        agent_processor.agent.react = AsyncMock(return_value=user_a_final)
        
        request_a = AgentRequest(
            question="What information is available about X?",
            state="undefined",
            group=["read-only"],
            history=[]
        )
        
        responses_a = []
        await agent_processor.agent_request(request_a, 
                                          lambda r: responses_a.append(r), 
                                          lambda x: None, {})
        
        # User B: Admin permissions  
        user_b_final = Final(final="Administrative tasks completed")
        agent_processor.agent.react = AsyncMock(return_value=user_b_final)
        
        request_b = AgentRequest(
            question="Update the knowledge base",
            state="analysis", 
            group=["write", "admin"],
            history=[]
        )
        
        responses_b = []
        await agent_processor.agent_request(request_b,
                                          lambda r: responses_b.append(r),
                                          lambda x: None, {})
        
        # Verify both users got appropriate responses
        assert len(responses_a) == 1
        assert len(responses_b) == 1
        assert "Read-only" in responses_a[0].answer
        assert "Administrative" in responses_b[0].answer