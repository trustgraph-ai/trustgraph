"""
Flow Controller Module

Orchestrates plan execution with confidence-based control flow.
Manages step dependencies, retry logic, and user overrides.
"""

import asyncio
import logging
import time
from typing import List, Dict, Set, Optional, Callable, Any, TYPE_CHECKING

from .types import (
    ExecutionPlan, ExecutionStep, StepResult, ExecutionStatus,
    PlanExecution, AgentConfig, ConfidenceMetrics
)

if TYPE_CHECKING:
    from .memory import MemoryManager
    from .executor import StepExecutor
    from .audit import AuditLogger


class FlowControlError(Exception):
    """Exception raised when flow control encounters unrecoverable errors."""
    pass


class FlowController:
    """
    Orchestrates execution plan flow with confidence-based control.
    
    Key Capabilities:
    - Step dependency resolution
    - Confidence-based retry logic  
    - User override handling
    - Graceful failure modes
    """
    
    def __init__(self, config: AgentConfig):
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # Callback for requesting user overrides (set by service)
        self.override_callback: Optional[Callable[[str, StepResult], bool]] = None
        
        # Callback for progress updates (set by service)
        self.progress_callback: Optional[Callable[[str, StepResult], None]] = None
    
    async def execute_plan(
        self,
        plan: ExecutionPlan,
        memory_manager: "MemoryManager", 
        executor: "StepExecutor",
        audit_logger: Optional["AuditLogger"] = None
    ) -> PlanExecution:
        """
        Execute a complete execution plan with confidence control.
        
        Args:
            plan: Execution plan to run
            memory_manager: Memory manager for context
            executor: Step executor
            audit_logger: Optional audit logger
            
        Returns:
            PlanExecution with results and status
        """
        start_time = time.time()
        
        # Initialize plan execution tracking
        execution = PlanExecution(
            plan_id=plan.id,
            status=ExecutionStatus.IN_PROGRESS,
            current_step=None,
            completed_steps=[],
            failed_steps=[],
            results=[],
            total_execution_time_ms=0
        )
        
        try:
            self.logger.info(f"Starting execution of plan '{plan.id}' with {len(plan.steps)} steps")
            
            if audit_logger:
                await audit_logger.log_plan_start(plan, execution)
            
            # Build dependency graph
            self._register_dependencies(plan, memory_manager)
            
            # Execute steps with dependency resolution
            if self.config.parallel_execution:
                await self._execute_parallel(plan, execution, memory_manager, executor, audit_logger)
            else:
                await self._execute_sequential(plan, execution, memory_manager, executor, audit_logger)
            
            # Final status determination
            if execution.failed_steps:
                execution.status = ExecutionStatus.FAILED
            else:
                execution.status = ExecutionStatus.COMPLETED
            
            execution.total_execution_time_ms = int((time.time() - start_time) * 1000)
            
            self.logger.info(
                f"Plan '{plan.id}' execution completed: {execution.status.value} "
                f"({len(execution.completed_steps)}/{len(plan.steps)} steps, "
                f"{execution.total_execution_time_ms}ms)"
            )
            
            if audit_logger:
                await audit_logger.log_plan_complete(plan, execution)
                
            return execution
            
        except Exception as e:
            execution.status = ExecutionStatus.FAILED
            execution.total_execution_time_ms = int((time.time() - start_time) * 1000)
            
            error_msg = f"Plan execution failed: {str(e)}"
            self.logger.error(error_msg)
            
            if audit_logger:
                await audit_logger.log_error(plan.id, error_msg)
            
            raise FlowControlError(error_msg)
    
    async def _execute_sequential(
        self,
        plan: ExecutionPlan,
        execution: PlanExecution,
        memory_manager: "MemoryManager",
        executor: "StepExecutor", 
        audit_logger: Optional["AuditLogger"]
    ) -> None:
        """Execute steps sequentially with dependency resolution."""
        
        remaining_steps = set(step.id for step in plan.steps)
        
        while remaining_steps:
            # Get steps ready to execute (dependencies satisfied)
            ready_steps = memory_manager.get_ready_steps(
                [step for step in plan.steps if step.id in remaining_steps],
                set(execution.completed_steps)
            )
            
            if not ready_steps:
                # Check if we're stuck (circular dependencies or failed dependencies)
                if execution.failed_steps:
                    self.logger.warning("Cannot proceed - some steps failed and others depend on them")
                    break
                else:
                    raise FlowControlError("Circular dependency detected - no steps can proceed")
            
            # Execute ready steps one by one
            for step in ready_steps:
                await self._execute_single_step(step, execution, memory_manager, executor, audit_logger)
                remaining_steps.discard(step.id)
    
    async def _execute_parallel(
        self,
        plan: ExecutionPlan,
        execution: PlanExecution,
        memory_manager: "MemoryManager",
        executor: "StepExecutor",
        audit_logger: Optional["AuditLogger"]
    ) -> None:
        """Execute steps in parallel where possible (Phase 2 feature)."""
        # For now, fall back to sequential - parallel execution is Phase 2
        await self._execute_sequential(plan, execution, memory_manager, executor, audit_logger)
    
    async def _execute_single_step(
        self,
        step: ExecutionStep,
        execution: PlanExecution,
        memory_manager: "MemoryManager",
        executor: "StepExecutor",
        audit_logger: Optional["AuditLogger"]
    ) -> None:
        """
        Execute a single step with retry logic and confidence control.
        
        Args:
            step: Step to execute
            execution: Plan execution state
            memory_manager: Memory manager
            executor: Step executor
            audit_logger: Optional audit logger
        """
        execution.current_step = step.id
        retry_count = 0
        
        while retry_count <= self.config.max_retries:
            try:
                self.logger.info(f"Executing step '{step.id}' (attempt {retry_count + 1})")
                
                if audit_logger:
                    await audit_logger.log_step_start(step, retry_count)
                
                # Get context for this step
                context = memory_manager.get_context_for_step(step)
                
                # Execute the step
                result = await executor.execute_step(step, context, memory_manager)
                
                # Update confidence with retry count
                result.confidence.retry_count = retry_count
                
                # Store result
                execution.results.append(result)
                memory_manager.store_step_result(result)
                
                if audit_logger:
                    await audit_logger.log_step_complete(step, result)
                
                # Check confidence against threshold
                confidence_ok = result.confidence.score >= step.confidence_threshold
                
                if result.success and confidence_ok:
                    # Step succeeded with good confidence
                    execution.completed_steps.append(step.id)
                    self.logger.info(
                        f"Step '{step.id}' completed successfully "
                        f"(confidence: {result.confidence.score:.3f})"
                    )
                    
                    # Notify progress callback
                    if self.progress_callback:
                        try:
                            self.progress_callback("step_success", result)
                        except Exception as e:
                            self.logger.warning(f"Progress callback error: {e}")
                    
                    break
                    
                elif result.success and not confidence_ok:
                    # Step succeeded but confidence too low
                    self.logger.warning(
                        f"Step '{step.id}' succeeded but confidence too low "
                        f"({result.confidence.score:.3f} < {step.confidence_threshold})"
                    )
                    
                    if retry_count < self.config.max_retries:
                        # Retry with backoff
                        backoff_delay = self.config.retry_backoff_factor ** retry_count
                        self.logger.info(f"Retrying step '{step.id}' after {backoff_delay}s backoff")
                        await asyncio.sleep(backoff_delay)
                        retry_count += 1
                        continue
                    else:
                        # Max retries reached - check for user override
                        if await self._handle_low_confidence(step, result):
                            execution.completed_steps.append(step.id)
                            self.logger.info(f"Step '{step.id}' accepted via user override")
                            break
                        else:
                            execution.failed_steps.append(step.id)
                            self.logger.error(f"Step '{step.id}' failed - low confidence after retries")
                            break
                
                else:
                    # Step execution failed
                    self.logger.warning(f"Step '{step.id}' execution failed: {result.output}")
                    
                    if retry_count < self.config.max_retries:
                        # Retry with backoff
                        backoff_delay = self.config.retry_backoff_factor ** retry_count
                        self.logger.info(f"Retrying failed step '{step.id}' after {backoff_delay}s backoff")
                        await asyncio.sleep(backoff_delay)
                        retry_count += 1
                        continue
                    else:
                        # Max retries reached
                        execution.failed_steps.append(step.id)
                        self.logger.error(f"Step '{step.id}' failed after {retry_count + 1} attempts")
                        break
                        
            except Exception as e:
                error_msg = f"Unexpected error executing step '{step.id}': {str(e)}"
                self.logger.error(error_msg)
                
                if audit_logger:
                    await audit_logger.log_error(step.id, error_msg)
                
                if retry_count < self.config.max_retries:
                    backoff_delay = self.config.retry_backoff_factor ** retry_count
                    self.logger.info(f"Retrying step '{step.id}' after error, {backoff_delay}s backoff")
                    await asyncio.sleep(backoff_delay)
                    retry_count += 1
                    continue
                else:
                    execution.failed_steps.append(step.id)
                    break
        
        execution.current_step = None
    
    async def _handle_low_confidence(self, step: ExecutionStep, result: StepResult) -> bool:
        """
        Handle low confidence scenario - potentially request user override.
        
        Args:
            step: Step that had low confidence
            result: Step result with low confidence
            
        Returns:
            True if step should be accepted anyway, False to fail
        """
        if not self.config.override_enabled:
            return False
        
        if not self.override_callback:
            self.logger.warning("No override callback configured - cannot request user override")
            return False
        
        try:
            # Request user override via callback
            override_granted = self.override_callback(
                f"Step '{step.id}' has low confidence ({result.confidence.score:.3f} < "
                f"{step.confidence_threshold}). Reasoning: {result.confidence.reasoning}. "
                f"Accept anyway?",
                result
            )
            
            if override_granted:
                self.logger.info(f"User override granted for step '{step.id}'")
                return True
            else:
                self.logger.info(f"User override denied for step '{step.id}'")
                return False
                
        except Exception as e:
            self.logger.error(f"Error requesting user override: {e}")
            return False
    
    def _register_dependencies(self, plan: ExecutionPlan, memory_manager: "MemoryManager") -> None:
        """Register step dependencies with memory manager."""
        for step in plan.steps:
            for dep_step_id in step.dependencies:
                memory_manager.register_dependency(step.id, dep_step_id)
    
    def set_override_callback(self, callback: Callable[[str, StepResult], bool]) -> None:
        """Set callback for requesting user overrides."""
        self.override_callback = callback
        self.logger.debug("Override callback configured")
    
    def set_progress_callback(self, callback: Callable[[str, StepResult], None]) -> None:
        """Set callback for progress updates.""" 
        self.progress_callback = callback
        self.logger.debug("Progress callback configured")
    
    def get_execution_stats(self, execution: PlanExecution) -> Dict[str, Any]:
        """
        Get execution statistics.
        
        Args:
            execution: Plan execution
            
        Returns:
            Dictionary with execution statistics
        """
        total_steps = len(execution.results)
        successful_steps = sum(1 for r in execution.results if r.success)
        high_confidence_steps = sum(
            1 for r in execution.results 
            if r.success and r.confidence.score >= 0.8
        )
        
        avg_confidence = 0.0
        if execution.results:
            avg_confidence = sum(r.confidence.score for r in execution.results) / len(execution.results)
        
        total_retries = sum(r.confidence.retry_count for r in execution.results)
        
        return {
            "total_steps": total_steps,
            "successful_steps": successful_steps,
            "failed_steps": len(execution.failed_steps),
            "high_confidence_steps": high_confidence_steps,
            "average_confidence": avg_confidence,
            "total_retries": total_retries,
            "execution_time_ms": execution.total_execution_time_ms,
            "status": execution.status.value
        }