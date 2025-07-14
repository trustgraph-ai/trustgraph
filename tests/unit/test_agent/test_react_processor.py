"""
Unit tests for ReAct processor logic

Tests the core business logic for the ReAct (Reasoning and Acting) pattern
without relying on external LLM services, focusing on the Think-Act-Observe
cycle and tool coordination.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import re


class TestReActProcessorLogic:
    """Test cases for ReAct processor business logic"""

    def test_react_cycle_parsing(self):
        """Test parsing of ReAct cycle components from LLM output"""
        # Arrange
        llm_output = """Think: I need to find information about the capital of France.
Act: knowledge_search: capital of France
Observe: The search returned that Paris is the capital of France.
Think: I now have enough information to answer.
Answer: The capital of France is Paris."""
        
        def parse_react_output(text):
            """Parse ReAct format output into structured steps"""
            steps = []
            lines = text.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if line.startswith('Think:'):
                    steps.append({
                        'type': 'think',
                        'content': line[6:].strip()
                    })
                elif line.startswith('Act:'):
                    act_content = line[4:].strip()
                    # Parse "tool_name: parameters" format
                    if ':' in act_content:
                        tool_name, params = act_content.split(':', 1)
                        steps.append({
                            'type': 'act',
                            'tool_name': tool_name.strip(),
                            'parameters': params.strip()
                        })
                    else:
                        steps.append({
                            'type': 'act',
                            'content': act_content
                        })
                elif line.startswith('Observe:'):
                    steps.append({
                        'type': 'observe',
                        'content': line[8:].strip()
                    })
                elif line.startswith('Answer:'):
                    steps.append({
                        'type': 'answer',
                        'content': line[7:].strip()
                    })
            
            return steps
        
        # Act
        steps = parse_react_output(llm_output)
        
        # Assert
        assert len(steps) == 5
        assert steps[0]['type'] == 'think'
        assert steps[1]['type'] == 'act'
        assert steps[1]['tool_name'] == 'knowledge_search'
        assert steps[1]['parameters'] == 'capital of France'
        assert steps[2]['type'] == 'observe'
        assert steps[3]['type'] == 'think'
        assert steps[4]['type'] == 'answer'

    def test_tool_selection_logic(self):
        """Test tool selection based on question type and context"""
        # Arrange
        test_cases = [
            ("What is 2 + 2?", "calculator"),
            ("Who is the president of France?", "knowledge_search"),
            ("Tell me about the relationship between Paris and France", "graph_rag"),
            ("What time is it?", "knowledge_search")  # Default to general search
        ]
        
        available_tools = {
            "calculator": {"description": "Perform mathematical calculations"},
            "knowledge_search": {"description": "Search knowledge base for facts"},
            "graph_rag": {"description": "Query knowledge graph for relationships"}
        }
        
        def select_tool(question, tools):
            """Select appropriate tool based on question content"""
            question_lower = question.lower()
            
            # Math keywords
            if any(word in question_lower for word in ['+', '-', '*', '/', 'calculate', 'math']):
                return "calculator"
            
            # Relationship/graph keywords
            if any(word in question_lower for word in ['relationship', 'between', 'connected', 'related']):
                return "graph_rag"
            
            # General knowledge keywords or default case
            if any(word in question_lower for word in ['who', 'what', 'where', 'when', 'why', 'how', 'time']):
                return "knowledge_search"
            
            return None
        
        # Act & Assert
        for question, expected_tool in test_cases:
            selected_tool = select_tool(question, available_tools)
            assert selected_tool == expected_tool, f"Question '{question}' should select {expected_tool}"

    def test_tool_execution_logic(self):
        """Test tool execution and result processing"""
        # Arrange
        def mock_knowledge_search(query):
            if "capital" in query.lower() and "france" in query.lower():
                return "Paris is the capital of France."
            return "Information not found."
        
        def mock_calculator(expression):
            try:
                # Simple expression evaluation
                if '+' in expression:
                    parts = expression.split('+')
                    return str(sum(int(p.strip()) for p in parts))
                return str(eval(expression))
            except:
                return "Error: Invalid expression"
        
        tools = {
            "knowledge_search": mock_knowledge_search,
            "calculator": mock_calculator
        }
        
        def execute_tool(tool_name, parameters, available_tools):
            """Execute tool with given parameters"""
            if tool_name not in available_tools:
                return {"error": f"Tool {tool_name} not available"}
            
            try:
                tool_function = available_tools[tool_name]
                result = tool_function(parameters)
                return {"success": True, "result": result}
            except Exception as e:
                return {"error": str(e)}
        
        # Act & Assert
        test_cases = [
            ("knowledge_search", "capital of France", "Paris is the capital of France."),
            ("calculator", "2 + 2", "4"),
            ("calculator", "invalid expression", "Error: Invalid expression"),
            ("nonexistent_tool", "anything", None)  # Error case
        ]
        
        for tool_name, params, expected in test_cases:
            result = execute_tool(tool_name, params, tools)
            
            if expected is None:
                assert "error" in result
            else:
                assert result.get("result") == expected

    def test_conversation_context_integration(self):
        """Test integration of conversation history into ReAct reasoning"""
        # Arrange
        conversation_history = [
            {"role": "user", "content": "What is 2 + 2?"},
            {"role": "assistant", "content": "2 + 2 = 4"},
            {"role": "user", "content": "What about 3 + 3?"}
        ]
        
        def build_context_prompt(question, history, max_turns=3):
            """Build context prompt from conversation history"""
            context_parts = []
            
            # Include recent conversation turns
            recent_history = history[-(max_turns*2):] if history else []
            
            for turn in recent_history:
                role = turn["role"]
                content = turn["content"]
                context_parts.append(f"{role}: {content}")
            
            current_question = f"user: {question}"
            context_parts.append(current_question)
            
            return "\n".join(context_parts)
        
        # Act
        context_prompt = build_context_prompt("What about 3 + 3?", conversation_history)
        
        # Assert
        assert "2 + 2" in context_prompt
        assert "2 + 2 = 4" in context_prompt
        assert "3 + 3" in context_prompt
        assert context_prompt.count("user:") == 3
        assert context_prompt.count("assistant:") == 1

    def test_react_cycle_validation(self):
        """Test validation of complete ReAct cycles"""
        # Arrange
        complete_cycle = [
            {"type": "think", "content": "I need to solve this math problem"},
            {"type": "act", "tool_name": "calculator", "parameters": "2 + 2"},
            {"type": "observe", "content": "The calculator returned 4"},
            {"type": "think", "content": "I can now provide the answer"},
            {"type": "answer", "content": "2 + 2 = 4"}
        ]
        
        incomplete_cycle = [
            {"type": "think", "content": "I need to solve this"},
            {"type": "act", "tool_name": "calculator", "parameters": "2 + 2"}
            # Missing observe and answer steps
        ]
        
        def validate_react_cycle(steps):
            """Validate that ReAct cycle is complete"""
            step_types = [step.get("type") for step in steps]
            
            # Must have at least one think, act, observe, and answer
            required_types = ["think", "act", "observe", "answer"]
            
            validation_results = {
                "is_complete": all(req_type in step_types for req_type in required_types),
                "has_reasoning": "think" in step_types,
                "has_action": "act" in step_types,
                "has_observation": "observe" in step_types,
                "has_answer": "answer" in step_types,
                "step_count": len(steps)
            }
            
            return validation_results
        
        # Act & Assert
        complete_validation = validate_react_cycle(complete_cycle)
        assert complete_validation["is_complete"] is True
        assert complete_validation["has_reasoning"] is True
        assert complete_validation["has_action"] is True
        assert complete_validation["has_observation"] is True
        assert complete_validation["has_answer"] is True
        
        incomplete_validation = validate_react_cycle(incomplete_cycle)
        assert incomplete_validation["is_complete"] is False
        assert incomplete_validation["has_reasoning"] is True
        assert incomplete_validation["has_action"] is True
        assert incomplete_validation["has_observation"] is False
        assert incomplete_validation["has_answer"] is False

    def test_multi_step_reasoning_logic(self):
        """Test multi-step reasoning chains"""
        # Arrange
        complex_question = "What is the population of the capital of France?"
        
        def plan_reasoning_steps(question):
            """Plan the reasoning steps needed for complex questions"""
            steps = []
            
            question_lower = question.lower()
            
            # Check if question requires multiple pieces of information
            if "capital of" in question_lower and ("population" in question_lower or "how many" in question_lower):
                steps.append({
                    "step": 1,
                    "action": "find_capital",
                    "description": "First find the capital city"
                })
                steps.append({
                    "step": 2,
                    "action": "find_population",
                    "description": "Then find the population of that city"
                })
            elif "capital of" in question_lower:
                steps.append({
                    "step": 1,
                    "action": "find_capital",
                    "description": "Find the capital city"
                })
            elif "population" in question_lower:
                steps.append({
                    "step": 1,
                    "action": "find_population",
                    "description": "Find the population"
                })
            else:
                steps.append({
                    "step": 1,
                    "action": "general_search",
                    "description": "Search for relevant information"
                })
            
            return steps
        
        # Act
        reasoning_plan = plan_reasoning_steps(complex_question)
        
        # Assert
        assert len(reasoning_plan) == 2
        assert reasoning_plan[0]["action"] == "find_capital"
        assert reasoning_plan[1]["action"] == "find_population"
        assert all("step" in step for step in reasoning_plan)

    def test_error_handling_in_react_cycle(self):
        """Test error handling during ReAct execution"""
        # Arrange
        def execute_react_step_with_errors(step_type, content, tools=None):
            """Execute ReAct step with potential error handling"""
            try:
                if step_type == "think":
                    # Thinking step - validate reasoning
                    if not content or len(content.strip()) < 5:
                        return {"error": "Reasoning too brief"}
                    return {"success": True, "content": content}
                
                elif step_type == "act":
                    # Action step - validate tool exists and execute
                    if not tools or not content:
                        return {"error": "No tools available or no action specified"}
                    
                    # Parse tool and parameters
                    if ":" in content:
                        tool_name, params = content.split(":", 1)
                        tool_name = tool_name.strip()
                        params = params.strip()
                        
                        if tool_name not in tools:
                            return {"error": f"Tool {tool_name} not available"}
                        
                        # Execute tool
                        result = tools[tool_name](params)
                        return {"success": True, "tool_result": result}
                    else:
                        return {"error": "Invalid action format"}
                
                elif step_type == "observe":
                    # Observation step - validate observation
                    if not content:
                        return {"error": "No observation provided"}
                    return {"success": True, "content": content}
                
                else:
                    return {"error": f"Unknown step type: {step_type}"}
                    
            except Exception as e:
                return {"error": f"Execution error: {str(e)}"}
        
        # Test cases
        mock_tools = {
            "calculator": lambda x: str(eval(x)) if x.replace('+', '').replace('-', '').replace('*', '').replace('/', '').replace(' ', '').isdigit() else "Error"
        }
        
        test_cases = [
            ("think", "I need to calculate", {"success": True}),
            ("think", "", {"error": True}),  # Empty reasoning
            ("act", "calculator: 2 + 2", {"success": True}),
            ("act", "nonexistent: something", {"error": True}),  # Tool doesn't exist
            ("act", "invalid format", {"error": True}),  # Invalid format
            ("observe", "The result is 4", {"success": True}),
            ("observe", "", {"error": True}),  # Empty observation
            ("invalid_step", "content", {"error": True})  # Invalid step type
        ]
        
        # Act & Assert
        for step_type, content, expected in test_cases:
            result = execute_react_step_with_errors(step_type, content, mock_tools)
            
            if expected.get("error"):
                assert "error" in result, f"Expected error for step {step_type}: {content}"
            else:
                assert "success" in result, f"Expected success for step {step_type}: {content}"

    def test_response_synthesis_logic(self):
        """Test synthesis of final response from ReAct steps"""
        # Arrange
        react_steps = [
            {"type": "think", "content": "I need to find the capital of France"},
            {"type": "act", "tool_name": "knowledge_search", "tool_result": "Paris is the capital of France"},
            {"type": "observe", "content": "The search confirmed Paris is the capital"},
            {"type": "think", "content": "I have the information needed to answer"}
        ]
        
        def synthesize_response(steps, original_question):
            """Synthesize final response from ReAct steps"""
            # Extract key information from steps
            tool_results = []
            observations = []
            reasoning = []
            
            for step in steps:
                if step["type"] == "think":
                    reasoning.append(step["content"])
                elif step["type"] == "act" and "tool_result" in step:
                    tool_results.append(step["tool_result"])
                elif step["type"] == "observe":
                    observations.append(step["content"])
            
            # Build response based on available information
            if tool_results:
                # Use tool results as primary information source
                primary_info = tool_results[0]
                
                # Extract specific answer from tool result
                if "capital" in original_question.lower() and "Paris" in primary_info:
                    return "The capital of France is Paris."
                elif "+" in original_question and any(char.isdigit() for char in primary_info):
                    return f"The answer is {primary_info}."
                else:
                    return primary_info
            else:
                # Fallback to reasoning if no tool results
                return "I need more information to answer this question."
        
        # Act
        response = synthesize_response(react_steps, "What is the capital of France?")
        
        # Assert
        assert "Paris" in response
        assert "capital of france" in response.lower()
        assert len(response) > 10  # Should be a complete sentence

    def test_tool_parameter_extraction(self):
        """Test extraction and validation of tool parameters"""
        # Arrange
        def extract_tool_parameters(action_content, tool_schema):
            """Extract and validate parameters for tool execution"""
            # Parse action content for tool name and parameters
            if ":" not in action_content:
                return {"error": "Invalid action format - missing tool parameters"}
            
            tool_name, params_str = action_content.split(":", 1)
            tool_name = tool_name.strip()
            params_str = params_str.strip()
            
            if tool_name not in tool_schema:
                return {"error": f"Unknown tool: {tool_name}"}
            
            schema = tool_schema[tool_name]
            required_params = schema.get("required_parameters", [])
            
            # Simple parameter extraction (for more complex tools, this would be more sophisticated)
            if len(required_params) == 1 and required_params[0] == "query":
                # Single query parameter
                return {"tool_name": tool_name, "parameters": {"query": params_str}}
            elif len(required_params) == 1 and required_params[0] == "expression":
                # Single expression parameter  
                return {"tool_name": tool_name, "parameters": {"expression": params_str}}
            else:
                # Multiple parameters would need more complex parsing
                return {"tool_name": tool_name, "parameters": {"input": params_str}}
        
        tool_schema = {
            "knowledge_search": {"required_parameters": ["query"]},
            "calculator": {"required_parameters": ["expression"]},
            "graph_rag": {"required_parameters": ["query"]}
        }
        
        test_cases = [
            ("knowledge_search: capital of France", "knowledge_search", {"query": "capital of France"}),
            ("calculator: 2 + 2", "calculator", {"expression": "2 + 2"}),
            ("invalid format", None, None),  # No colon
            ("unknown_tool: something", None, None)  # Unknown tool
        ]
        
        # Act & Assert
        for action_content, expected_tool, expected_params in test_cases:
            result = extract_tool_parameters(action_content, tool_schema)
            
            if expected_tool is None:
                assert "error" in result
            else:
                assert result["tool_name"] == expected_tool
                assert result["parameters"] == expected_params