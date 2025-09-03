"""
Memory Manager Module

Handles inter-step data flow and context preservation for the confidence agent.
Manages execution context, result caching, and dependency resolution.
"""

import json
import time
import logging
from typing import Dict, Any, Optional, List, Set
from .types import ContextEntry, ExecutionStep, StepResult


class MemoryManager:
    """
    Manages execution context and inter-step data flow.
    
    Responsibilities:
    - Store and retrieve execution context between steps
    - Manage step dependencies and result passing
    - Handle context window management
    - Provide result caching with TTL
    """
    
    def __init__(self, max_context_size: int = 8192, cache_ttl_seconds: int = 300):
        self.logger = logging.getLogger(__name__)
        self.max_context_size = max_context_size
        self.cache_ttl_seconds = cache_ttl_seconds
        
        # In-memory storage for Phase 1 (could be Redis/external in Phase 2)
        self._context: Dict[str, ContextEntry] = {}
        self._step_results: Dict[str, StepResult] = {}
        self._dependency_graph: Dict[str, Set[str]] = {}  # step_id -> dependent_step_ids
        
    def store_context(self, key: str, value: Any, step_id: str, ttl_seconds: Optional[int] = None) -> None:
        """
        Store a context entry.
        
        Args:
            key: Context key
            value: Value to store
            step_id: ID of step that created this entry
            ttl_seconds: Time to live (defaults to cache_ttl_seconds)
        """
        ttl = ttl_seconds or self.cache_ttl_seconds
        
        entry = ContextEntry(
            key=key,
            value=value,
            step_id=step_id,
            timestamp=int(time.time()),
            ttl_seconds=ttl
        )
        
        self._context[key] = entry
        self.logger.debug(f"Stored context key '{key}' from step '{step_id}'")
        
        # Clean up expired entries
        self._cleanup_expired()
        
        # Manage context size
        self._manage_context_size()
    
    def get_context(self, key: str) -> Optional[Any]:
        """
        Retrieve a context value.
        
        Args:
            key: Context key to retrieve
            
        Returns:
            Context value or None if not found/expired
        """
        entry = self._context.get(key)
        if not entry:
            return None
            
        # Check if expired
        if self._is_expired(entry):
            del self._context[key]
            return None
            
        return entry.value
    
    def get_context_for_step(self, step: ExecutionStep) -> Dict[str, Any]:
        """
        Get all relevant context for a step based on its dependencies.
        
        Args:
            step: Execution step needing context
            
        Returns:
            Dictionary of relevant context entries
        """
        context = {}
        
        # Include results from dependency steps
        for dep_step_id in step.dependencies:
            result = self._step_results.get(dep_step_id)
            if result and result.success:
                context[f"step_{dep_step_id}_output"] = result.output
                context[f"step_{dep_step_id}_confidence"] = result.confidence.score
        
        # Include global context entries (filter by relevance if needed)
        for key, entry in self._context.items():
            if not self._is_expired(entry):
                context[key] = entry.value
        
        self.logger.debug(f"Retrieved context for step '{step.id}': {len(context)} entries")
        return context
    
    def store_step_result(self, result: StepResult) -> None:
        """
        Store result from step execution.
        
        Args:
            result: Step execution result
        """
        self._step_results[result.step_id] = result
        
        # Store key outputs in context for easy access
        if result.success:
            self.store_context(
                key=f"result_{result.step_id}",
                value=result.output,
                step_id=result.step_id
            )
        
        self.logger.debug(f"Stored result for step '{result.step_id}' (success: {result.success})")
    
    def get_step_result(self, step_id: str) -> Optional[StepResult]:
        """
        Get stored result for a step.
        
        Args:
            step_id: ID of step
            
        Returns:
            StepResult or None if not found
        """
        return self._step_results.get(step_id)
    
    def register_dependency(self, step_id: str, depends_on: str) -> None:
        """
        Register a dependency relationship between steps.
        
        Args:
            step_id: Step that depends on another
            depends_on: Step that must complete first
        """
        if depends_on not in self._dependency_graph:
            self._dependency_graph[depends_on] = set()
        
        self._dependency_graph[depends_on].add(step_id)
        
    def get_ready_steps(self, all_steps: List[ExecutionStep], completed_steps: Set[str]) -> List[ExecutionStep]:
        """
        Get steps that are ready to execute (all dependencies completed).
        
        Args:
            all_steps: All steps in the plan
            completed_steps: Set of completed step IDs
            
        Returns:
            List of steps ready for execution
        """
        ready = []
        
        for step in all_steps:
            if step.id in completed_steps:
                continue
                
            # Check if all dependencies are completed
            deps_completed = all(dep_id in completed_steps for dep_id in step.dependencies)
            
            if deps_completed:
                ready.append(step)
        
        return ready
    
    def serialize_context(self) -> str:
        """
        Serialize current context for debugging/audit.
        
        Returns:
            JSON string of current context
        """
        serializable = {}
        
        for key, entry in self._context.items():
            if not self._is_expired(entry):
                # Convert complex objects to strings for serialization
                try:
                    value = entry.value
                    if not isinstance(value, (str, int, float, bool, list, dict)):
                        value = str(value)
                    
                    serializable[key] = {
                        "value": value,
                        "step_id": entry.step_id,
                        "timestamp": entry.timestamp
                    }
                except Exception as e:
                    self.logger.warning(f"Could not serialize context key '{key}': {e}")
        
        return json.dumps(serializable, indent=2)
    
    def clear_context(self) -> None:
        """Clear all stored context (for cleanup between requests)."""
        self._context.clear()
        self._step_results.clear()
        self._dependency_graph.clear()
        self.logger.debug("Cleared all context")
    
    def get_memory_usage(self) -> Dict[str, int]:
        """
        Get memory usage statistics.
        
        Returns:
            Dictionary with usage statistics
        """
        return {
            "context_entries": len(self._context),
            "step_results": len(self._step_results),
            "dependencies": sum(len(deps) for deps in self._dependency_graph.values()),
            "estimated_size_bytes": self._estimate_memory_size()
        }
    
    def _is_expired(self, entry: ContextEntry) -> bool:
        """Check if a context entry has expired."""
        if entry.ttl_seconds is None:
            return False
            
        age_seconds = int(time.time()) - entry.timestamp
        return age_seconds > entry.ttl_seconds
    
    def _cleanup_expired(self) -> None:
        """Remove expired context entries."""
        expired_keys = [
            key for key, entry in self._context.items() 
            if self._is_expired(entry)
        ]
        
        for key in expired_keys:
            del self._context[key]
            
        if expired_keys:
            self.logger.debug(f"Cleaned up {len(expired_keys)} expired context entries")
    
    def _manage_context_size(self) -> None:
        """Manage context size by removing oldest entries if needed."""
        current_size = self._estimate_memory_size()
        
        if current_size > self.max_context_size:
            # Remove oldest entries first
            sorted_entries = sorted(
                self._context.items(),
                key=lambda x: x[1].timestamp
            )
            
            removed_count = 0
            for key, entry in sorted_entries:
                del self._context[key]
                removed_count += 1
                
                # Check size again
                if self._estimate_memory_size() <= self.max_context_size * 0.8:
                    break
            
            self.logger.debug(f"Removed {removed_count} context entries to manage size")
    
    def _estimate_memory_size(self) -> int:
        """Rough estimate of memory usage in bytes."""
        total = 0
        
        for key, entry in self._context.items():
            total += len(key) * 2  # Unicode chars
            total += len(str(entry.value)) * 2  # Rough estimate
            total += 100  # Overhead
            
        return total