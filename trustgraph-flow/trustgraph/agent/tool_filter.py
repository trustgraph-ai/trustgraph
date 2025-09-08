"""
Tool filtering logic for the TrustGraph tool group system.

Provides functions to filter available tools based on group membership
and execution state as defined in the tool-group tech spec.
"""

import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


def filter_tools_by_group_and_state(
    tools: Dict[str, Any],
    requested_groups: Optional[List[str]] = None,
    current_state: Optional[str] = None
) -> Dict[str, Any]:
    """
    Filter tools based on group membership and execution state.
    
    Args:
        tools: Dictionary of tool_name -> tool_object
        requested_groups: List of groups requested (defaults to ["default"])
        current_state: Current execution state (defaults to "undefined")
        
    Returns:
        Dictionary of filtered tools that match group and state criteria
    """
    
    # Apply defaults as specified in tech spec
    if requested_groups is None:
        requested_groups = ["default"]
    if current_state is None or current_state == "":
        current_state = "undefined"
        
    logger.info(f"Filtering tools with groups={requested_groups}, state={current_state}")
    
    filtered_tools = {}
    
    for tool_name, tool in tools.items():
        if _is_tool_available(tool, requested_groups, current_state):
            filtered_tools[tool_name] = tool
        else:
            logger.debug(f"Tool {tool_name} filtered out")
            
    logger.info(f"Filtered {len(tools)} tools to {len(filtered_tools)} available tools")
    return filtered_tools


def _is_tool_available(
    tool: Any,
    requested_groups: List[str],
    current_state: str
) -> bool:
    """
    Check if a tool is available based on group and state criteria.
    
    Args:
        tool: Tool object with config attribute containing group/state metadata
        requested_groups: List of requested groups  
        current_state: Current execution state
        
    Returns:
        True if tool should be available, False otherwise
    """
    
    # Extract tool configuration
    config = getattr(tool, 'config', {})
    
    # Get tool groups (default to ["default"] if not specified)
    tool_groups = config.get('group', ["default"])
    if not isinstance(tool_groups, list):
        tool_groups = [tool_groups]
        
    # Get tool applicable states (default to all states if not specified)  
    applicable_states = config.get('applicable-states', ["*"])
    if not isinstance(applicable_states, list):
        applicable_states = [applicable_states]
    
    # Apply group filtering logic from tech spec:
    # Tool is available if intersection(tool_groups, requested_groups) is not empty 
    # OR "*" is in requested_groups (wildcard access)
    group_match = (
        "*" in requested_groups or 
        bool(set(tool_groups) & set(requested_groups))
    )
    
    # Apply state filtering logic from tech spec:
    # Tool is available if current_state is in applicable_states 
    # OR "*" is in applicable_states (available in all states)
    state_match = (
        "*" in applicable_states or 
        current_state in applicable_states
    )
    
    is_available = group_match and state_match
    
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool availability check: tool_groups={tool_groups}, "
            f"requested_groups={requested_groups}, applicable_states={applicable_states}, "
            f"current_state={current_state}, group_match={group_match}, "
            f"state_match={state_match}, is_available={is_available}"
        )
    
    return is_available


def get_next_state(tool: Any, current_state: str) -> str:
    """
    Get the next state after successful tool execution.
    
    Args:
        tool: Tool object with config attribute
        current_state: Current execution state
        
    Returns:
        Next state, or current_state if no transition is defined
    """
    config = getattr(tool, 'config', {})
    if config is None:
        config = {}
    next_state = config.get('state')
    
    if next_state:
        logger.debug(f"State transition: {current_state} -> {next_state}")
        return next_state
    else:
        logger.debug(f"No state transition defined, staying in {current_state}")
        return current_state


def validate_tool_config(config: Dict[str, Any]) -> None:
    """
    Validate tool configuration for group and state fields.
    
    Args:
        config: Tool configuration dictionary
        
    Raises:
        ValueError: If configuration is invalid
    """
    
    # Validate group field
    if 'group' in config:
        groups = config['group']
        if not isinstance(groups, list):
            raise ValueError("Tool 'group' field must be a list of strings")
        if not all(isinstance(g, str) for g in groups):
            raise ValueError("All group names must be strings")
            
    # Validate state field
    if 'state' in config:
        state = config['state']
        if not isinstance(state, str):
            raise ValueError("Tool 'state' field must be a string")
            
    # Validate applicable-states field
    if 'applicable-states' in config:
        states = config['applicable-states']
        if not isinstance(states, list):
            raise ValueError("Tool 'applicable-states' field must be a list of strings")
        if not all(isinstance(s, str) for s in states):
            raise ValueError("All state names must be strings")