"""
Internal type definitions for the confidence-based agent.

These types are used internally between confidence agent modules for
structured data flow, execution state, and metrics tracking.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum


@dataclass
class ConfidenceMetrics:
    """Confidence evaluation metrics for execution results."""
    
    score: float  # Confidence score (0.0 to 1.0)
    reasoning: str  # Explanation of score calculation
    retry_count: int  # Number of retries attempted


@dataclass
class ExecutionStep:
    """Individual step in an execution plan."""
    
    id: str  # Unique step identifier
    function: str  # Tool/function to execute
    arguments: Dict[str, Any]  # Arguments for the function
    dependencies: List[str]  # IDs of prerequisite steps
    confidence_threshold: float  # Minimum acceptable confidence
    timeout_ms: int  # Execution timeout


@dataclass
class ExecutionPlan:
    """Complete execution plan with ordered steps."""
    
    id: str  # Plan identifier
    steps: List[ExecutionStep]  # Ordered execution steps
    context: Dict[str, Any]  # Global context for plan


@dataclass
class StepResult:
    """Result of executing a single step."""
    
    step_id: str  # Reference to ExecutionStep
    success: bool  # Execution success status
    output: str  # Step execution output
    confidence: ConfidenceMetrics  # Confidence evaluation
    execution_time_ms: int  # Actual execution time


class ExecutionStatus(Enum):
    """Status of plan or step execution."""
    
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class PlanExecution:
    """Tracks execution state of an entire plan."""
    
    plan_id: str
    status: ExecutionStatus
    current_step: Optional[str]  # ID of currently executing step
    completed_steps: List[str]  # IDs of completed steps
    failed_steps: List[str]  # IDs of failed steps
    results: List[StepResult]  # All step results
    total_execution_time_ms: int
    
    
@dataclass
class AgentConfig:
    """Configuration for the confidence agent."""
    
    default_confidence_threshold: float = 0.75
    max_retries: int = 3
    retry_backoff_factor: float = 2.0
    override_enabled: bool = True
    step_timeout_ms: int = 30000
    parallel_execution: bool = False
    max_iterations: int = 15
    
    # Tool-specific thresholds
    tool_thresholds: Dict[str, float] = None
    
    def __post_init__(self):
        if self.tool_thresholds is None:
            self.tool_thresholds = {
                "GraphQuery": 0.8,
                "TextCompletion": 0.7, 
                "McpTool": 0.6,
                "Prompt": 0.7
            }


@dataclass
class ContextEntry:
    """Entry in the execution context/memory."""
    
    key: str
    value: Any
    step_id: str  # Step that created this entry
    timestamp: int  # Unix timestamp
    ttl_seconds: Optional[int] = None  # Time to live