"""
Error handling and recovery mechanisms for OntoRAG.
Provides comprehensive error handling, retry logic, and graceful degradation.
"""

import logging
import time
import asyncio
from typing import Dict, Any, List, Optional, Callable, Union, Type
from dataclasses import dataclass
from enum import Enum
from functools import wraps
import traceback

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for better handling."""
    ONTOLOGY_LOADING = "ontology_loading"
    QUESTION_ANALYSIS = "question_analysis"
    QUERY_GENERATION = "query_generation"
    QUERY_EXECUTION = "query_execution"
    ANSWER_GENERATION = "answer_generation"
    BACKEND_CONNECTION = "backend_connection"
    CACHE_ERROR = "cache_error"
    VALIDATION_ERROR = "validation_error"
    TIMEOUT_ERROR = "timeout_error"
    AUTHENTICATION_ERROR = "authentication_error"


@dataclass
class ErrorContext:
    """Context information for an error."""
    category: ErrorCategory
    severity: ErrorSeverity
    component: str
    operation: str
    user_message: Optional[str] = None
    technical_details: Optional[str] = None
    suggestion: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = None


class OntoRAGError(Exception):
    """Base exception for OntoRAG system."""

    def __init__(self,
                 message: str,
                 context: Optional[ErrorContext] = None,
                 cause: Optional[Exception] = None):
        """Initialize OntoRAG error.

        Args:
            message: Error message
            context: Error context
            cause: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.context = context or ErrorContext(
            category=ErrorCategory.VALIDATION_ERROR,
            severity=ErrorSeverity.MEDIUM,
            component="unknown",
            operation="unknown"
        )
        self.cause = cause
        self.timestamp = time.time()


class OntologyLoadingError(OntoRAGError):
    """Error loading ontology."""
    pass


class QuestionAnalysisError(OntoRAGError):
    """Error analyzing question."""
    pass


class QueryGenerationError(OntoRAGError):
    """Error generating query."""
    pass


class QueryExecutionError(OntoRAGError):
    """Error executing query."""
    pass


class AnswerGenerationError(OntoRAGError):
    """Error generating answer."""
    pass


class BackendConnectionError(OntoRAGError):
    """Error connecting to backend."""
    pass


class TimeoutError(OntoRAGError):
    """Operation timeout error."""
    pass


@dataclass
class RetryConfig:
    """Configuration for retry logic."""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_backoff: bool = True
    jitter: bool = True
    retry_on_exceptions: List[Type[Exception]] = None


