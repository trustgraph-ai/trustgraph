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

    def test_multi_iteration_react_execution(self):
        """Test complete multi-iteration ReACT cycle with sequential tool invocations
        
        This test simulates a complex query that requires:
        1. Tool #1: Search for initial information
        2. Tool #2: Analyze/refine based on Tool #1's output  
        3. Tool #3: Generate final answer using accumulated context
        
        Each iteration includes Think -> Act -> Observe phases with
        observations feeding into subsequent thinking phases.
        """
        # Arrange
        question = "Find the GDP of the capital of Japan and compare it to Tokyo's population"
        
        # Mock tools that build on each other's outputs
        tool_invocation_log = []
        
        def mock_geo_search(query):
            """Tool 1: Geographic information search"""
            tool_invocation_log.append(("geo_search", query))
            if "capital" in query.lower() and "japan" in query.lower():
                return {"city": "Tokyo", "country": "Japan", "is_capital": True}
            return {"error": "Location not found"}
        
        def mock_economic_data(query, context=None):
            """Tool 2: Economic data retrieval (uses context from Tool 1)"""
            tool_invocation_log.append(("economic_data", query, context))
            if context and context.get("city") == "Tokyo":
                return {"city": "Tokyo", "gdp_trillion_yen": 115.7, "year": 2023}
            return {"error": "Economic data not available"}
        
        def mock_demographic_data(query, context=None):
            """Tool 3: Demographic data and comparison (uses context from Tools 1 & 2)"""
            tool_invocation_log.append(("demographic_data", query, context))
            if context and context.get("city") == "Tokyo":
                population_millions = 14.0
                gdp_from_context = context.get("gdp_trillion_yen", 0)
                return {
                    "city": "Tokyo",
                    "population_millions": population_millions,
                    "gdp_trillion_yen": gdp_from_context,
                    "gdp_per_capita_million_yen": round(gdp_from_context / population_millions, 2) if population_millions > 0 else 0
                }
            return {"error": "Demographic data not available"}
        
        # Execute multi-iteration ReACT cycle
        def execute_multi_iteration_react(question, tools):
            """Execute a complete multi-iteration ReACT cycle"""
            iterations = []
            context = {}
            
            # Iteration 1: Initial geographic search
            iteration_1 = {
                "iteration": 1,
                "think": "I need to first identify the capital of Japan to get its GDP",
                "act": {"tool": "geo_search", "query": "capital of Japan"},
                "observe": None
            }
            result_1 = tools["geo_search"](iteration_1["act"]["query"])
            iteration_1["observe"] = f"Found that {result_1['city']} is the capital of {result_1['country']}"
            context.update(result_1)
            iterations.append(iteration_1)
            
            # Iteration 2: Get economic data using context from iteration 1
            iteration_2 = {
                "iteration": 2,
                "think": f"Now I know {context['city']} is the capital. I need to get its GDP data",
                "act": {"tool": "economic_data", "query": f"GDP of {context['city']}"},
                "observe": None
            }
            result_2 = tools["economic_data"](iteration_2["act"]["query"], context)
            iteration_2["observe"] = f"Retrieved GDP data: {result_2['gdp_trillion_yen']} trillion yen for {result_2['year']}"
            context.update(result_2)
            iterations.append(iteration_2)
            
            # Iteration 3: Get demographic data and compare using accumulated context
            iteration_3 = {
                "iteration": 3,
                "think": f"I have the GDP ({context['gdp_trillion_yen']} trillion yen). Now I need population data to compare",
                "act": {"tool": "demographic_data", "query": f"population of {context['city']}"},
                "observe": None
            }
            result_3 = tools["demographic_data"](iteration_3["act"]["query"], context)
            iteration_3["observe"] = f"Population is {result_3['population_millions']} million. GDP per capita is {result_3['gdp_per_capita_million_yen']} million yen"
            context.update(result_3)
            iterations.append(iteration_3)
            
            # Final answer synthesis
            final_answer = {
                "think": "I now have all the information needed to answer the question",
                "answer": f"Tokyo, the capital of Japan, has a GDP of {context['gdp_trillion_yen']} trillion yen and a population of {context['population_millions']} million people, resulting in a GDP per capita of {context['gdp_per_capita_million_yen']} million yen."
            }
            
            return {
                "iterations": iterations,
                "final_answer": final_answer,
                "context": context,
                "tool_invocations": len(tool_invocation_log)
            }
        
        tools = {
            "geo_search": mock_geo_search,
            "economic_data": mock_economic_data,
            "demographic_data": mock_demographic_data
        }
        
        # Act
        result = execute_multi_iteration_react(question, tools)
        
        # Assert - Verify complete multi-iteration execution
        assert len(result["iterations"]) == 3, "Should have exactly 3 iterations"
        
        # Verify each iteration has complete Think-Act-Observe cycle
        for i, iteration in enumerate(result["iterations"], 1):
            assert iteration["iteration"] == i
            assert "think" in iteration and len(iteration["think"]) > 0
            assert "act" in iteration and "tool" in iteration["act"]
            assert "observe" in iteration and iteration["observe"] is not None
        
        # Verify sequential tool invocations
        assert tool_invocation_log[0][0] == "geo_search"
        assert tool_invocation_log[1][0] == "economic_data"
        assert tool_invocation_log[2][0] == "demographic_data"
        
        # Verify context accumulation across iterations
        assert "Tokyo" in tool_invocation_log[1][1], "Iteration 2 should use data from iteration 1"
        assert tool_invocation_log[2][2].get("gdp_trillion_yen") == 115.7, "Iteration 3 should have accumulated GDP data"
        
        # Verify observations feed into subsequent thinking
        assert "Tokyo" in result["iterations"][1]["think"], "Iteration 2 thinking should reference observation from iteration 1"
        assert "115.7" in result["iterations"][2]["think"], "Iteration 3 thinking should reference GDP from iteration 2"
        
        # Verify final answer synthesis
        assert "Tokyo" in result["final_answer"]["answer"]
        assert "115.7" in result["final_answer"]["answer"]
        assert "14.0" in result["final_answer"]["answer"]
        assert "8.26" in result["final_answer"]["answer"], "Should include calculated GDP per capita"
        
        # Verify all 3 tools were invoked in sequence
        assert result["tool_invocations"] == 3

    def test_multi_iteration_with_dynamic_tool_selection(self):
        """Test multi-iteration ReACT with mocked LLM reasoning dynamically selecting tools
        
        This test simulates how an LLM would dynamically choose tools based on:
        1. The original question
        2. Previous observations
        3. Accumulated context
        
        The mocked LLM reasoning adapts its tool selection based on what it has learned
        in previous iterations, mimicking real agent behavior.
        """
        # Arrange
        question = "What are the main exports of the largest city in Brazil by population?"
        
        # Track reasoning and tool selection
        reasoning_log = []
        tool_invocation_log = []
        
        def mock_llm_reasoning(question, history, available_tools):
            """Mock LLM that reasons about tool selection based on context"""
            # Analyze what we know from history
            context = {}
            for step in history:
                if "observation" in step:
                    # Extract information from observations
                    obs = step["observation"]
                    if "São Paulo" in obs:
                        context["city"] = "São Paulo"
                    if "largest city" in obs:
                        context["is_largest"] = True
                    if "million" in obs and "population" in obs:
                        context["has_population"] = True
                    if "exports" in obs:
                        context["has_exports"] = True
            
            # Decide next action based on what we know
            if not context.get("city"):
                # Step 1: Need to find the largest city
                reasoning = "I need to find the largest city in Brazil by population"
                tool = "geo_search"
                args = {"query": "largest city Brazil population"}
            elif not context.get("has_population"):
                # Step 2: Confirm population data
                reasoning = f"I found {context['city']}. Now I need to verify it's the largest by checking population"
                tool = "demographic_data"
                args = {"query": f"population {context['city']} Brazil"}
            elif not context.get("has_exports"):
                # Step 3: Get export information
                reasoning = f"Confirmed {context['city']} is the largest. Now I need export information"
                tool = "economic_data"
                args = {"query": f"main exports {context['city']} Brazil"}
            else:
                # Final: Have all information
                reasoning = "I have all the information needed to answer"
                tool = "final_answer"
                args = None
            
            reasoning_log.append({"reasoning": reasoning, "tool": tool, "context": context.copy()})
            return reasoning, tool, args
        
        def mock_geo_search(query):
            """Mock geographic search tool"""
            tool_invocation_log.append(("geo_search", query))
            if "largest city brazil" in query.lower():
                return {
                    "result": "São Paulo is the largest city in Brazil",
                    "details": {"city": "São Paulo", "country": "Brazil", "rank": 1}
                }
            return {"error": "No results found"}
        
        def mock_demographic_data(query):
            """Mock demographic data tool"""
            tool_invocation_log.append(("demographic_data", query))
            if "são paulo" in query.lower():
                return {
                    "result": "São Paulo has a population of 12.4 million in the city proper, 22.8 million in the metro area",
                    "details": {"city_population": 12.4, "metro_population": 22.8, "unit": "million"}
                }
            return {"error": "No demographic data found"}
        
        def mock_economic_data(query):
            """Mock economic data tool"""
            tool_invocation_log.append(("economic_data", query))
            if "são paulo" in query.lower() and "export" in query.lower():
                return {
                    "result": "São Paulo's main exports include aircraft, vehicles, machinery, coffee, and soybeans",
                    "details": {
                        "top_exports": ["aircraft", "vehicles", "machinery", "coffee", "soybeans"],
                        "export_value_billions_usd": 65.2
                    }
                }
            return {"error": "No economic data found"}
        
        # Execute multi-iteration ReACT with dynamic tool selection
        def execute_dynamic_react(question, tools, llm_reasoner):
            """Execute ReACT with dynamic LLM-based tool selection"""
            iterations = []
            history = []
            available_tools = list(tools.keys())
            
            max_iterations = 4
            for i in range(max_iterations):
                # LLM reasons about next action
                reasoning, tool_name, args = llm_reasoner(question, history, available_tools)
                
                if tool_name == "final_answer":
                    # Agent has decided it has enough information
                    final_answer = {
                        "reasoning": reasoning,
                        "answer": "São Paulo, Brazil's largest city with 12.4 million people, " +
                                "has main exports including aircraft, vehicles, machinery, coffee, and soybeans."
                    }
                    break
                
                # Execute selected tool
                iteration = {
                    "iteration": i + 1,
                    "think": reasoning,
                    "act": {"tool": tool_name, "args": args},
                    "observe": None
                }
                
                # Get tool result
                if tool_name in tools:
                    result = tools[tool_name](args["query"])
                    iteration["observe"] = result.get("result", "No information found")
                else:
                    iteration["observe"] = f"Tool {tool_name} not available"
                
                iterations.append(iteration)
                
                # Add to history for next iteration
                history.append({
                    "thought": reasoning,
                    "action": tool_name,
                    "args": args,
                    "observation": iteration["observe"]
                })
            
            return {
                "iterations": iterations,
                "final_answer": final_answer if 'final_answer' in locals() else None,
                "reasoning_log": reasoning_log,
                "tool_invocations": len(tool_invocation_log)
            }
        
        tools = {
            "geo_search": mock_geo_search,
            "demographic_data": mock_demographic_data,
            "economic_data": mock_economic_data
        }
        
        # Act
        result = execute_dynamic_react(question, tools, mock_llm_reasoning)
        
        # Assert - Verify dynamic multi-iteration execution
        assert len(result["iterations"]) == 3, "Should have 3 iterations before final answer"
        
        # Verify reasoning adapts based on observations
        assert len(reasoning_log) == 4, "Should have 4 reasoning steps (3 tools + final)"
        
        # Verify first iteration searches for largest city
        assert reasoning_log[0]["tool"] == "geo_search"
        assert "largest city" in reasoning_log[0]["reasoning"].lower()
        assert not reasoning_log[0]["context"].get("city")
        
        # Verify second iteration uses city name from first observation
        assert reasoning_log[1]["tool"] == "demographic_data"
        assert "São Paulo" in reasoning_log[1]["reasoning"]
        assert reasoning_log[1]["context"]["city"] == "São Paulo"
        
        # Verify third iteration builds on previous knowledge
        assert reasoning_log[2]["tool"] == "economic_data"
        assert "export" in reasoning_log[2]["reasoning"].lower()
        assert reasoning_log[2]["context"]["has_population"] is True
        
        # Verify final reasoning has all information
        assert reasoning_log[3]["tool"] == "final_answer"
        assert reasoning_log[3]["context"]["has_exports"] is True
        
        # Verify tool invocation sequence
        assert tool_invocation_log[0][0] == "geo_search"
        assert tool_invocation_log[1][0] == "demographic_data"
        assert tool_invocation_log[2][0] == "economic_data"
        
        # Verify observations influence subsequent tool selection
        assert "São Paulo" in result["iterations"][1]["act"]["args"]["query"]
        assert "São Paulo" in result["iterations"][2]["act"]["args"]["query"]
        
        # Verify final answer synthesizes all gathered information
        assert result["final_answer"] is not None
        assert "São Paulo" in result["final_answer"]["answer"]
        assert "12.4 million" in result["final_answer"]["answer"]
        assert "aircraft" in result["final_answer"]["answer"]
        assert "vehicles" in result["final_answer"]["answer"]

    def test_action_name_with_quotes_handling(self):
        """Test that action names with quotes are properly stripped
        
        This test verifies the fix for when LLMs output action names wrapped
        in quotes, e.g., Action: "get_bank_balance" instead of Action: get_bank_balance
        """
        # Arrange
        def parse_react_output(text):
            """Parse ReAct format output into structured steps"""
            steps = []
            lines = text.strip().split('\n')
            
            thought = None
            action = None
            args = None
            
            for line in lines:
                line = line.strip()
                if line.startswith('Think:') or line.startswith('Thought:'):
                    thought = line.split(':', 1)[1].strip()
                elif line.startswith('Action:'):
                    action = line[7:].strip()
                    # Strip quotes from action name - this is the fix being tested
                    while action and action[0] == '"':
                        action = action[1:]
                    while action and action[-1] == '"':
                        action = action[:-1]
                elif line.startswith('Args:'):
                    # Simple args parsing for test
                    args_text = line[5:].strip()
                    if args_text:
                        import json
                        try:
                            args = json.loads(args_text)
                        except:
                            args = {"raw": args_text}
            
            return {
                "thought": thought,
                "action": action,
                "args": args
            }
        
        # Test cases with various quote patterns
        test_cases = [
            # Normal case without quotes
            (
                'Thought: I need to check the bank balance\nAction: get_bank_balance\nArgs: {"account": "12345"}',
                "get_bank_balance"
            ),
            # Single quotes around action name
            (
                'Thought: I need to check the bank balance\nAction: "get_bank_balance"\nArgs: {"account": "12345"}',
                "get_bank_balance"
            ),
            # Multiple quotes (nested)
            (
                'Thought: I need to check the bank balance\nAction: ""get_bank_balance""\nArgs: {"account": "12345"}',
                "get_bank_balance"
            ),
            # Action with underscores and quotes
            (
                'Thought: I need to search\nAction: "search_knowledge_base"\nArgs: {"query": "test"}',
                "search_knowledge_base"
            ),
            # Action with hyphens and quotes
            (
                'Thought: I need to search\nAction: "search-knowledge-base"\nArgs: {"query": "test"}',
                "search-knowledge-base"
            ),
            # Edge case: just quotes (should result in empty string)
            (
                'Thought: Error case\nAction: ""\nArgs: {}',
                ""
            ),
            # Mixed quotes at start and end
            (
                'Thought: Processing\nAction: """complex_tool"""\nArgs: {}',
                "complex_tool"
            ),
        ]
        
        # Act & Assert
        for llm_output, expected_action in test_cases:
            result = parse_react_output(llm_output)
            assert result["action"] == expected_action, \
                f"Failed to parse action correctly from: {llm_output}\nExpected: {expected_action}, Got: {result['action']}"
        
        # Test with actual tool matching
        tools = {
            "get_bank_balance": {"description": "Get bank balance"},
            "search_knowledge_base": {"description": "Search knowledge"},
            "complex_tool": {"description": "Complex operations"}
        }
        
        # Simulate tool lookup with quoted action names
        quoted_actions = [
            '"get_bank_balance"',
            '""search_knowledge_base""',
            'complex_tool',  # without quotes
            '"complex_tool"'
        ]
        
        for quoted_action in quoted_actions:
            # Strip quotes as the fix does
            clean_action = quoted_action
            while clean_action and clean_action[0] == '"':
                clean_action = clean_action[1:]
            while clean_action and clean_action[-1] == '"':
                clean_action = clean_action[:-1]
            
            # Verify the cleaned action exists in tools (except empty string case)
            if clean_action:
                assert clean_action in tools, \
                    f"Cleaned action '{clean_action}' from '{quoted_action}' should be in tools"

    def test_mcp_tool_arguments_support(self):
        """Test that MCP tools can be configured with arguments and expose them correctly
        
        This test verifies the MCP tool arguments feature where:
        1. MCP tool configurations can specify arguments
        2. Configuration parsing extracts arguments correctly
        3. Arguments are structured properly for tool use
        """
        # Define a simple Argument class for testing (mimics the real one)
        class TestArgument:
            def __init__(self, name, type, description):
                self.name = name
                self.type = type 
                self.description = description
        
        # Define a mock McpToolImpl that mimics the new functionality
        class MockMcpToolImpl:
            def __init__(self, context, mcp_tool_id, arguments=None):
                self.context = context
                self.mcp_tool_id = mcp_tool_id
                self.arguments = arguments or []
            
            def get_arguments(self):
                return self.arguments
        
        # Test 1: MCP tool with arguments
        test_arguments = [
            TestArgument(
                name="account_id",
                type="string",
                description="Bank account identifier"
            ),
            TestArgument(
                name="date",
                type="string",
                description="Date for balance query (optional, format: YYYY-MM-DD)"
            )
        ]
        
        context_mock = lambda service_name: None
        mcp_tool_with_args = MockMcpToolImpl(
            context=context_mock,
            mcp_tool_id="get_bank_balance",
            arguments=test_arguments
        )
        
        returned_args = mcp_tool_with_args.get_arguments()
        
        # Verify arguments are stored and returned correctly
        assert len(returned_args) == 2
        assert returned_args[0].name == "account_id"
        assert returned_args[0].type == "string"
        assert returned_args[0].description == "Bank account identifier"
        assert returned_args[1].name == "date"
        assert returned_args[1].type == "string"
        assert "optional" in returned_args[1].description.lower()
        
        # Test 2: MCP tool without arguments (backward compatibility)
        mcp_tool_no_args = MockMcpToolImpl(
            context=context_mock,
            mcp_tool_id="simple_tool"
        )
        
        returned_args_empty = mcp_tool_no_args.get_arguments()
        assert len(returned_args_empty) == 0
        assert returned_args_empty == []
        
        # Test 3: MCP tool with empty arguments list
        mcp_tool_empty_args = MockMcpToolImpl(
            context=context_mock,
            mcp_tool_id="another_tool",
            arguments=[]
        )
        
        returned_args_explicit_empty = mcp_tool_empty_args.get_arguments()
        assert len(returned_args_explicit_empty) == 0
        assert returned_args_explicit_empty == []
        
        # Test 4: Configuration parsing simulation
        def simulate_config_parsing(config_data):
            """Simulate how service.py parses MCP tool configuration"""
            config_args = config_data.get("arguments", [])
            arguments = [
                TestArgument(
                    name=arg.get("name"),
                    type=arg.get("type"),
                    description=arg.get("description")
                )
                for arg in config_args
            ]
            return arguments
        
        # Test configuration with arguments
        config_with_args = {
            "type": "mcp-tool",
            "name": "get_bank_balance",
            "description": "Get bank account balance",
            "mcp-tool": "get_bank_balance",
            "arguments": [
                {
                    "name": "account_id",
                    "type": "string",
                    "description": "Bank account identifier"
                },
                {
                    "name": "date",
                    "type": "string",
                    "description": "Date for balance query (optional)"
                }
            ]
        }
        
        parsed_args = simulate_config_parsing(config_with_args)
        assert len(parsed_args) == 2
        assert parsed_args[0].name == "account_id"
        assert parsed_args[1].name == "date"
        
        # Test configuration without arguments
        config_without_args = {
            "type": "mcp-tool",
            "name": "simple_tool",
            "description": "Simple MCP tool",
            "mcp-tool": "simple_tool"
        }
        
        parsed_args_empty = simulate_config_parsing(config_without_args)
        assert len(parsed_args_empty) == 0
        
        # Test 5: Argument structure validation
        def validate_argument_structure(arg):
            """Validate that an argument has required fields"""
            required_fields = ['name', 'type', 'description']
            return all(hasattr(arg, field) and getattr(arg, field) for field in required_fields)
        
        # Validate all parsed arguments have proper structure
        for arg in parsed_args:
            assert validate_argument_structure(arg), f"Argument {arg.name} missing required fields"
        
        # Test 6: Prompt template integration simulation
        def simulate_prompt_template_rendering(tools):
            """Simulate how agent prompts include tool arguments"""
            tool_descriptions = []
            
            for tool in tools:
                tool_desc = f"- **{tool.name}**: {tool.description}"
                
                # Add argument details if present
                for arg in tool.arguments:
                    tool_desc += f"\n  - Required: `\"{arg.name}\"` ({arg.type}): {arg.description}"
                    
                tool_descriptions.append(tool_desc)
            
            return "\n".join(tool_descriptions)
        
        # Create mock tools with our MCP tool
        class MockTool:
            def __init__(self, name, description, arguments):
                self.name = name
                self.description = description
                self.arguments = arguments
        
        mock_tools = [
            MockTool("search", "Search the web", []),  # Tool without arguments
            MockTool("get_bank_balance", "Get bank account balance", parsed_args)  # MCP tool with arguments
        ]
        
        prompt_section = simulate_prompt_template_rendering(mock_tools)
        
        # Verify the prompt includes MCP tool arguments
        assert "get_bank_balance" in prompt_section
        assert "account_id" in prompt_section
        assert "Bank account identifier" in prompt_section
        assert "date" in prompt_section
        assert "(string)" in prompt_section
        assert "Required:" in prompt_section
        
        # Verify tools without arguments still work
        assert "search" in prompt_section
        assert "Search the web" in prompt_section

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
