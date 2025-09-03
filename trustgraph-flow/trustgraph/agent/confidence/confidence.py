"""
Confidence Evaluator Module

Calculates confidence scores for execution results based on multiple factors
to ensure reliability and guide retry decisions.
"""

import json
import logging
from typing import Dict, Any, Optional
from .types import ConfidenceMetrics


class ConfidenceEvaluator:
    """
    Evaluates confidence scores for tool execution results.
    
    Uses multiple scoring factors:
    - Graph query result size and consistency  
    - Entity extraction precision scores
    - Vector search similarity thresholds
    - LLM response coherence metrics
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Default scoring weights
        self.weights = {
            "output_completeness": 0.3,
            "structure_validity": 0.2, 
            "semantic_coherence": 0.2,
            "result_size": 0.2,
            "error_indicators": 0.1
        }
    
    def evaluate(
        self, 
        function_name: str,
        arguments: Dict[str, Any],
        output: str,
        execution_time_ms: int,
        retry_count: int = 0
    ) -> ConfidenceMetrics:
        """
        Evaluate confidence score for execution result.
        
        Args:
            function_name: Name of the function/tool executed
            arguments: Arguments passed to the function
            output: Raw output from function execution
            execution_time_ms: Time taken for execution
            retry_count: Number of retries attempted
            
        Returns:
            ConfidenceMetrics with score, reasoning, and retry count
        """
        # Function-specific confidence evaluation
        if function_name == "GraphQuery":
            return self._evaluate_graph_query(output, arguments, execution_time_ms, retry_count)
        elif function_name == "TextCompletion":
            return self._evaluate_text_completion(output, arguments, execution_time_ms, retry_count)
        elif function_name == "McpTool":
            return self._evaluate_mcp_tool(output, arguments, execution_time_ms, retry_count)
        elif function_name == "Prompt":
            return self._evaluate_prompt(output, arguments, execution_time_ms, retry_count)
        else:
            return self._evaluate_generic(output, arguments, execution_time_ms, retry_count)
    
    def _evaluate_graph_query(
        self, 
        output: str, 
        arguments: Dict[str, Any], 
        execution_time_ms: int,
        retry_count: int
    ) -> ConfidenceMetrics:
        """Evaluate confidence for graph query results."""
        
        score = 0.5  # Base score
        reasons = []
        
        try:
            # Try to parse as JSON result
            if output.strip():
                try:
                    result = json.loads(output)
                    if isinstance(result, list):
                        result_count = len(result)
                        
                        if result_count == 0:
                            score = 0.3
                            reasons.append("Empty result set - may indicate query issues")
                        elif result_count > 0 and result_count < 1000:
                            score = 0.8 + min(0.15, result_count / 100 * 0.1)
                            reasons.append(f"Good result size: {result_count} items")
                        else:
                            score = 0.7
                            reasons.append(f"Large result set: {result_count} items")
                            
                    elif isinstance(result, dict):
                        if result:
                            score = 0.85
                            reasons.append("Structured result with data")
                        else:
                            score = 0.4
                            reasons.append("Empty structured result")
                    else:
                        score = 0.75
                        reasons.append("Valid structured response")
                        
                except json.JSONDecodeError:
                    # Not JSON, treat as text response
                    if len(output.strip()) > 0:
                        score = 0.6
                        reasons.append("Non-JSON response with content")
                    else:
                        score = 0.2
                        reasons.append("Empty text response")
            else:
                score = 0.2
                reasons.append("No output returned")
                
        except Exception as e:
            score = 0.3
            reasons.append(f"Error evaluating output: {str(e)}")
        
        # Adjust for execution time (very fast might indicate cached/empty result)
        if execution_time_ms < 100:
            score *= 0.9
            reasons.append("Very fast execution - possible empty result")
        elif execution_time_ms > 30000:
            score *= 0.85  
            reasons.append("Slow execution - possible complexity issues")
        
        # Penalty for retries
        score *= (0.9 ** retry_count)
        if retry_count > 0:
            reasons.append(f"Retry penalty applied ({retry_count} retries)")
        
        return ConfidenceMetrics(
            score=max(0.0, min(1.0, score)),
            reasoning="; ".join(reasons),
            retry_count=retry_count
        )
    
    def _evaluate_text_completion(
        self, 
        output: str, 
        arguments: Dict[str, Any], 
        execution_time_ms: int,
        retry_count: int
    ) -> ConfidenceMetrics:
        """Evaluate confidence for text completion results."""
        
        score = 0.5
        reasons = []
        
        if not output or not output.strip():
            score = 0.1
            reasons.append("Empty response")
        else:
            text = output.strip()
            
            # Basic coherence checks
            if len(text) < 10:
                score = 0.4
                reasons.append("Very short response")
            elif len(text) > 10000:
                score = 0.6
                reasons.append("Very long response - may contain hallucinations")
            else:
                score = 0.75
                reasons.append("Reasonable response length")
            
            # Check for common error patterns
            error_patterns = [
                "i don't know",
                "i cannot",
                "i'm unable to",
                "error:",
                "failed to",
                "sorry, i"
            ]
            
            text_lower = text.lower()
            error_found = any(pattern in text_lower for pattern in error_patterns)
            
            if error_found:
                score = 0.5
                reasons.append("Response indicates uncertainty or error")
            else:
                score += 0.1
                reasons.append("No obvious error indicators")
            
            # Check for structure (sentences, paragraphs)
            sentences = text.count('.') + text.count('!') + text.count('?')
            if sentences >= 2:
                score += 0.05
                reasons.append("Well-structured response")
        
        # Execution time considerations
        if execution_time_ms < 500:
            score *= 0.95
            reasons.append("Very fast completion")
        elif execution_time_ms > 45000:
            score *= 0.9
            reasons.append("Slow completion")
        
        # Retry penalty
        score *= (0.85 ** retry_count)
        if retry_count > 0:
            reasons.append(f"Retry penalty applied ({retry_count} retries)")
            
        return ConfidenceMetrics(
            score=max(0.0, min(1.0, score)),
            reasoning="; ".join(reasons), 
            retry_count=retry_count
        )
    
    def _evaluate_mcp_tool(
        self, 
        output: str, 
        arguments: Dict[str, Any], 
        execution_time_ms: int,
        retry_count: int
    ) -> ConfidenceMetrics:
        """Evaluate confidence for MCP tool results."""
        
        score = 0.6  # Default for tools
        reasons = []
        
        if not output:
            score = 0.3
            reasons.append("No tool output")
        else:
            try:
                # Try to parse tool result
                result = json.loads(output)
                if isinstance(result, dict) and "error" in result:
                    score = 0.2
                    reasons.append("Tool returned error")
                elif isinstance(result, dict) and result.get("success", True):
                    score = 0.8
                    reasons.append("Tool execution successful")
                else:
                    score = 0.65
                    reasons.append("Tool returned result")
            except json.JSONDecodeError:
                if "error" in output.lower() or "failed" in output.lower():
                    score = 0.3
                    reasons.append("Error indicated in output")
                else:
                    score = 0.7
                    reasons.append("Text output from tool")
        
        # Time-based adjustments
        if execution_time_ms > 60000:
            score *= 0.8
            reasons.append("Tool execution timeout risk")
        
        # Retry penalty
        score *= (0.8 ** retry_count)
        if retry_count > 0:
            reasons.append(f"Retry penalty applied ({retry_count} retries)")
        
        return ConfidenceMetrics(
            score=max(0.0, min(1.0, score)),
            reasoning="; ".join(reasons),
            retry_count=retry_count
        )
    
    def _evaluate_prompt(
        self, 
        output: str, 
        arguments: Dict[str, Any], 
        execution_time_ms: int,
        retry_count: int
    ) -> ConfidenceMetrics:
        """Evaluate confidence for prompt service results."""
        
        # Similar to text completion but with prompt-specific logic
        return self._evaluate_text_completion(output, arguments, execution_time_ms, retry_count)
    
    def _evaluate_generic(
        self, 
        output: str, 
        arguments: Dict[str, Any], 
        execution_time_ms: int,
        retry_count: int
    ) -> ConfidenceMetrics:
        """Generic confidence evaluation for unknown functions."""
        
        score = 0.5
        reasons = ["Generic evaluation for unknown function"]
        
        if output and len(output.strip()) > 0:
            score = 0.6
            reasons.append("Function returned output")
        else:
            score = 0.3
            reasons.append("No output from function")
        
        # Retry penalty
        score *= (0.9 ** retry_count)
        if retry_count > 0:
            reasons.append(f"Retry penalty applied ({retry_count} retries)")
        
        return ConfidenceMetrics(
            score=max(0.0, min(1.0, score)),
            reasoning="; ".join(reasons),
            retry_count=retry_count
        )