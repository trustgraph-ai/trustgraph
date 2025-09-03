"""
Unit tests for the tool filtering logic in the tool group system.
"""

import pytest
import sys
import os
from unittest.mock import Mock

# Add trustgraph-flow to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'trustgraph-flow'))

from trustgraph.agent.tool_filter import (
    filter_tools_by_group_and_state,
    get_next_state,
    validate_tool_config,
    _is_tool_available
)


class TestToolFiltering:
    """Test tool filtering based on groups and states."""

    def test_filter_tools_default_group(self):
        """Tools without groups should belong to 'default' group."""
        tools = {
            'tool1': Mock(config={}),
            'tool2': Mock(config={'group': ['read-only']})
        }
        
        # Request default group (implicit)
        filtered = filter_tools_by_group_and_state(tools, None, None)
        
        # Only tool1 should be available (no group = default group)
        assert 'tool1' in filtered
        assert 'tool2' not in filtered

    def test_filter_tools_explicit_groups(self):
        """Test filtering with explicit group membership."""
        tools = {
            'read_tool': Mock(config={'group': ['read-only', 'basic']}),
            'write_tool': Mock(config={'group': ['write', 'admin']}),
            'mixed_tool': Mock(config={'group': ['read-only', 'write']})
        }
        
        # Request read-only tools
        filtered = filter_tools_by_group_and_state(tools, ['read-only'], None)
        
        assert 'read_tool' in filtered
        assert 'write_tool' not in filtered
        assert 'mixed_tool' in filtered  # Has read-only in its groups

    def test_filter_tools_multiple_requested_groups(self):
        """Test filtering with multiple requested groups."""
        tools = {
            'tool1': Mock(config={'group': ['read-only']}),
            'tool2': Mock(config={'group': ['write']}),
            'tool3': Mock(config={'group': ['admin']})
        }
        
        # Request read-only and write tools
        filtered = filter_tools_by_group_and_state(tools, ['read-only', 'write'], None)
        
        assert 'tool1' in filtered
        assert 'tool2' in filtered
        assert 'tool3' not in filtered

    def test_filter_tools_wildcard_group(self):
        """Test wildcard group grants access to all tools."""
        tools = {
            'tool1': Mock(config={'group': ['read-only']}),
            'tool2': Mock(config={'group': ['admin']}),
            'tool3': Mock(config={})  # default group
        }
        
        # Request wildcard access
        filtered = filter_tools_by_group_and_state(tools, ['*'], None)
        
        assert len(filtered) == 3
        assert all(tool in filtered for tool in tools)

    def test_filter_tools_by_state(self):
        """Test filtering based on available_in_states."""
        tools = {
            'init_tool': Mock(config={'available_in_states': ['undefined']}),
            'analysis_tool': Mock(config={'available_in_states': ['analysis']}),
            'any_state_tool': Mock(config={})  # available in all states
        }
        
        # Filter for 'analysis' state
        filtered = filter_tools_by_group_and_state(tools, ['default'], 'analysis')
        
        assert 'init_tool' not in filtered
        assert 'analysis_tool' in filtered
        assert 'any_state_tool' in filtered

    def test_filter_tools_state_wildcard(self):
        """Test tools with '*' in available_in_states are always available."""
        tools = {
            'wildcard_tool': Mock(config={'available_in_states': ['*']}),
            'specific_tool': Mock(config={'available_in_states': ['research']})
        }
        
        # Filter for 'analysis' state
        filtered = filter_tools_by_group_and_state(tools, ['default'], 'analysis')
        
        assert 'wildcard_tool' in filtered
        assert 'specific_tool' not in filtered

    def test_filter_tools_combined_group_and_state(self):
        """Test combined group and state filtering."""
        tools = {
            'valid_tool': Mock(config={
                'group': ['read-only'],
                'available_in_states': ['analysis']
            }),
            'wrong_group': Mock(config={
                'group': ['admin'],
                'available_in_states': ['analysis']
            }),
            'wrong_state': Mock(config={
                'group': ['read-only'],
                'available_in_states': ['research']
            }),
            'wrong_both': Mock(config={
                'group': ['admin'],
                'available_in_states': ['research']
            })
        }
        
        filtered = filter_tools_by_group_and_state(
            tools, ['read-only'], 'analysis'
        )
        
        assert 'valid_tool' in filtered
        assert 'wrong_group' not in filtered
        assert 'wrong_state' not in filtered
        assert 'wrong_both' not in filtered

    def test_filter_tools_empty_request_groups(self):
        """Test that empty group list results in no available tools."""
        tools = {
            'tool1': Mock(config={'group': ['read-only']}),
            'tool2': Mock(config={})
        }
        
        filtered = filter_tools_by_group_and_state(tools, [], None)
        
        assert len(filtered) == 0


class TestStateTransitions:
    """Test state transition logic."""

    def test_get_next_state_with_transition(self):
        """Test state transition when tool defines next state."""
        tool = Mock(config={'state': 'analysis'})
        
        next_state = get_next_state(tool, 'undefined')
        
        assert next_state == 'analysis'

    def test_get_next_state_no_transition(self):
        """Test no state change when tool doesn't define next state."""
        tool = Mock(config={})
        
        next_state = get_next_state(tool, 'research')
        
        assert next_state == 'research'

    def test_get_next_state_empty_config(self):
        """Test with tool that has no config."""
        tool = Mock(config=None)
        tool.config = None
        
        next_state = get_next_state(tool, 'initial')
        
        assert next_state == 'initial'


