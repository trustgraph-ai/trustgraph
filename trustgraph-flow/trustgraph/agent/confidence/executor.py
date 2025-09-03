"""
Executor Module

Handles individual plan step execution using registered tools.
Manages tool selection, error handling, and result transformation.
"""

import json
import asyncio
import logging
import time
from typing import Dict, Any, Optional, TYPE_CHECKING

from trustgraph.base import (
    TextCompletionClient,
    GraphRagClient, 
    ToolClient,
    PromptClient
)

from .types import ExecutionStep, StepResult, ContextEntry
from .confidence import ConfidenceEvaluator

if TYPE_CHECKING:
    from .memory import MemoryManager


class StepExecutor:
    """
    Executes individual execution steps using the appropriate tools.
    
    Tool Mapping:
    - GraphQuery → GraphRagClient
    - TextCompletion → TextCompletionClient  
    - McpTool → ToolClient
    - Prompt → PromptClient
    """
    
    def __init__(
        self, 
        text_completion_client: Optional[TextCompletionClient] = None,
        graph_rag_client: Optional[GraphRagClient] = None,
        tool_client: Optional[ToolClient] = None,
        prompt_client: Optional[PromptClient] = None
    ):
        self.logger = logging.getLogger(__name__)
        
        # Tool clients (will be injected by service)
        self.text_completion_client = text_completion_client
        self.graph_rag_client = graph_rag_client
        self.tool_client = tool_client
        self.prompt_client = prompt_client
        
        # Confidence evaluator
        self.confidence_evaluator = ConfidenceEvaluator()
    
    async def execute_step(
        self, 
        step: ExecutionStep, 
        context: Dict[str, Any], 
        memory_manager: "MemoryManager"
    ) -> StepResult:
        """
        Execute a single step with the given context.
        
        Args:
            step: The execution step to run
            context: Context data from memory manager
            memory_manager: Memory manager for storing results
            
        Returns:
            StepResult with execution outcome and confidence
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Executing step '{step.id}' with function '{step.function}'")
            
            # Execute the step based on function type
            output = await self._execute_function(step, context)
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Evaluate confidence
            confidence = self.confidence_evaluator.evaluate(
                function_name=step.function,
                arguments=step.arguments,
                output=output,
                execution_time_ms=execution_time_ms
            )
            
            # Create result
            result = StepResult(
                step_id=step.id,
                success=True,
                output=output,
                confidence=confidence,
                execution_time_ms=execution_time_ms
            )
            
            self.logger.info(
                f"Step '{step.id}' completed successfully "
                f"(confidence: {confidence.score:.2f}, time: {execution_time_ms}ms)"
            )
            
            return result
            
        except asyncio.TimeoutError:
            execution_time_ms = int((time.time() - start_time) * 1000)
            self.logger.error(f"Step '{step.id}' timed out after {execution_time_ms}ms")
            
            return StepResult(
                step_id=step.id,
                success=False,
                output=f"Execution timed out after {execution_time_ms}ms",
                confidence=self.confidence_evaluator._evaluate_generic(
                    "", step.arguments, execution_time_ms, 0
                ),
                execution_time_ms=execution_time_ms
            )
            
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Step execution failed: {str(e)}"
            self.logger.error(f"Step '{step.id}' failed: {error_msg}")
            
            return StepResult(
                step_id=step.id,
                success=False,
                output=error_msg,
                confidence=self.confidence_evaluator._evaluate_generic(
                    "", step.arguments, execution_time_ms, 0
                ),
                execution_time_ms=execution_time_ms
            )
    
    async def _execute_function(self, step: ExecutionStep, context: Dict[str, Any]) -> str:
        """
        Execute the specific function based on step type.
        
        Args:
            step: Execution step
            context: Available context data
            
        Returns:
            Raw output from function execution
        """
        function_name = step.function
        args = step.arguments
        timeout_seconds = step.timeout_ms / 1000.0
        
        # Substitute context variables in arguments
        resolved_args = self._resolve_arguments(args, context)
        
        if function_name == "GraphQuery":
            return await self._execute_graph_query(resolved_args, timeout_seconds)
        elif function_name == "TextCompletion":
            return await self._execute_text_completion(resolved_args, timeout_seconds)
        elif function_name == "McpTool":
            return await self._execute_mcp_tool(resolved_args, timeout_seconds)
        elif function_name == "Prompt":
            return await self._execute_prompt(resolved_args, timeout_seconds)
        else:
            raise ValueError(f"Unknown function type: {function_name}")
    
    async def _execute_graph_query(self, args: Dict[str, Any], timeout: float) -> str:
        """Execute graph query using GraphRagClient."""
        if not self.graph_rag_client:
            raise RuntimeError("GraphRagClient not configured")
        
        query = args.get("query", "")
        user = args.get("user", "trustgraph")
        collection = args.get("collection", "default")
        
        result = await self.graph_rag_client.rag(
            query=query, 
            user=user, 
            collection=collection,
            timeout=timeout
        )
        
        # Convert result to JSON string for consistent handling
        if isinstance(result, (dict, list)):
            return json.dumps(result)
        else:
            return str(result)
    
    async def _execute_text_completion(self, args: Dict[str, Any], timeout: float) -> str:
        """Execute text completion using TextCompletionClient."""
        if not self.text_completion_client:
            raise RuntimeError("TextCompletionClient not configured")
        
        system = args.get("system", "")
        prompt = args.get("prompt", "")
        
        result = await self.text_completion_client.text_completion(
            system=system,
            prompt=prompt,
            timeout=timeout
        )
        
        return str(result)
    
    async def _execute_mcp_tool(self, args: Dict[str, Any], timeout: float) -> str:
        """Execute MCP tool using ToolClient."""
        if not self.tool_client:
            raise RuntimeError("ToolClient not configured")
        
        name = args.get("name", "")
        parameters = args.get("parameters", {})
        
        result = await self.tool_client.invoke(
            name=name,
            parameters=parameters,
            timeout=timeout
        )
        
        # Convert result to string for consistent handling
        if isinstance(result, (dict, list)):
            return json.dumps(result)
        else:
            return str(result)
    
    async def _execute_prompt(self, args: Dict[str, Any], timeout: float) -> str:
        """Execute prompt using PromptClient."""
        if not self.prompt_client:
            raise RuntimeError("PromptClient not configured")
        
        # Note: This is a simplified implementation
        # The actual prompt client interface may differ
        prompt = args.get("prompt", "")
        
        # For now, delegate to text completion
        # In practice, this would use the prompt service
        if self.text_completion_client:
            result = await self.text_completion_client.text_completion(
                system="",
                prompt=prompt,
                timeout=timeout
            )
            return str(result)
        else:
            raise RuntimeError("No text completion client for prompt execution")
    
    def _resolve_arguments(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve context variables in step arguments.
        
        Supports simple variable substitution like {{variable_name}}.
        
        Args:
            args: Original arguments
            context: Available context variables
            
        Returns:
            Arguments with context variables resolved
        """
        resolved = {}
        
        for key, value in args.items():
            if isinstance(value, str):
                resolved[key] = self._substitute_variables(value, context)
            else:
                resolved[key] = value
        
        return resolved
    
    def _substitute_variables(self, text: str, context: Dict[str, Any]) -> str:
        """
        Substitute {{variable}} patterns with context values.
        
        Args:
            text: Text potentially containing variables
            context: Context dictionary
            
        Returns:
            Text with variables substituted
        """
        import re
        
        def replace_var(match):
            var_name = match.group(1)
            return str(context.get(var_name, f"{{{{{var_name}}}}}"))  # Keep original if not found
        
        # Replace {{variable}} patterns
        return re.sub(r'\{\{(\w+)\}\}', replace_var, text)
    
    def set_clients(
        self,
        text_completion_client: Optional[TextCompletionClient] = None,
        graph_rag_client: Optional[GraphRagClient] = None, 
        tool_client: Optional[ToolClient] = None,
        prompt_client: Optional[PromptClient] = None
    ) -> None:
        """
        Set tool clients (used by service for dependency injection).
        
        Args:
            text_completion_client: Text completion client
            graph_rag_client: Graph RAG client
            tool_client: MCP tool client  
            prompt_client: Prompt service client
        """
        if text_completion_client:
            self.text_completion_client = text_completion_client
        if graph_rag_client:
            self.graph_rag_client = graph_rag_client
        if tool_client:
            self.tool_client = tool_client
        if prompt_client:
            self.prompt_client = prompt_client
            
        self.logger.debug("Tool clients configured")