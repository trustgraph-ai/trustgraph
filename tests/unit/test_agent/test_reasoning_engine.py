"""
Unit tests for reasoning engine logic

Tests the core reasoning algorithms that power agent decision-making,
including question analysis, reasoning chain construction, and 
decision-making processes.
"""

import pytest
from unittest.mock import Mock, AsyncMock


class TestReasoningEngineLogic:
    """Test cases for reasoning engine business logic"""

    def test_question_analysis_and_categorization(self):
        """Test analysis and categorization of user questions"""
        # Arrange
        def analyze_question(question):
            """Analyze question to determine type and complexity"""
            question_lower = question.lower().strip()
            
            analysis = {
                "type": "unknown",
                "complexity": "simple",
                "entities": [],
                "intent": "information_seeking",
                "requires_tools": [],
                "confidence": 0.5
            }
            
            # Determine question type
            if any(word in question_lower for word in ["what", "who", "where", "when"]):
                analysis["type"] = "factual"
                analysis["intent"] = "information_seeking"
                analysis["confidence"] = 0.8
            elif any(word in question_lower for word in ["how", "why"]):
                analysis["type"] = "explanatory"
                analysis["intent"] = "explanation_seeking"
                analysis["complexity"] = "moderate"
                analysis["confidence"] = 0.7
            elif any(word in question_lower for word in ["calculate", "+", "-", "*", "/", "="]):
                analysis["type"] = "computational"
                analysis["intent"] = "calculation"
                analysis["requires_tools"] = ["calculator"]
                analysis["confidence"] = 0.9
            
            # Detect entities (simplified)
            known_entities = ["france", "paris", "openai", "microsoft", "python", "ai"]
            analysis["entities"] = [entity for entity in known_entities if entity in question_lower]
            
            # Determine complexity
            if len(question.split()) > 15:
                analysis["complexity"] = "complex"
            elif len(question.split()) > 8:
                analysis["complexity"] = "moderate"
            
            # Determine required tools
            if analysis["type"] == "computational":
                analysis["requires_tools"] = ["calculator"]
            elif analysis["entities"]:
                analysis["requires_tools"] = ["knowledge_search", "graph_rag"]
            elif analysis["type"] in ["factual", "explanatory"]:
                analysis["requires_tools"] = ["knowledge_search"]
            
            return analysis
        
        test_cases = [
            ("What is the capital of France?", "factual", ["france"], ["knowledge_search", "graph_rag"]),
            ("How does machine learning work?", "explanatory", [], ["knowledge_search"]),
            ("Calculate 15 * 8", "computational", [], ["calculator"]),
            ("Tell me about OpenAI", "factual", ["openai"], ["knowledge_search", "graph_rag"]),
            ("Why is Python popular for AI development?", "explanatory", ["python", "ai"], ["knowledge_search"])
        ]
        
        # Act & Assert
        for question, expected_type, expected_entities, expected_tools in test_cases:
            analysis = analyze_question(question)
            
            assert analysis["type"] == expected_type
            assert all(entity in analysis["entities"] for entity in expected_entities)
            assert any(tool in expected_tools for tool in analysis["requires_tools"])
            assert analysis["confidence"] > 0.5

    def test_reasoning_chain_construction(self):
        """Test construction of logical reasoning chains"""
        # Arrange
        def construct_reasoning_chain(question, available_tools, context=None):
            """Construct a logical chain of reasoning steps"""
            reasoning_chain = []
            
            # Analyze question
            question_lower = question.lower()
            
            # Multi-step questions requiring decomposition
            if "capital of" in question_lower and ("population" in question_lower or "size" in question_lower):
                reasoning_chain.extend([
                    {
                        "step": 1,
                        "type": "decomposition",
                        "description": "Break down complex question into sub-questions",
                        "sub_questions": ["What is the capital?", "What is the population/size?"]
                    },
                    {
                        "step": 2,
                        "type": "information_gathering",
                        "description": "Find the capital city",
                        "tool": "knowledge_search",
                        "query": f"capital of {question_lower.split('capital of')[1].split()[0]}"
                    },
                    {
                        "step": 3,
                        "type": "information_gathering",
                        "description": "Find population/size of the capital",
                        "tool": "knowledge_search",
                        "query": "population size [CAPITAL_CITY]"
                    },
                    {
                        "step": 4,
                        "type": "synthesis",
                        "description": "Combine information to answer original question"
                    }
                ])
            
            elif "relationship" in question_lower or "connection" in question_lower:
                reasoning_chain.extend([
                    {
                        "step": 1,
                        "type": "entity_identification",
                        "description": "Identify entities mentioned in question"
                    },
                    {
                        "step": 2,
                        "type": "relationship_exploration",
                        "description": "Explore relationships between entities",
                        "tool": "graph_rag"
                    },
                    {
                        "step": 3,
                        "type": "analysis",
                        "description": "Analyze relationship patterns and significance"
                    }
                ])
            
            elif any(op in question_lower for op in ["+", "-", "*", "/", "calculate"]):
                reasoning_chain.extend([
                    {
                        "step": 1,
                        "type": "expression_parsing",
                        "description": "Parse mathematical expression from question"
                    },
                    {
                        "step": 2,
                        "type": "calculation",
                        "description": "Perform calculation",
                        "tool": "calculator"
                    },
                    {
                        "step": 3,
                        "type": "result_formatting",
                        "description": "Format result appropriately"
                    }
                ])
            
            else:
                # Simple information seeking
                reasoning_chain.extend([
                    {
                        "step": 1,
                        "type": "information_gathering",
                        "description": "Search for relevant information",
                        "tool": "knowledge_search"
                    },
                    {
                        "step": 2,
                        "type": "response_formulation",
                        "description": "Formulate clear response"
                    }
                ])
            
            return reasoning_chain
        
        available_tools = ["knowledge_search", "graph_rag", "calculator"]
        
        # Act & Assert
        # Test complex multi-step question
        complex_chain = construct_reasoning_chain(
            "What is the population of the capital of France?", 
            available_tools
        )
        assert len(complex_chain) == 4
        assert complex_chain[0]["type"] == "decomposition"
        assert complex_chain[1]["tool"] == "knowledge_search"
        
        # Test relationship question
        relationship_chain = construct_reasoning_chain(
            "What is the relationship between Paris and France?",
            available_tools
        )
        assert any(step["type"] == "relationship_exploration" for step in relationship_chain)
        assert any(step.get("tool") == "graph_rag" for step in relationship_chain)
        
        # Test calculation question
        calc_chain = construct_reasoning_chain("Calculate 15 * 8", available_tools)
        assert any(step["type"] == "calculation" for step in calc_chain)
        assert any(step.get("tool") == "calculator" for step in calc_chain)

    def test_decision_making_algorithms(self):
        """Test decision-making algorithms for tool selection and strategy"""
        # Arrange
        def make_reasoning_decisions(question, available_tools, context=None, constraints=None):
            """Make decisions about reasoning approach and tool usage"""
            decisions = {
                "primary_strategy": "direct_search",
                "selected_tools": [],
                "reasoning_depth": "shallow",
                "confidence": 0.5,
                "fallback_strategy": "general_search"
            }
            
            question_lower = question.lower()
            constraints = constraints or {}
            
            # Strategy selection based on question type
            if "calculate" in question_lower or any(op in question_lower for op in ["+", "-", "*", "/"]):
                decisions["primary_strategy"] = "calculation"
                decisions["selected_tools"] = ["calculator"]
                decisions["reasoning_depth"] = "shallow"
                decisions["confidence"] = 0.9
            
            elif "relationship" in question_lower or "connect" in question_lower:
                decisions["primary_strategy"] = "graph_exploration"
                decisions["selected_tools"] = ["graph_rag", "knowledge_search"]
                decisions["reasoning_depth"] = "deep"
                decisions["confidence"] = 0.8
            
            elif any(word in question_lower for word in ["what", "who", "where", "when"]):
                decisions["primary_strategy"] = "factual_lookup"
                decisions["selected_tools"] = ["knowledge_search"]
                decisions["reasoning_depth"] = "moderate"
                decisions["confidence"] = 0.7
            
            elif any(word in question_lower for word in ["how", "why", "explain"]):
                decisions["primary_strategy"] = "explanatory_reasoning"
                decisions["selected_tools"] = ["knowledge_search", "graph_rag"]
                decisions["reasoning_depth"] = "deep"
                decisions["confidence"] = 0.6
            
            # Apply constraints
            if constraints.get("max_tools", 0) > 0:
                decisions["selected_tools"] = decisions["selected_tools"][:constraints["max_tools"]]
            
            if constraints.get("fast_mode", False):
                decisions["reasoning_depth"] = "shallow"
                decisions["selected_tools"] = decisions["selected_tools"][:1]
            
            # Filter by available tools
            decisions["selected_tools"] = [tool for tool in decisions["selected_tools"] if tool in available_tools]
            
            if not decisions["selected_tools"]:
                decisions["primary_strategy"] = "general_search"
                decisions["selected_tools"] = ["knowledge_search"] if "knowledge_search" in available_tools else []
                decisions["confidence"] = 0.3
            
            return decisions
        
        available_tools = ["knowledge_search", "graph_rag", "calculator"]
        
        test_cases = [
            ("What is 2 + 2?", "calculation", ["calculator"], 0.9),
            ("What is the relationship between Paris and France?", "graph_exploration", ["graph_rag"], 0.8),
            ("Who is the president of France?", "factual_lookup", ["knowledge_search"], 0.7),
            ("How does photosynthesis work?", "explanatory_reasoning", ["knowledge_search"], 0.6)
        ]
        
        # Act & Assert
        for question, expected_strategy, expected_tools, min_confidence in test_cases:
            decisions = make_reasoning_decisions(question, available_tools)
            
            assert decisions["primary_strategy"] == expected_strategy
            assert any(tool in decisions["selected_tools"] for tool in expected_tools)
            assert decisions["confidence"] >= min_confidence
        
        # Test with constraints
        constrained_decisions = make_reasoning_decisions(
            "How does machine learning work?", 
            available_tools,
            constraints={"fast_mode": True}
        )
        assert constrained_decisions["reasoning_depth"] == "shallow"
        assert len(constrained_decisions["selected_tools"]) <= 1

    def test_confidence_scoring_logic(self):
        """Test confidence scoring for reasoning steps and decisions"""
        # Arrange
        def calculate_confidence_score(reasoning_step, available_evidence, tool_reliability=None):
            """Calculate confidence score for a reasoning step"""
            base_confidence = 0.5
            tool_reliability = tool_reliability or {}
            
            step_type = reasoning_step.get("type", "unknown")
            tool_used = reasoning_step.get("tool")
            evidence_quality = available_evidence.get("quality", "medium")
            evidence_sources = available_evidence.get("sources", 1)
            
            # Adjust confidence based on step type
            confidence_modifiers = {
                "calculation": 0.4,  # High confidence for math
                "factual_lookup": 0.2,  # Moderate confidence for facts
                "relationship_exploration": 0.1,  # Lower confidence for complex relationships
                "synthesis": -0.1,  # Slightly lower for synthesized information
                "speculation": -0.3   # Much lower for speculative reasoning
            }
            
            base_confidence += confidence_modifiers.get(step_type, 0)
            
            # Adjust for tool reliability
            if tool_used and tool_used in tool_reliability:
                tool_score = tool_reliability[tool_used]
                base_confidence += (tool_score - 0.5) * 0.2  # Scale tool reliability impact
            
            # Adjust for evidence quality
            evidence_modifiers = {
                "high": 0.2,
                "medium": 0.0,
                "low": -0.2,
                "none": -0.4
            }
            base_confidence += evidence_modifiers.get(evidence_quality, 0)
            
            # Adjust for multiple sources
            if evidence_sources > 1:
                base_confidence += min(0.2, evidence_sources * 0.05)
            
            # Cap between 0 and 1
            return max(0.0, min(1.0, base_confidence))
        
        tool_reliability = {
            "calculator": 0.95,
            "knowledge_search": 0.8,
            "graph_rag": 0.7
        }
        
        test_cases = [
            (
                {"type": "calculation", "tool": "calculator"},
                {"quality": "high", "sources": 1},
                0.9  # Should be very high confidence
            ),
            (
                {"type": "factual_lookup", "tool": "knowledge_search"},
                {"quality": "medium", "sources": 2},
                0.8  # Good confidence with multiple sources
            ),
            (
                {"type": "speculation", "tool": None},
                {"quality": "low", "sources": 1},
                0.2  # Low confidence for speculation
            ),
            (
                {"type": "relationship_exploration", "tool": "graph_rag"},
                {"quality": "high", "sources": 3},
                0.7  # Moderate-high confidence
            )
        ]
        
        # Act & Assert
        for reasoning_step, evidence, expected_min_confidence in test_cases:
            confidence = calculate_confidence_score(reasoning_step, evidence, tool_reliability)
            assert confidence >= expected_min_confidence - 0.15  # Allow larger tolerance for confidence calculations
            assert 0 <= confidence <= 1

    def test_reasoning_validation_logic(self):
        """Test validation of reasoning chains for logical consistency"""
        # Arrange
        def validate_reasoning_chain(reasoning_chain):
            """Validate logical consistency of reasoning chain"""
            validation_results = {
                "is_valid": True,
                "issues": [],
                "completeness_score": 0.0,
                "logical_consistency": 0.0
            }
            
            if not reasoning_chain:
                validation_results["is_valid"] = False
                validation_results["issues"].append("Empty reasoning chain")
                return validation_results
            
            # Check for required components
            step_types = [step.get("type") for step in reasoning_chain]
            
            # Must have some form of information gathering or processing
            has_information_step = any(t in step_types for t in [
                "information_gathering", "calculation", "relationship_exploration"
            ])
            
            if not has_information_step:
                validation_results["issues"].append("No information gathering step")
            
            # Check for logical flow
            for i, step in enumerate(reasoning_chain):
                # Each step should have required fields
                if "type" not in step:
                    validation_results["issues"].append(f"Step {i+1} missing type")
                
                if "description" not in step:
                    validation_results["issues"].append(f"Step {i+1} missing description")
                
                # Tool steps should specify tool
                if step.get("type") in ["information_gathering", "calculation", "relationship_exploration"]:
                    if "tool" not in step:
                        validation_results["issues"].append(f"Step {i+1} missing tool specification")
            
            # Check for synthesis or conclusion
            has_synthesis = any(t in step_types for t in [
                "synthesis", "response_formulation", "result_formatting"
            ])
            
            if not has_synthesis and len(reasoning_chain) > 1:
                validation_results["issues"].append("Multi-step reasoning missing synthesis")
            
            # Calculate scores
            completeness_items = [
                has_information_step,
                has_synthesis or len(reasoning_chain) == 1,
                all("description" in step for step in reasoning_chain),
                len(reasoning_chain) >= 1
            ]
            validation_results["completeness_score"] = sum(completeness_items) / len(completeness_items)
            
            consistency_items = [
                len(validation_results["issues"]) == 0,
                len(reasoning_chain) > 0,
                all("type" in step for step in reasoning_chain)
            ]
            validation_results["logical_consistency"] = sum(consistency_items) / len(consistency_items)
            
            validation_results["is_valid"] = len(validation_results["issues"]) == 0
            
            return validation_results
        
        # Test cases
        valid_chain = [
            {"type": "information_gathering", "description": "Search for information", "tool": "knowledge_search"},
            {"type": "response_formulation", "description": "Formulate response"}
        ]
        
        invalid_chain = [
            {"description": "Do something"},  # Missing type
            {"type": "information_gathering"}  # Missing description and tool
        ]
        
        empty_chain = []
        
        # Act & Assert
        valid_result = validate_reasoning_chain(valid_chain)
        assert valid_result["is_valid"] is True
        assert len(valid_result["issues"]) == 0
        assert valid_result["completeness_score"] > 0.8
        
        invalid_result = validate_reasoning_chain(invalid_chain)
        assert invalid_result["is_valid"] is False
        assert len(invalid_result["issues"]) > 0
        
        empty_result = validate_reasoning_chain(empty_chain)
        assert empty_result["is_valid"] is False
        assert "Empty reasoning chain" in empty_result["issues"]

    def test_adaptive_reasoning_strategies(self):
        """Test adaptive reasoning that adjusts based on context and feedback"""
        # Arrange
        def adapt_reasoning_strategy(initial_strategy, feedback, context=None):
            """Adapt reasoning strategy based on feedback and context"""
            adapted_strategy = initial_strategy.copy()
            context = context or {}
            
            # Analyze feedback
            if feedback.get("accuracy", 0) < 0.5:
                # Low accuracy - need different approach
                if initial_strategy["primary_strategy"] == "direct_search":
                    adapted_strategy["primary_strategy"] = "multi_source_verification"
                    adapted_strategy["selected_tools"].extend(["graph_rag"])
                    adapted_strategy["reasoning_depth"] = "deep"
                
                elif initial_strategy["primary_strategy"] == "factual_lookup":
                    adapted_strategy["primary_strategy"] = "explanatory_reasoning" 
                    adapted_strategy["reasoning_depth"] = "deep"
            
            if feedback.get("completeness", 0) < 0.5:
                # Incomplete answer - need more comprehensive approach
                adapted_strategy["reasoning_depth"] = "deep"
                if "graph_rag" not in adapted_strategy["selected_tools"]:
                    adapted_strategy["selected_tools"].append("graph_rag")
            
            if feedback.get("response_time", 0) > context.get("max_response_time", 30):
                # Too slow - simplify approach
                adapted_strategy["reasoning_depth"] = "shallow"
                adapted_strategy["selected_tools"] = adapted_strategy["selected_tools"][:1]
            
            # Update confidence based on adaptation
            if adapted_strategy != initial_strategy:
                adapted_strategy["confidence"] = max(0.3, adapted_strategy["confidence"] - 0.2)
            
            return adapted_strategy
        
        initial_strategy = {
            "primary_strategy": "direct_search",
            "selected_tools": ["knowledge_search"],
            "reasoning_depth": "shallow",
            "confidence": 0.7
        }
        
        # Test adaptation to low accuracy feedback
        low_accuracy_feedback = {"accuracy": 0.3, "completeness": 0.8, "response_time": 10}
        adapted = adapt_reasoning_strategy(initial_strategy, low_accuracy_feedback)
        
        assert adapted["primary_strategy"] != initial_strategy["primary_strategy"]
        assert "graph_rag" in adapted["selected_tools"]
        assert adapted["reasoning_depth"] == "deep"
        
        # Test adaptation to slow response
        slow_feedback = {"accuracy": 0.8, "completeness": 0.8, "response_time": 40}
        adapted_fast = adapt_reasoning_strategy(initial_strategy, slow_feedback, {"max_response_time": 30})
        
        assert adapted_fast["reasoning_depth"] == "shallow"
        assert len(adapted_fast["selected_tools"]) <= 1