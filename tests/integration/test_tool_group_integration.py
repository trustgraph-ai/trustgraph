"""
Integration tests for the tool group system.

Tests the complete workflow of tool filtering and execution logic.
"""

import pytest
import json
import sys
import os
from unittest.mock import Mock, AsyncMock, patch

# Add trustgraph paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'trustgraph-base'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'trustgraph-flow'))

from trustgraph.agent.tool_filter import filter_tools_by_group_and_state, get_next_state, validate_tool_config


@pytest.fixture
def sample_tools():
    """Sample tools with different groups and states for testing."""
    return {
        'knowledge_query': Mock(config={
            'group': ['read-only', 'knowledge', 'basic'],
            'state': 'analysis',
            'applicable-states': ['undefined', 'research']
        }),
        'graph_update': Mock(config={
            'group': ['write', 'knowledge', 'admin'],
            'applicable-states': ['analysis', 'modification']
        }),
        'text_completion': Mock(config={
            'group': ['read-only', 'text', 'basic'],
            'state': 'undefined'
            # No applicable-states = available in all states
        }),
        'complex_analysis': Mock(config={
            'group': ['advanced', 'compute', 'expensive'],
            'state': 'results',
            'applicable-states': ['analysis']
        })
    }


class TestToolGroupFiltering:
    """Test tool group filtering integration scenarios."""

    def test_basic_group_filtering(self, sample_tools):
        """Test that filtering only returns tools matching requested groups."""
        
        # Filter for read-only and knowledge tools
        filtered = filter_tools_by_group_and_state(
            sample_tools, 
            ['read-only', 'knowledge'], 
            'undefined'
        )
        
        # Should include tools with matching groups and correct state
        assert 'knowledge_query' in filtered  # Has read-only + knowledge, available in undefined
        assert 'text_completion' in filtered  # Has read-only, available in all states
        assert 'graph_update' not in filtered  # Has knowledge but no read-only
        assert 'complex_analysis' not in filtered  # Wrong groups and state

    def test_state_based_filtering(self, sample_tools):
        """Test filtering based on current state."""
        
        # Filter for analysis state with advanced tools
        filtered = filter_tools_by_group_and_state(
            sample_tools, 
            ['advanced', 'compute'], 
            'analysis'
        )
        
        # Should only include tools available in analysis state
        assert 'complex_analysis' in filtered  # Available in analysis state
        assert 'knowledge_query' not in filtered  # Not available in analysis state
        assert 'graph_update' not in filtered  # Wrong group (no advanced/compute)
        assert 'text_completion' not in filtered  # Wrong group

    def test_state_transition_handling(self, sample_tools):
        """Test state transitions after tool execution."""
        
        # Get knowledge_query tool and test state transition
        knowledge_tool = sample_tools['knowledge_query']
        
        # Test state transition
        next_state = get_next_state(knowledge_tool, 'undefined')
        assert next_state == 'analysis'  # knowledge_query should transition to analysis
        
        # Test tool with no state transition
        text_tool = sample_tools['text_completion']
        next_state = get_next_state(text_tool, 'research')
        assert next_state == 'undefined'  # text_completion transitions to undefined

    def test_wildcard_group_access(self, sample_tools):
        """Test wildcard group grants access to all tools."""
        
        # Filter with wildcard group access
        filtered = filter_tools_by_group_and_state(
            sample_tools, 
            ['*'],  # Wildcard access
            'undefined'
        )
        
        # Should include all tools that are available in undefined state
        assert 'knowledge_query' in filtered  # Available in undefined
        assert 'text_completion' in filtered  # Available in all states
        assert 'graph_update' not in filtered  # Not available in undefined
        assert 'complex_analysis' not in filtered  # Not available in undefined

    def test_no_matching_tools(self, sample_tools):
        """Test behavior when no tools match the requested groups."""
        
        # Filter with non-matching group
        filtered = filter_tools_by_group_and_state(
            sample_tools, 
            ['nonexistent-group'], 
            'undefined'
        )
        
        # Should return empty dictionary
        assert len(filtered) == 0

    def test_default_group_behavior(self):
        """Test default group behavior when no group is specified."""
        
        # Create tools with and without explicit groups
        tools = {
            'default_tool': Mock(config={}),  # No group = default group
            'admin_tool': Mock(config={'group': ['admin']})
        }
        
        # Filter with no group specified (should default to ["default"])
        filtered = filter_tools_by_group_and_state(tools, None, 'undefined')
        
        # Only default_tool should be available
        assert 'default_tool' in filtered
        assert 'admin_tool' not in filtered


