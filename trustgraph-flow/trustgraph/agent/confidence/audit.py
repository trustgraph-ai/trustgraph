"""
Audit Logger Module

Provides structured audit logging for all confidence agent operations.
Records execution decisions, confidence scores, and complete audit trails.
"""

import json
import time
import logging
from typing import Dict, Any, Optional, TYPE_CHECKING

from .types import ExecutionPlan, ExecutionStep, StepResult, PlanExecution

if TYPE_CHECKING:
    pass


class AuditLogger:
    """
    Centralized audit logging for confidence agent operations.
    
    Records structured audit trails including:
    - Plan generation and validation
    - Step execution with confidence scores  
    - Retry decisions and reasoning
    - User overrides and manual interventions
    - Performance metrics and timing
    """
    
    def __init__(self, logger_name: str = "confidence_agent_audit"):
        # Create dedicated audit logger
        self.audit_logger = logging.getLogger(logger_name)
        self.audit_logger.setLevel(logging.INFO)
        
        # Prevent propagation to avoid duplication in main logs
        self.audit_logger.propagate = False
        
        # Add handler if not already present
        if not self.audit_logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - AUDIT - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.audit_logger.addHandler(handler)
        
        self.main_logger = logging.getLogger(__name__)
        
        # Track current execution context
        self.current_execution_id: Optional[str] = None
        self.execution_start_time: Optional[float] = None
    
    async def log_plan_start(self, plan: ExecutionPlan, execution: PlanExecution) -> None:
        """
        Log the start of plan execution.
        
        Args:
            plan: Execution plan being started
            execution: Plan execution state
        """
        self.current_execution_id = execution.plan_id
        self.execution_start_time = time.time()
        
        audit_entry = {
            "event": "plan_start",
            "execution_id": execution.plan_id,
            "timestamp": self._get_timestamp(),
            "plan": {
                "id": plan.id,
                "step_count": len(plan.steps),
                "steps": [
                    {
                        "id": step.id,
                        "function": step.function,
                        "dependencies": step.dependencies,
                        "confidence_threshold": step.confidence_threshold,
                        "timeout_ms": step.timeout_ms
                    }
                    for step in plan.steps
                ],
                "context": plan.context
            }
        }
        
        self.audit_logger.info(json.dumps(audit_entry))
        self.main_logger.debug(f"Audit: Plan '{plan.id}' execution started")
    
    async def log_plan_complete(self, plan: ExecutionPlan, execution: PlanExecution) -> None:
        """
        Log the completion of plan execution.
        
        Args:
            plan: Execution plan that completed
            execution: Final execution state
        """
        total_duration = 0
        if self.execution_start_time:
            total_duration = int((time.time() - self.execution_start_time) * 1000)
        
        # Calculate summary statistics
        successful_steps = len(execution.completed_steps)
        failed_steps = len(execution.failed_steps)
        total_retries = sum(r.confidence.retry_count for r in execution.results)
        
        avg_confidence = 0.0
        if execution.results:
            avg_confidence = sum(r.confidence.score for r in execution.results) / len(execution.results)
        
        audit_entry = {
            "event": "plan_complete",
            "execution_id": execution.plan_id,
            "timestamp": self._get_timestamp(),
            "status": execution.status.value,
            "duration_ms": total_duration,
            "summary": {
                "total_steps": len(plan.steps),
                "successful_steps": successful_steps,
                "failed_steps": failed_steps,
                "success_rate": successful_steps / len(plan.steps) if plan.steps else 0.0,
                "total_retries": total_retries,
                "average_confidence": avg_confidence
            },
            "completed_steps": execution.completed_steps,
            "failed_steps": execution.failed_steps
        }
        
        self.audit_logger.info(json.dumps(audit_entry))
        self.main_logger.debug(
            f"Audit: Plan '{plan.id}' completed with status {execution.status.value} "
            f"({successful_steps}/{len(plan.steps)} successful)"
        )
        
        # Clear execution context
        self.current_execution_id = None
        self.execution_start_time = None
    
    async def log_step_start(self, step: ExecutionStep, retry_count: int = 0) -> None:
        """
        Log the start of step execution.
        
        Args:
            step: Execution step being started
            retry_count: Current retry attempt number
        """
        audit_entry = {
            "event": "step_start",
            "execution_id": self.current_execution_id,
            "timestamp": self._get_timestamp(),
            "step": {
                "id": step.id,
                "function": step.function,
                "arguments": step.arguments,
                "dependencies": step.dependencies,
                "confidence_threshold": step.confidence_threshold,
                "timeout_ms": step.timeout_ms,
                "retry_count": retry_count
            }
        }
        
        self.audit_logger.info(json.dumps(audit_entry))
        
        if retry_count > 0:
            self.main_logger.debug(f"Audit: Step '{step.id}' retry {retry_count} started")
        else:
            self.main_logger.debug(f"Audit: Step '{step.id}' execution started")
    
    async def log_step_complete(self, step: ExecutionStep, result: StepResult) -> None:
        """
        Log the completion of step execution.
        
        Args:
            step: Execution step that completed
            result: Step execution result
        """
        audit_entry = {
            "event": "step_complete",
            "execution_id": self.current_execution_id,
            "timestamp": self._get_timestamp(),
            "step_id": step.id,
            "result": {
                "success": result.success,
                "confidence": {
                    "score": result.confidence.score,
                    "reasoning": result.confidence.reasoning,
                    "retry_count": result.confidence.retry_count,
                    "threshold": step.confidence_threshold,
                    "threshold_met": result.confidence.score >= step.confidence_threshold
                },
                "execution_time_ms": result.execution_time_ms,
                "output_length": len(result.output) if result.output else 0,
                "output_preview": result.output[:200] if result.output else ""
            }
        }
        
        self.audit_logger.info(json.dumps(audit_entry))
        self.main_logger.debug(
            f"Audit: Step '{step.id}' completed "
            f"(success: {result.success}, confidence: {result.confidence.score:.3f})"
        )
    
    async def log_retry_decision(
        self, 
        step: ExecutionStep, 
        result: StepResult, 
        retry_count: int,
        will_retry: bool,
        reason: str
    ) -> None:
        """
        Log retry decision making.
        
        Args:
            step: Step being retried
            result: Current step result
            retry_count: Current retry count
            will_retry: Whether step will be retried
            reason: Reason for retry decision
        """
        audit_entry = {
            "event": "retry_decision",
            "execution_id": self.current_execution_id,
            "timestamp": self._get_timestamp(),
            "step_id": step.id,
            "retry_count": retry_count,
            "will_retry": will_retry,
            "reason": reason,
            "current_result": {
                "success": result.success,
                "confidence_score": result.confidence.score,
                "confidence_threshold": step.confidence_threshold,
                "confidence_reasoning": result.confidence.reasoning
            }
        }
        
        self.audit_logger.info(json.dumps(audit_entry))
        self.main_logger.debug(
            f"Audit: Retry decision for step '{step.id}' - will_retry: {will_retry} ({reason})"
        )
    
    async def log_user_override(
        self, 
        step: ExecutionStep, 
        result: StepResult,
        override_granted: bool,
        override_reason: Optional[str] = None
    ) -> None:
        """
        Log user override decisions.
        
        Args:
            step: Step requiring override
            result: Step result with low confidence
            override_granted: Whether override was granted
            override_reason: Optional reason provided by user
        """
        audit_entry = {
            "event": "user_override",
            "execution_id": self.current_execution_id,
            "timestamp": self._get_timestamp(),
            "step_id": step.id,
            "override_granted": override_granted,
            "override_reason": override_reason,
            "trigger": {
                "confidence_score": result.confidence.score,
                "confidence_threshold": step.confidence_threshold,
                "confidence_reasoning": result.confidence.reasoning,
                "retry_count": result.confidence.retry_count
            }
        }
        
        self.audit_logger.info(json.dumps(audit_entry))
        self.main_logger.info(
            f"Audit: User override for step '{step.id}' - "
            f"{'GRANTED' if override_granted else 'DENIED'}"
        )
    
    async def log_error(self, context_id: str, error_message: str, error_details: Optional[Dict[str, Any]] = None) -> None:
        """
        Log errors during execution.
        
        Args:
            context_id: ID of step or plan where error occurred
            error_message: Error message
            error_details: Optional additional error details
        """
        audit_entry = {
            "event": "error",
            "execution_id": self.current_execution_id,
            "timestamp": self._get_timestamp(),
            "context_id": context_id,
            "error_message": error_message,
            "error_details": error_details or {}
        }
        
        self.audit_logger.error(json.dumps(audit_entry))
        self.main_logger.error(f"Audit: Error in {context_id} - {error_message}")
    
    async def log_confidence_analysis(
        self, 
        step_id: str, 
        function_name: str,
        confidence_factors: Dict[str, Any]
    ) -> None:
        """
        Log detailed confidence analysis for debugging.
        
        Args:
            step_id: ID of step being analyzed
            function_name: Function that was executed
            confidence_factors: Detailed confidence analysis factors
        """
        audit_entry = {
            "event": "confidence_analysis",
            "execution_id": self.current_execution_id,
            "timestamp": self._get_timestamp(),
            "step_id": step_id,
            "function_name": function_name,
            "confidence_factors": confidence_factors
        }
        
        self.audit_logger.debug(json.dumps(audit_entry))
    
    async def log_memory_operation(
        self, 
        operation: str, 
        key: str, 
        step_id: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log memory manager operations for debugging.
        
        Args:
            operation: Type of memory operation (store, retrieve, etc.)
            key: Memory key
            step_id: Step performing the operation
            details: Optional operation details
        """
        audit_entry = {
            "event": "memory_operation",
            "execution_id": self.current_execution_id,
            "timestamp": self._get_timestamp(),
            "operation": operation,
            "key": key,
            "step_id": step_id,
            "details": details or {}
        }
        
        self.audit_logger.debug(json.dumps(audit_entry))
    
    def _get_timestamp(self) -> str:
        """Get ISO format timestamp."""
        return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    
    def get_audit_summary(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Get audit summary for an execution (placeholder for future implementation).
        
        Args:
            execution_id: Execution ID to summarize
            
        Returns:
            Audit summary or None if not available
        """
        # In a full implementation, this would query stored audit logs
        # For Phase 1, this is a placeholder
        self.main_logger.debug(f"Audit summary requested for execution {execution_id}")
        return None
    
    def set_log_level(self, level: str) -> None:
        """
        Set audit logging level.
        
        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        numeric_level = getattr(logging, level.upper(), logging.INFO)
        self.audit_logger.setLevel(numeric_level)
        self.main_logger.debug(f"Audit log level set to {level}")
    
    def flush_logs(self) -> None:
        """Flush any buffered audit logs."""
        for handler in self.audit_logger.handlers:
            if hasattr(handler, 'flush'):
                handler.flush()