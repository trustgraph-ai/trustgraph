"""
Planner Module

Generates structured execution plans from user requests using an LLM.
Creates confidence-scored step sequences with appropriate tool combinations.
"""

import uuid
import json
import logging
from typing import Dict, Any, List, Optional, TYPE_CHECKING

from trustgraph.base import TextCompletionClient
from .types import ExecutionPlan, ExecutionStep, AgentConfig

if TYPE_CHECKING:
    pass


class PlanningError(Exception):
    """Exception raised when plan generation fails."""
    pass


class ExecutionPlanner:
    """
    Generates structured execution plans from natural language requests.
    
    Key Responsibilities:
    - Parse user requests into structured plans
    - Assign confidence thresholds based on operation criticality
    - Determine step dependencies
    - Select appropriate tool combinations
    """
    
    def __init__(self, text_completion_client: Optional[TextCompletionClient] = None):
        self.logger = logging.getLogger(__name__)
        self.text_completion_client = text_completion_client
        
        # Planning prompt template
        self.planning_prompt = """You are an AI planning assistant that converts user questions into structured execution plans.

Available tools and their capabilities:
- GraphQuery: Query knowledge graphs using natural language. Returns structured data about entities and relationships.
- TextCompletion: Generate text, analyze content, or answer questions using LLM capabilities.  
- McpTool: Execute external tools and APIs for specialized tasks.
- Prompt: Use pre-defined prompts for specific analysis tasks.

Given a user question, create an execution plan with the following structure:

{
  "steps": [
    {
      "id": "step-1", 
      "function": "GraphQuery|TextCompletion|McpTool|Prompt",
      "arguments": {"key": "value", "key2": "{{context_variable}}"},
      "dependencies": ["step-id1", "step-id2"],
      "confidence_threshold": 0.7,
      "timeout_ms": 30000,
      "reasoning": "Why this step is needed and what it accomplishes"
    }
  ],
  "context": {
    "user_question": "Original question",
    "approach": "High-level approach description"
  }
}

Important guidelines:
1. Use GraphQuery for factual information retrieval from knowledge graphs
2. Use TextCompletion for analysis, summarization, and text generation
3. Break complex tasks into logical steps with clear dependencies
4. Set higher confidence thresholds (0.8-0.9) for critical operations
5. Use context variables like {{step_1_output}} to pass data between steps
6. Keep steps focused and atomic - each step should do one thing well
7. Include reasoning for each step to explain its purpose

User Question: {question}

Generate the execution plan as JSON:"""
    
    async def generate_plan(
        self, 
        question: str, 
        config: AgentConfig,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> ExecutionPlan:
        """
        Generate an execution plan from a user question.
        
        Args:
            question: User's question or request
            config: Agent configuration with thresholds
            additional_context: Optional additional context
            
        Returns:
            ExecutionPlan with structured steps
            
        Raises:
            PlanningError: If plan generation fails
        """
        if not self.text_completion_client:
            raise PlanningError("TextCompletionClient not configured")
        
        try:
            self.logger.info(f"Generating execution plan for question: {question[:100]}...")
            
            # Format the planning prompt
            prompt = self.planning_prompt.format(question=question)
            
            # Get plan from LLM
            response = await self.text_completion_client.text_completion(
                system="You are a precise AI planning assistant. Always respond with valid JSON only.",
                prompt=prompt,
                timeout=30
            )
            
            # Parse the response
            plan_data = self._parse_plan_response(response)
            
            # Create ExecutionPlan object
            plan = self._create_execution_plan(plan_data, config)
            
            self.logger.info(f"Generated plan '{plan.id}' with {len(plan.steps)} steps")
            return plan
            
        except Exception as e:
            error_msg = f"Failed to generate execution plan: {str(e)}"
            self.logger.error(error_msg)
            raise PlanningError(error_msg)
    
    def _parse_plan_response(self, response: str) -> Dict[str, Any]:
        """
        Parse LLM response into plan data structure.
        
        Args:
            response: Raw response from LLM
            
        Returns:
            Parsed plan data
            
        Raises:
            PlanningError: If parsing fails
        """
        try:
            # Try to extract JSON from response
            response = response.strip()
            
            # Handle cases where LLM adds extra text
            if not response.startswith('{'):
                # Look for JSON block
                start = response.find('{')
                end = response.rfind('}') + 1
                if start != -1 and end > start:
                    response = response[start:end]
                else:
                    raise ValueError("No JSON found in response")
            
            plan_data = json.loads(response)
            
            # Validate required fields
            if "steps" not in plan_data:
                raise ValueError("Missing 'steps' field in plan")
            
            if not isinstance(plan_data["steps"], list):
                raise ValueError("'steps' must be a list")
            
            return plan_data
            
        except json.JSONDecodeError as e:
            raise PlanningError(f"Invalid JSON in plan response: {e}")
        except ValueError as e:
            raise PlanningError(f"Invalid plan structure: {e}")
    
    def _create_execution_plan(
        self, 
        plan_data: Dict[str, Any], 
        config: AgentConfig
    ) -> ExecutionPlan:
        """
        Create ExecutionPlan object from parsed plan data.
        
        Args:
            plan_data: Parsed plan data from LLM
            config: Agent configuration
            
        Returns:
            ExecutionPlan object
        """
        plan_id = str(uuid.uuid4())
        steps = []
        
        for step_data in plan_data["steps"]:
            step = self._create_execution_step(step_data, config)
            steps.append(step)
        
        # Get context, defaulting to empty dict
        context = plan_data.get("context", {})
        
        return ExecutionPlan(
            id=plan_id,
            steps=steps,
            context=context
        )
    
    def _create_execution_step(
        self, 
        step_data: Dict[str, Any], 
        config: AgentConfig
    ) -> ExecutionStep:
        """
        Create ExecutionStep object from step data.
        
        Args:
            step_data: Step data from plan
            config: Agent configuration
            
        Returns:
            ExecutionStep object
        """
        # Required fields
        step_id = step_data.get("id", str(uuid.uuid4()))
        function = step_data.get("function", "")
        arguments = step_data.get("arguments", {})
        
        # Optional fields with defaults
        dependencies = step_data.get("dependencies", [])
        
        # Get confidence threshold - use function-specific or default
        confidence_threshold = step_data.get("confidence_threshold")
        if confidence_threshold is None:
            confidence_threshold = config.tool_thresholds.get(
                function, 
                config.default_confidence_threshold
            )
        
        timeout_ms = step_data.get("timeout_ms", config.step_timeout_ms)
        
        return ExecutionStep(
            id=step_id,
            function=function,
            arguments=arguments,
            dependencies=dependencies,
            confidence_threshold=confidence_threshold,
            timeout_ms=timeout_ms
        )
    
    def create_simple_plan(
        self, 
        function: str, 
        arguments: Dict[str, Any], 
        config: AgentConfig
    ) -> ExecutionPlan:
        """
        Create a simple single-step plan programmatically.
        
        Useful for testing or simple operations.
        
        Args:
            function: Function name to execute
            arguments: Function arguments
            config: Agent configuration
            
        Returns:
            ExecutionPlan with single step
        """
        step = ExecutionStep(
            id="step-1",
            function=function,
            arguments=arguments,
            dependencies=[],
            confidence_threshold=config.tool_thresholds.get(
                function, config.default_confidence_threshold
            ),
            timeout_ms=config.step_timeout_ms
        )
        
        plan = ExecutionPlan(
            id=str(uuid.uuid4()),
            steps=[step],
            context={
                "approach": f"Single {function} execution",
                "generated_by": "create_simple_plan"
            }
        )
        
        self.logger.debug(f"Created simple plan for {function}")
        return plan
    
    def validate_plan(self, plan: ExecutionPlan) -> List[str]:
        """
        Validate an execution plan for common issues.
        
        Args:
            plan: Plan to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if not plan.steps:
            errors.append("Plan has no steps")
            return errors
        
        step_ids = {step.id for step in plan.steps}
        
        for step in plan.steps:
            # Check step has required fields
            if not step.id:
                errors.append("Step missing ID")
            if not step.function:
                errors.append(f"Step '{step.id}' missing function")
            
            # Check dependencies exist
            for dep_id in step.dependencies:
                if dep_id not in step_ids:
                    errors.append(f"Step '{step.id}' depends on non-existent step '{dep_id}'")
            
            # Check for circular dependencies (basic check)
            if step.id in step.dependencies:
                errors.append(f"Step '{step.id}' has circular dependency on itself")
            
            # Validate confidence threshold
            if not (0.0 <= step.confidence_threshold <= 1.0):
                errors.append(f"Step '{step.id}' has invalid confidence threshold: {step.confidence_threshold}")
            
            # Validate timeout
            if step.timeout_ms <= 0:
                errors.append(f"Step '{step.id}' has invalid timeout: {step.timeout_ms}")
        
        return errors
    
    def set_text_completion_client(self, client: TextCompletionClient) -> None:
        """Set the text completion client (dependency injection)."""
        self.text_completion_client = client
        self.logger.debug("TextCompletionClient configured for planner")