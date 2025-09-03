"""
Confidence Agent Service

Main service class that coordinates all confidence agent components
and handles request/response flow through the Pulsar message bus.
"""

import json
import logging
import functools
from typing import Dict, Any, Optional, Callable

from trustgraph.base import (
    AgentService, 
    TextCompletionClientSpec, 
    GraphRagClientSpec,
    ToolClientSpec,
    PromptClientSpec
)
from trustgraph.schema import AgentRequest, AgentResponse, Error

from .types import AgentConfig
from .planner import ExecutionPlanner, PlanningError
from .flow_controller import FlowController, FlowControlError
from .memory import MemoryManager
from .executor import StepExecutor
from .audit import AuditLogger

# Module logger
logger = logging.getLogger(__name__)

default_ident = "confidence-agent"
default_max_iterations = 15


class ConfidenceAgentService(AgentService):
    """
    Main service class for the confidence-based agent.
    
    Service Workflow:
    1. Generate execution plan via Planner Module
    2. Execute plan with confidence control via Flow Controller
    3. Generate response with confidence metrics and audit trail
    
    Uses existing AgentRequest and AgentResponse schemas for compatibility.
    """
    
    def __init__(self, **params):
        id = params.get("id", default_ident)
        
        # Extract configuration parameters
        self.max_iterations = int(params.get("max_iterations", default_max_iterations))
        self.confidence_threshold = float(params.get("confidence_threshold", 0.75))
        self.max_retries = int(params.get("max_retries", 3))
        self.retry_backoff_factor = float(params.get("retry_backoff_factor", 2.0))
        self.override_enabled = bool(params.get("override_enabled", True))
        self.step_timeout_ms = int(params.get("step_timeout_ms", 30000))
        self.parallel_execution = bool(params.get("parallel_execution", False))
        
        # Tool-specific thresholds
        self.graph_query_threshold = float(params.get("graph_query_threshold", 0.8))
        self.text_completion_threshold = float(params.get("text_completion_threshold", 0.7))
        self.mcp_tool_threshold = float(params.get("mcp_tool_threshold", 0.6))
        
        # Create agent configuration
        self.config = AgentConfig(
            default_confidence_threshold=self.confidence_threshold,
            max_retries=self.max_retries,
            retry_backoff_factor=self.retry_backoff_factor,
            override_enabled=self.override_enabled,
            step_timeout_ms=self.step_timeout_ms,
            parallel_execution=self.parallel_execution,
            max_iterations=self.max_iterations,
            tool_thresholds={
                "GraphQuery": self.graph_query_threshold,
                "TextCompletion": self.text_completion_threshold,
                "McpTool": self.mcp_tool_threshold,
                "Prompt": self.text_completion_threshold
            }
        )
        
        super(ConfidenceAgentService, self).__init__(**params | {"id": id})
        
        # Initialize core modules
        self.memory_manager = MemoryManager()
        self.executor = StepExecutor()
        self.planner = ExecutionPlanner()
        self.flow_controller = FlowController(self.config)
        self.audit_logger = AuditLogger()
        
        # Set up flow controller callbacks
        self.flow_controller.set_override_callback(self._request_user_override)
        self.flow_controller.set_progress_callback(self._handle_progress_update)
        
        # Track current request for callbacks
        self._current_respond_callback: Optional[Callable] = None
        
        # Register client specifications
        self.register_specification(
            TextCompletionClientSpec(
                request_name="text-completion-request",
                response_name="text-completion-response",
            )
        )
        
        self.register_specification(
            GraphRagClientSpec(
                request_name="graph-rag-request", 
                response_name="graph-rag-response",
            )
        )
        
        self.register_specification(
            ToolClientSpec(
                request_name="mcp-tool-request",
                response_name="mcp-tool-response",
            )
        )
        
        self.register_specification(
            PromptClientSpec(
                request_name="prompt-request",
                response_name="prompt-response",
            )
        )
        
        logger.info(f"ConfidenceAgentService initialized with config: {self.config.__dict__}")
    
    async def agent_request(self, request, respond, next, flow):
        """
        Process an agent request with confidence-based execution.
        
        Args:
            request: AgentRequest message
            respond: Response callback function
            next: Next request callback (for chaining)
            flow: Flow context
        """
        self._current_respond_callback = respond
        
        try:
            logger.info(f"Processing confidence agent request: {request.question[:100]}...")
            
            # Parse plan overrides from request if provided
            plan_overrides = self._parse_plan_overrides(request.plan)
            if plan_overrides:
                logger.debug(f"Plan overrides: {plan_overrides}")
            
            # Clear previous context
            self.memory_manager.clear_context()
            
            # Set up tool clients
            self._configure_tool_clients(flow)
            
            # Send planning thought
            await self._send_thought(respond, "Creating execution plan with confidence thresholds")
            
            # Generate execution plan
            planner = self.planner
            try:
                plan = await planner.generate_plan(
                    request.question,
                    self.config,
                    additional_context=plan_overrides
                )
                
                # Validate plan
                validation_errors = planner.validate_plan(plan)
                if validation_errors:
                    error_msg = f"Plan validation failed: {'; '.join(validation_errors)}"
                    logger.error(error_msg)
                    await self._send_error(respond, error_msg)
                    return
                
                await self._send_observation(
                    respond, 
                    f"Plan generated: {len(plan.steps)} steps with confidence thresholds"
                )
                
            except PlanningError as e:
                error_msg = f"Plan generation failed: {str(e)}"
                logger.error(error_msg)
                await self._send_error(respond, error_msg)
                return
            
            # Execute the plan
            try:
                await self._send_thought(respond, "Executing plan with confidence-based control")
                
                execution = await self.flow_controller.execute_plan(
                    plan,
                    self.memory_manager,
                    self.executor,
                    self.audit_logger
                )
                
                # Generate final response based on execution results
                final_answer = self._generate_final_answer(plan, execution, request.question)
                
                # Send final response
                await self._send_final_answer(respond, final_answer, execution)
                
            except FlowControlError as e:
                error_msg = f"Plan execution failed: {str(e)}"
                logger.error(error_msg)
                await self._send_error(respond, error_msg)
                return
                
        except Exception as e:
            error_msg = f"Unexpected error in confidence agent: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await self._send_error(respond, error_msg)
        
        finally:
            self._current_respond_callback = None
    
    def _configure_tool_clients(self, flow):
        """Configure tool clients from flow context."""
        
        # Get clients from flow context
        text_completion_client = getattr(flow, 'text_completion_client', None)
        graph_rag_client = getattr(flow, 'graph_rag_client', None)
        tool_client = getattr(flow, 'tool_client', None)
        prompt_client = getattr(flow, 'prompt_client', None)
        
        # Configure executor
        self.executor.set_clients(
            text_completion_client=text_completion_client,
            graph_rag_client=graph_rag_client,
            tool_client=tool_client,
            prompt_client=prompt_client
        )
        
        # Configure planner
        if text_completion_client:
            self.planner.set_text_completion_client(text_completion_client)
    
    def _parse_plan_overrides(self, plan_str: str) -> Optional[Dict[str, Any]]:
        """Parse plan overrides from request.plan field."""
        if not plan_str or not plan_str.strip():
            return None
        
        try:
            return json.loads(plan_str)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in plan field: {plan_str}")
            return None
    
    def _generate_final_answer(self, plan, execution, original_question: str) -> str:
        """Generate final answer from execution results."""
        
        if not execution.results:
            return "No results were generated."
        
        # Get the last successful result as the primary answer
        successful_results = [r for r in execution.results if r.success]
        
        if not successful_results:
            return "All execution steps failed. Please try rephrasing your question."
        
        # Use the output from the last successful step
        primary_result = successful_results[-1]
        answer = primary_result.output
        
        # If the result looks like JSON, try to make it more readable
        try:
            parsed = json.loads(answer)
            if isinstance(parsed, list) and len(parsed) > 0:
                if len(parsed) == 1:
                    answer = f"Found 1 result: {json.dumps(parsed[0], indent=2)}"
                else:
                    answer = f"Found {len(parsed)} results:\n" + "\n".join([
                        f"{i+1}. {json.dumps(item, indent=2)}" 
                        for i, item in enumerate(parsed[:3])
                    ])
                    if len(parsed) > 3:
                        answer += f"\n... and {len(parsed) - 3} more results"
            elif isinstance(parsed, dict):
                answer = json.dumps(parsed, indent=2)
        except json.JSONDecodeError:
            # Keep original answer if not JSON
            pass
        
        return answer
    
    async def _send_thought(self, respond, thought: str):
        """Send a thought response."""
        response = AgentResponse(
            answer="",
            error=None,
            thought=thought,
            observation=""
        )
        await respond(response)
    
    async def _send_observation(self, respond, observation: str):
        """Send an observation response."""
        response = AgentResponse(
            answer="",
            error=None,
            thought="",
            observation=observation
        )
        await respond(response)
    
    async def _send_final_answer(self, respond, answer: str, execution):
        """Send the final answer with confidence information."""
        
        # Calculate overall confidence
        avg_confidence = 0.0
        if execution.results:
            avg_confidence = sum(r.confidence.score for r in execution.results) / len(execution.results)
        
        # Create final thought with confidence summary
        final_thought = (
            f"Analysis complete with average confidence {avg_confidence:.2f} "
            f"({len(execution.completed_steps)}/{len(execution.results)} steps successful)"
        )
        
        response = AgentResponse(
            answer=answer,
            error=None,
            thought=final_thought,
            observation=""
        )
        await respond(response)
    
    async def _send_error(self, respond, error_message: str):
        """Send an error response."""
        response = AgentResponse(
            answer="",
            error=Error(message=error_message),
            thought="",
            observation=""
        )
        await respond(response)
    
    def _request_user_override(self, message: str, result) -> bool:
        """
        Request user override for low confidence results.
        
        For Phase 1, this automatically denies overrides.
        In Phase 2, this could integrate with UI for user input.
        """
        logger.info(f"User override requested: {message}")
        
        # For Phase 1, automatically deny overrides
        # In Phase 2, this could send a special response asking for user input
        return False
    
    async def _handle_progress_update(self, event_type: str, result):
        """Handle progress updates from flow controller."""
        if not self._current_respond_callback:
            return
        
        try:
            if event_type == "step_success":
                observation = (
                    f"Step '{result.step_id}' completed successfully "
                    f"(confidence: {result.confidence.score:.2f})"
                )
                await self._send_observation(self._current_respond_callback, observation)
            elif event_type == "step_retry":
                thought = f"Retrying step '{result.step_id}' - confidence too low"
                await self._send_thought(self._current_respond_callback, thought)
        except Exception as e:
            logger.warning(f"Error sending progress update: {e}")


# Create the main processor class for service registration  
class Processor(ConfidenceAgentService):
    """Main processor class for service registration."""
    pass