class TestToolConfigurationValidation:
    """Test tool configuration validation with group metadata."""

    def test_tool_config_validation_invalid(self):
        """Test that invalid tool configurations are rejected."""
        
        # Test invalid group field (should be list)
        invalid_config = {
            "name": "invalid_tool",
            "description": "Invalid tool",
            "type": "text-completion",
            "group": "not-a-list"  # Should be list
        }
        
        # Should raise validation error
        with pytest.raises(ValueError, match="'group' field must be a list"):
            validate_tool_config(invalid_config)

    def test_tool_config_validation_valid(self):
        """Test that valid tool configurations are accepted."""
        
        valid_config = {
            "name": "valid_tool",
            "description": "Valid tool",
            "type": "text-completion",
            "group": ["read-only", "text"],
            "state": "analysis",
            "applicable-states": ["undefined", "research"]
        }
        
        # Should not raise any exception
        validate_tool_config(valid_config)
        
    def test_kebab_case_field_names(self):
        """Test that kebab-case field names are properly handled."""
        
        config = {
            "name": "test_tool",
            "group": ["basic"],
            "applicable-states": ["undefined", "analysis"]  # kebab-case
        }
        
        # Should validate without error
        validate_tool_config(config)
        
        # Create mock tool and test filtering
        tool = Mock(config=config)
        
        # Test that kebab-case field is properly read
        filtered = filter_tools_by_group_and_state(
            {'test_tool': tool}, 
            ['basic'], 
            'analysis'
        )
        
        assert 'test_tool' in filtered


class TestCompleteWorkflow:
    """Test complete multi-step workflows with state transitions."""

    def test_research_analysis_workflow(self, sample_tools):
        """Test complete research -> analysis -> results workflow."""
        
        # Step 1: Initial research phase (undefined state)
        step1_filtered = filter_tools_by_group_and_state(
            sample_tools,
            ['read-only', 'knowledge'],
            'undefined'
        )
        
        # Should have access to knowledge_query and text_completion
        assert 'knowledge_query' in step1_filtered
        assert 'text_completion' in step1_filtered
        assert 'complex_analysis' not in step1_filtered  # Not available in undefined
        
        # Simulate executing knowledge_query tool
        knowledge_tool = step1_filtered['knowledge_query']
        next_state = get_next_state(knowledge_tool, 'undefined')
        assert next_state == 'analysis'  # Transition to analysis state
        
        # Step 2: Analysis phase
        step2_filtered = filter_tools_by_group_and_state(
            sample_tools,
            ['advanced', 'compute', 'text'],  # Include text for text_completion
            'analysis'
        )
        
        # Should have access to complex_analysis and text_completion
        assert 'complex_analysis' in step2_filtered
        assert 'text_completion' in step2_filtered  # Available in all states
        assert 'knowledge_query' not in step2_filtered  # Not available in analysis
        
        # Simulate executing complex_analysis tool
        analysis_tool = step2_filtered['complex_analysis']
        final_state = get_next_state(analysis_tool, 'analysis')
        assert final_state == 'results'  # Transition to results state

    def test_multi_tenant_scenario(self, sample_tools):
        """Test different users with different permissions."""
        
        # User A: Read-only permissions in undefined state
        user_a_tools = filter_tools_by_group_and_state(
            sample_tools,
            ['read-only'],
            'undefined'
        )
        
        # Should only have access to read-only tools in undefined state
        assert 'knowledge_query' in user_a_tools  # read-only + available in undefined
        assert 'text_completion' in user_a_tools  # read-only + available in all states
        assert 'graph_update' not in user_a_tools  # write permissions required
        assert 'complex_analysis' not in user_a_tools  # advanced permissions required
        
        # User B: Admin permissions in analysis state
        user_b_tools = filter_tools_by_group_and_state(
            sample_tools,
            ['write', 'admin'],
            'analysis'
        )
        
        # Should have access to admin tools available in analysis state
        assert 'graph_update' in user_b_tools  # admin + available in analysis
        assert 'complex_analysis' not in user_b_tools  # wrong group (needs advanced/compute)
        assert 'knowledge_query' not in user_b_tools  # not available in analysis state
        assert 'text_completion' not in user_b_tools  # wrong group (no admin)