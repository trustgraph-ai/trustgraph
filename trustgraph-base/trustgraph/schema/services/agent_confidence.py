"""
Schema definitions for the confidence-based agent internal communication.

These schemas are used internally between confidence agent modules and are not
part of the external API. The confidence agent uses the existing AgentRequest
and AgentResponse schemas for external communication.
"""

from pulsar.schema import Record, String, Array, Map, Float, Integer, Boolean

############################################################################

# Confidence evaluation schemas

class ConfidenceMetrics(Record):
    """Confidence evaluation metrics for execution results."""
    score = Float()  # Confidence score (0.0 to 1.0)
    reasoning = String()  # Explanation of score calculation  
    retry_count = Integer()  # Number of retries attempted


class ExecutionStep(Record):
    """Individual step in an execution plan."""
    id = String()  # Unique step identifier
    function = String()  # Tool/function to execute
    arguments = Map(String())  # Arguments for the function
    dependencies = Array(String())  # IDs of prerequisite steps
    confidence_threshold = Float()  # Minimum acceptable confidence
    timeout_ms = Integer()  # Execution timeout


class ExecutionPlan(Record):
    """Complete execution plan with ordered steps."""
    id = String()  # Plan identifier
    steps = Array(ExecutionStep())  # Ordered execution steps
    context = Map(String())  # Global context for plan


class StepResult(Record):
    """Result of executing a single step."""
    step_id = String()  # Reference to ExecutionStep
    success = Boolean()  # Execution success status
    output = String()  # Step execution output
    confidence = ConfidenceMetrics()  # Confidence evaluation
    execution_time_ms = Integer()  # Actual execution time

############################################################################