class TestConfigValidation:
    """Test tool configuration validation."""

    def test_validate_valid_config(self):
        """Test validation of valid configuration."""
        config = {
            'group': ['read-only', 'basic'],
            'state': 'analysis',
            'available_in_states': ['undefined', 'research']
        }
        
        # Should not raise an exception
        validate_tool_config(config)

    def test_validate_group_not_list(self):
        """Test validation fails when group is not a list."""
        config = {'group': 'read-only'}  # Should be list
        
        with pytest.raises(ValueError, match="'group' field must be a list"):
            validate_tool_config(config)

    def test_validate_group_non_string_elements(self):
        """Test validation fails when group contains non-strings."""
        config = {'group': ['read-only', 123]}  # 123 is not string
        
        with pytest.raises(ValueError, match="All group names must be strings"):
            validate_tool_config(config)

    def test_validate_state_not_string(self):
        """Test validation fails when state is not a string."""
        config = {'state': 123}  # Should be string
        
        with pytest.raises(ValueError, match="'state' field must be a string"):
            validate_tool_config(config)

    def test_validate_available_in_states_not_list(self):
        """Test validation fails when available_in_states is not a list."""
        config = {'available_in_states': 'undefined'}  # Should be list
        
        with pytest.raises(ValueError, match="'available_in_states' field must be a list"):
            validate_tool_config(config)

    def test_validate_available_in_states_non_string_elements(self):
        """Test validation fails when available_in_states contains non-strings."""
        config = {'available_in_states': ['undefined', 123]}
        
        with pytest.raises(ValueError, match="All state names must be strings"):
            validate_tool_config(config)

    def test_validate_minimal_config(self):
        """Test validation of minimal valid configuration."""
        config = {'name': 'test', 'description': 'Test tool'}
        
        # Should not raise an exception
        validate_tool_config(config)


class TestToolAvailability:
    """Test the internal _is_tool_available function."""

    def test_tool_available_default_groups_and_states(self):
        """Test tool with default groups and states."""
        tool = Mock(config={})
        
        # Default group request, default state
        assert _is_tool_available(tool, ['default'], 'undefined')
        
        # Non-default group request should fail
        assert not _is_tool_available(tool, ['admin'], 'undefined')

    def test_tool_available_string_group_conversion(self):
        """Test that single group string is converted to list."""
        tool = Mock(config={'group': 'read-only'})  # Single string
        
        assert _is_tool_available(tool, ['read-only'], 'undefined')
        assert not _is_tool_available(tool, ['admin'], 'undefined')

    def test_tool_available_string_state_conversion(self):
        """Test that single state string is converted to list."""
        tool = Mock(config={'available_in_states': 'analysis'})  # Single string
        
        assert _is_tool_available(tool, ['default'], 'analysis')
        assert not _is_tool_available(tool, ['default'], 'research')

    def test_tool_no_config_attribute(self):
        """Test tool without config attribute."""
        tool = Mock()
        del tool.config  # Remove config attribute
        
        # Should use defaults and be available for default group/state
        assert _is_tool_available(tool, ['default'], 'undefined')
        assert not _is_tool_available(tool, ['admin'], 'undefined')


class TestWorkflowScenarios:
    """Test complete workflow scenarios from the tech spec."""

    def test_research_to_analysis_workflow(self):
        """Test the research -> analysis workflow from tech spec."""
        tools = {
            'knowledge_query': Mock(config={
                'group': ['read-only', 'knowledge'],
                'state': 'analysis',
                'available_in_states': ['undefined', 'research']
            }),
            'complex_analysis': Mock(config={
                'group': ['advanced', 'compute'],
                'state': 'results',
                'available_in_states': ['analysis']
            }),
            'text_completion': Mock(config={
                'group': ['read-only', 'text', 'basic']
                # No available_in_states = available in all states
            })
        }
        
        # Phase 1: Initial research (undefined state)
        phase1_filtered = filter_tools_by_group_and_state(
            tools, ['read-only', 'knowledge'], 'undefined'
        )
        assert 'knowledge_query' in phase1_filtered
        assert 'text_completion' in phase1_filtered
        assert 'complex_analysis' not in phase1_filtered
        
        # Simulate tool execution and state transition
        executed_tool = phase1_filtered['knowledge_query']
        next_state = get_next_state(executed_tool, 'undefined')
        assert next_state == 'analysis'
        
        # Phase 2: Analysis state (include basic group for text_completion)
        phase2_filtered = filter_tools_by_group_and_state(
            tools, ['advanced', 'compute', 'basic'], 'analysis'
        )
        assert 'knowledge_query' not in phase2_filtered  # Not available in analysis
        assert 'complex_analysis' in phase2_filtered
        assert 'text_completion' in phase2_filtered  # Always available
        
        # Simulate complex analysis execution
        executed_tool = phase2_filtered['complex_analysis']
        final_state = get_next_state(executed_tool, 'analysis')
        assert final_state == 'results'