class ErrorRecoveryStrategy:
    """Strategy for handling and recovering from errors."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize error recovery strategy.

        Args:
            config: Recovery configuration
        """
        self.config = config or {}
        self.retry_configs = self._build_retry_configs()
        self.fallback_strategies = self._build_fallback_strategies()
        self.error_counters: Dict[str, int] = {}
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}

    def _build_retry_configs(self) -> Dict[ErrorCategory, RetryConfig]:
        """Build retry configurations for different error categories."""
        return {
            ErrorCategory.BACKEND_CONNECTION: RetryConfig(
                max_retries=5,
                base_delay=2.0,
                retry_on_exceptions=[BackendConnectionError, ConnectionError, TimeoutError]
            ),
            ErrorCategory.QUERY_EXECUTION: RetryConfig(
                max_retries=3,
                base_delay=1.0,
                retry_on_exceptions=[QueryExecutionError, TimeoutError]
            ),
            ErrorCategory.ONTOLOGY_LOADING: RetryConfig(
                max_retries=2,
                base_delay=0.5,
                retry_on_exceptions=[OntologyLoadingError, IOError]
            ),
            ErrorCategory.QUESTION_ANALYSIS: RetryConfig(
                max_retries=2,
                base_delay=1.0,
                retry_on_exceptions=[QuestionAnalysisError, TimeoutError]
            ),
            ErrorCategory.ANSWER_GENERATION: RetryConfig(
                max_retries=2,
                base_delay=1.0,
                retry_on_exceptions=[AnswerGenerationError, TimeoutError]
            )
        }

    def _build_fallback_strategies(self) -> Dict[ErrorCategory, Callable]:
        """Build fallback strategies for different error categories."""
        return {
            ErrorCategory.QUESTION_ANALYSIS: self._fallback_question_analysis,
            ErrorCategory.QUERY_GENERATION: self._fallback_query_generation,
            ErrorCategory.QUERY_EXECUTION: self._fallback_query_execution,
            ErrorCategory.ANSWER_GENERATION: self._fallback_answer_generation,
            ErrorCategory.BACKEND_CONNECTION: self._fallback_backend_connection
        }

    async def handle_error(self,
                          error: Exception,
                          context: ErrorContext,
                          operation: Callable,
                          *args,
                          **kwargs) -> Any:
        """Handle error with recovery strategies.

        Args:
            error: The exception that occurred
            context: Error context
            operation: Function to retry
            *args: Operation arguments
            **kwargs: Operation keyword arguments

        Returns:
            Result of successful operation or fallback
        """
        logger.error(f"Handling error in {context.component}.{context.operation}: {error}")

        # Update error counters
        error_key = f"{context.category.value}:{context.component}"
        self.error_counters[error_key] = self.error_counters.get(error_key, 0) + 1

        # Check circuit breaker
        if self._is_circuit_open(error_key):
            return await self._execute_fallback(context, *args, **kwargs)

        # Try retry if configured
        retry_config = self.retry_configs.get(context.category)
        if retry_config and context.retry_count < retry_config.max_retries:
            if any(isinstance(error, exc_type) for exc_type in retry_config.retry_on_exceptions or []):
                return await self._retry_operation(
                    operation, context, retry_config, *args, **kwargs
                )

        # Execute fallback strategy
        return await self._execute_fallback(context, *args, **kwargs)

    async def _retry_operation(self,
                              operation: Callable,
                              context: ErrorContext,
                              retry_config: RetryConfig,
                              *args,
                              **kwargs) -> Any:
        """Retry operation with backoff."""
        context.retry_count += 1

        # Calculate delay
        delay = retry_config.base_delay
        if retry_config.exponential_backoff:
            delay *= (2 ** (context.retry_count - 1))
        delay = min(delay, retry_config.max_delay)

        # Add jitter
        if retry_config.jitter:
            import random
            delay *= (0.5 + random.random())

        logger.info(f"Retrying {context.component}.{context.operation} "
                   f"(attempt {context.retry_count}) after {delay:.2f}s")

        await asyncio.sleep(delay)

        try:
            if asyncio.iscoroutinefunction(operation):
                return await operation(*args, **kwargs)
            else:
                return operation(*args, **kwargs)
        except Exception as e:
            return await self.handle_error(e, context, operation, *args, **kwargs)

    async def _execute_fallback(self,
                               context: ErrorContext,
                               *args,
                               **kwargs) -> Any:
        """Execute fallback strategy."""
        fallback_func = self.fallback_strategies.get(context.category)
        if fallback_func:
            logger.info(f"Executing fallback for {context.category.value}")
            try:
                if asyncio.iscoroutinefunction(fallback_func):
                    return await fallback_func(context, *args, **kwargs)
                else:
                    return fallback_func(context, *args, **kwargs)
            except Exception as e:
                logger.error(f"Fallback strategy failed: {e}")

        # Default fallback
        return self._default_fallback(context)

    def _is_circuit_open(self, error_key: str) -> bool:
        """Check if circuit breaker is open."""
        circuit = self.circuit_breakers.get(error_key, {})
        error_count = self.error_counters.get(error_key, 0)
        error_threshold = self.config.get('circuit_breaker_threshold', 10)
        window_seconds = self.config.get('circuit_breaker_window', 300)  # 5 minutes

        current_time = time.time()
        window_start = circuit.get('window_start', current_time)

        # Reset window if expired
        if current_time - window_start > window_seconds:
            self.circuit_breakers[error_key] = {'window_start': current_time}
            self.error_counters[error_key] = 0
            return False

        return error_count >= error_threshold

    def _default_fallback(self, context: ErrorContext) -> Any:
        """Default fallback response."""
        if context.category == ErrorCategory.ANSWER_GENERATION:
            return "I'm sorry, I encountered an error while processing your question. Please try again."
        elif context.category == ErrorCategory.QUERY_EXECUTION:
            return {"error": "Query execution failed", "results": []}
        else:
            return None

    # Fallback strategy implementations

    async def _fallback_question_analysis(self, context: ErrorContext, question: str, **kwargs):
        """Fallback for question analysis."""
        from .question_analyzer import QuestionComponents, QuestionType

        # Simple keyword-based analysis
        question_lower = question.lower()

        # Determine question type
        if any(word in question_lower for word in ['how many', 'count', 'number']):
            question_type = QuestionType.AGGREGATION
        elif question_lower.startswith(('is', 'are', 'does', 'can')):
            question_type = QuestionType.BOOLEAN
        elif any(word in question_lower for word in ['what', 'which', 'who', 'where']):
            question_type = QuestionType.RETRIEVAL
        else:
            question_type = QuestionType.FACTUAL

        # Extract simple entities (nouns)
        import re
        words = re.findall(r'\b[a-zA-Z]+\b', question)
        entities = [word for word in words if len(word) > 3 and word.lower() not in
                   {'what', 'which', 'where', 'when', 'who', 'how', 'does', 'are', 'the'}]

        return QuestionComponents(
            original_question=question,
            normalized_question=question.lower(),
            question_type=question_type,
            entities=entities[:3],  # Limit to 3 entities
            keywords=words[:5],     # Limit to 5 keywords
            relationships=[],
            constraints=[],
            aggregations=['count'] if question_type == QuestionType.AGGREGATION else [],
            expected_answer_type='text'
        )

    async def _fallback_query_generation(self, context: ErrorContext, **kwargs):
        """Fallback for query generation."""
        # Generate simple query based on available information
        if 'sparql' in context.metadata.get('query_language', '').lower():
            query = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?subject ?predicate ?object WHERE {
  ?subject ?predicate ?object .
}
LIMIT 10
"""
            from .sparql_generator import SPARQLQuery
            return SPARQLQuery(
                query=query,
                variables=['subject', 'predicate', 'object'],
                query_type='SELECT',
                explanation='Fallback SPARQL query',
                complexity_score=0.1
            )
        else:
            query = "MATCH (n) RETURN n LIMIT 10"
            from .cypher_generator import CypherQuery
            return CypherQuery(
                query=query,
                variables=['n'],
                query_type='MATCH',
                explanation='Fallback Cypher query',
                complexity_score=0.1
            )

    async def _fallback_query_execution(self, context: ErrorContext, **kwargs):
        """Fallback for query execution."""
        # Return empty results
        if 'sparql' in context.metadata.get('query_language', '').lower():
            from .sparql_cassandra import SPARQLResult
            return SPARQLResult(
                bindings=[],
                variables=[],
                execution_time=0.0
            )
        else:
            from .cypher_executor import CypherResult
            return CypherResult(
                records=[],
                summary={'type': 'fallback'},
                metadata={'query': 'fallback'},
                execution_time=0.0
            )

    async def _fallback_answer_generation(self, context: ErrorContext, question: str = None, **kwargs):
        """Fallback for answer generation."""
        fallback_messages = [
            "I'm experiencing some technical difficulties. Please try rephrasing your question.",
            "I couldn't process your question at the moment. Could you try asking it differently?",
            "There seems to be an issue with my analysis. Please try again in a moment.",
            "I'm having trouble understanding your question right now. Please try again."
        ]

        import random
        return random.choice(fallback_messages)

    async def _fallback_backend_connection(self, context: ErrorContext, **kwargs):
        """Fallback for backend connection."""
        logger.warning(f"Backend connection failed for {context.component}")
        # Could switch to alternative backend here
        return None


def with_error_handling(category: ErrorCategory,
                       component: str,
                       operation: str,
                       severity: ErrorSeverity = ErrorSeverity.MEDIUM):
    """Decorator for automatic error handling.

    Args:
        category: Error category
        component: Component name
        operation: Operation name
        severity: Error severity
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except Exception as e:
                context = ErrorContext(
                    category=category,
                    severity=severity,
                    component=component,
                    operation=operation,
                    technical_details=str(e),
                    metadata={'args': str(args), 'kwargs': str(kwargs)}
                )

                # Get error recovery strategy from first argument if it's available
                error_strategy = None
                if args and hasattr(args[0], '_error_strategy'):
                    error_strategy = args[0]._error_strategy

                if error_strategy:
                    return await error_strategy.handle_error(e, context, func, *args, **kwargs)
                else:
                    # Re-raise as OntoRAG error
                    raise OntoRAGError(
                        f"Error in {component}.{operation}: {str(e)}",
                        context=context,
                        cause=e
                    )

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = ErrorContext(
                    category=category,
                    severity=severity,
                    component=component,
                    operation=operation,
                    technical_details=str(e),
                    metadata={'args': str(args), 'kwargs': str(kwargs)}
                )

                raise OntoRAGError(
                    f"Error in {component}.{operation}: {str(e)}",
                    context=context,
                    cause=e
                )

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class ErrorReporter:
    """Reports and tracks errors for monitoring and debugging."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize error reporter.

        Args:
            config: Reporter configuration
        """
        self.config = config or {}
        self.error_log: List[Dict[str, Any]] = []
        self.max_log_size = self.config.get('max_log_size', 1000)

    def report_error(self, error: OntoRAGError):
        """Report an error for tracking.

        Args:
            error: The error to report
        """
        error_entry = {
            'timestamp': error.timestamp,
            'message': error.message,
            'category': error.context.category.value,
            'severity': error.context.severity.value,
            'component': error.context.component,
            'operation': error.context.operation,
            'retry_count': error.context.retry_count,
            'technical_details': error.context.technical_details,
            'stack_trace': traceback.format_exc() if error.cause else None
        }

        self.error_log.append(error_entry)

        # Trim log if too large
        if len(self.error_log) > self.max_log_size:
            self.error_log = self.error_log[-self.max_log_size:]

        # Log based on severity
        if error.context.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"CRITICAL ERROR: {error.message}")
        elif error.context.severity == ErrorSeverity.HIGH:
            logger.error(f"HIGH SEVERITY: {error.message}")
        elif error.context.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"MEDIUM SEVERITY: {error.message}")
        else:
            logger.info(f"LOW SEVERITY: {error.message}")

    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of recent errors.

        Returns:
            Error summary statistics
        """
        if not self.error_log:
            return {'total_errors': 0}

        recent_errors = [
            e for e in self.error_log
            if time.time() - e['timestamp'] < 3600  # Last hour
        ]

        category_counts = {}
        severity_counts = {}
        component_counts = {}

        for error in recent_errors:
            category_counts[error['category']] = category_counts.get(error['category'], 0) + 1
            severity_counts[error['severity']] = severity_counts.get(error['severity'], 0) + 1
            component_counts[error['component']] = component_counts.get(error['component'], 0) + 1

        return {
            'total_errors': len(self.error_log),
            'recent_errors': len(recent_errors),
            'category_breakdown': category_counts,
            'severity_breakdown': severity_counts,
            'component_breakdown': component_counts,
            'most_recent_error': self.error_log[-1] if self.error_log else None
        }