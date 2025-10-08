"""
Backend router for ontology query system.
Routes queries to appropriate backend based on configuration.
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from .question_analyzer import QuestionComponents
from .ontology_matcher import QueryOntologySubset

logger = logging.getLogger(__name__)


class BackendType(Enum):
    """Supported backend types."""
    CASSANDRA = "cassandra"
    NEO4J = "neo4j"
    MEMGRAPH = "memgraph"
    FALKORDB = "falkordb"


@dataclass
class BackendConfig:
    """Configuration for a backend."""
    type: BackendType
    priority: int = 0
    enabled: bool = True
    config: Dict[str, Any] = None


@dataclass
class QueryRoute:
    """Routing decision for a query."""
    backend_type: BackendType
    query_language: str  # 'sparql' or 'cypher'
    confidence: float
    reasoning: str


class BackendRouter:
    """Routes queries to appropriate backends based on configuration and heuristics."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize backend router.

        Args:
            config: Router configuration
        """
        self.config = config
        self.backends = self._parse_backend_config(config)
        self.routing_strategy = config.get('routing_strategy', 'priority')
        self.enable_fallback = config.get('enable_fallback', True)

    def _parse_backend_config(self, config: Dict[str, Any]) -> Dict[BackendType, BackendConfig]:
        """Parse backend configuration.

        Args:
            config: Configuration dictionary

        Returns:
            Dictionary of backend type to configuration
        """
        backends = {}

        # Parse primary backend
        primary = config.get('primary', 'cassandra')
        if primary:
            try:
                backend_type = BackendType(primary)
                backends[backend_type] = BackendConfig(
                    type=backend_type,
                    priority=100,
                    enabled=True,
                    config=config.get(primary, {})
                )
            except ValueError:
                logger.warning(f"Unknown primary backend type: {primary}")

        # Parse fallback backends
        fallbacks = config.get('fallback', [])
        for i, fallback in enumerate(fallbacks):
            try:
                backend_type = BackendType(fallback)
                backends[backend_type] = BackendConfig(
                    type=backend_type,
                    priority=50 - i * 10,  # Decreasing priority
                    enabled=True,
                    config=config.get(fallback, {})
                )
            except ValueError:
                logger.warning(f"Unknown fallback backend type: {fallback}")

        return backends

    def route_query(self,
                   question_components: QuestionComponents,
                   ontology_subsets: List[QueryOntologySubset]) -> QueryRoute:
        """Route a query to the best backend.

        Args:
            question_components: Analyzed question
            ontology_subsets: Relevant ontology subsets

        Returns:
            QueryRoute with routing decision
        """
        if self.routing_strategy == 'priority':
            return self._route_by_priority()
        elif self.routing_strategy == 'adaptive':
            return self._route_adaptive(question_components, ontology_subsets)
        elif self.routing_strategy == 'round_robin':
            return self._route_round_robin()
        else:
            return self._route_by_priority()

    def _route_by_priority(self) -> QueryRoute:
        """Route based on backend priority.

        Returns:
            QueryRoute to highest priority backend
        """
        # Find highest priority enabled backend
        best_backend = None
        best_priority = -1

        for backend_type, backend_config in self.backends.items():
            if backend_config.enabled and backend_config.priority > best_priority:
                best_backend = backend_type
                best_priority = backend_config.priority

        if best_backend is None:
            raise RuntimeError("No enabled backends available")

        # Determine query language
        query_language = 'sparql' if best_backend == BackendType.CASSANDRA else 'cypher'

        return QueryRoute(
            backend_type=best_backend,
            query_language=query_language,
            confidence=1.0,
            reasoning=f"Priority routing to {best_backend.value}"
        )

    def _route_adaptive(self,
                       question_components: QuestionComponents,
                       ontology_subsets: List[QueryOntologySubset]) -> QueryRoute:
        """Route based on question characteristics and ontology complexity.

        Args:
            question_components: Analyzed question
            ontology_subsets: Relevant ontology subsets

        Returns:
            QueryRoute with adaptive decision
        """
        scores = {}

        for backend_type, backend_config in self.backends.items():
            if not backend_config.enabled:
                continue

            score = self._calculate_backend_score(
                backend_type, question_components, ontology_subsets
            )
            scores[backend_type] = score

        if not scores:
            raise RuntimeError("No enabled backends available")

        # Select backend with highest score
        best_backend = max(scores.keys(), key=lambda k: scores[k])
        best_score = scores[best_backend]

        # Determine query language
        query_language = 'sparql' if best_backend == BackendType.CASSANDRA else 'cypher'

        return QueryRoute(
            backend_type=best_backend,
            query_language=query_language,
            confidence=best_score,
            reasoning=f"Adaptive routing: {best_backend.value} scored {best_score:.2f}"
        )

    def _calculate_backend_score(self,
                                backend_type: BackendType,
                                question_components: QuestionComponents,
                                ontology_subsets: List[QueryOntologySubset]) -> float:
        """Calculate score for a backend based on query characteristics.

        Args:
            backend_type: Backend to score
            question_components: Question analysis
            ontology_subsets: Ontology subsets

        Returns:
            Score (0.0 to 1.0)
        """
        score = 0.0

        # Base priority score
        backend_config = self.backends[backend_type]
        score += backend_config.priority / 100.0

        # Question type preferences
        if backend_type == BackendType.CASSANDRA:
            # SPARQL is good for hierarchical and complex reasoning
            if question_components.question_type.value in ['factual', 'aggregation']:
                score += 0.3
            # Good for ontology-heavy queries
            if len(ontology_subsets) > 1:
                score += 0.2
        else:
            # Cypher is good for graph traversal and relationships
            if question_components.question_type.value in ['relationship', 'retrieval']:
                score += 0.3
            # Good for simple graph patterns
            if len(question_components.relationships) > 0:
                score += 0.2

        # Complexity considerations
        total_elements = sum(
            len(subset.classes) + len(subset.object_properties) + len(subset.datatype_properties)
            for subset in ontology_subsets
        )

        if backend_type == BackendType.CASSANDRA:
            # SPARQL handles complex ontologies well
            if total_elements > 20:
                score += 0.2
        else:
            # Cypher is efficient for simpler queries
            if total_elements <= 10:
                score += 0.2

        # Aggregation considerations
        if question_components.aggregations:
            if backend_type == BackendType.CASSANDRA:
                score += 0.1  # SPARQL has built-in aggregation
            else:
                score += 0.2  # Cypher has excellent aggregation

        return min(score, 1.0)

    def _route_round_robin(self) -> QueryRoute:
        """Route using round-robin strategy.

        Returns:
            QueryRoute using round-robin selection
        """
        # Simple round-robin implementation
        enabled_backends = [
            bt for bt, bc in self.backends.items() if bc.enabled
        ]

        if not enabled_backends:
            raise RuntimeError("No enabled backends available")

        # For simplicity, just return the first enabled backend
        # In a real implementation, you'd track state
        backend_type = enabled_backends[0]
        query_language = 'sparql' if backend_type == BackendType.CASSANDRA else 'cypher'

        return QueryRoute(
            backend_type=backend_type,
            query_language=query_language,
            confidence=0.8,
            reasoning=f"Round-robin routing to {backend_type.value}"
        )

    def get_fallback_route(self, failed_backend: BackendType) -> Optional[QueryRoute]:
        """Get fallback route when a backend fails.

        Args:
            failed_backend: Backend that failed

        Returns:
            Fallback route or None if no fallback available
        """
        if not self.enable_fallback:
            return None

        # Find next best backend
        fallback_backends = [
            (bt, bc) for bt, bc in self.backends.items()
            if bc.enabled and bt != failed_backend
        ]

        if not fallback_backends:
            return None

        # Sort by priority
        fallback_backends.sort(key=lambda x: x[1].priority, reverse=True)
        fallback_type = fallback_backends[0][0]

        query_language = 'sparql' if fallback_type == BackendType.CASSANDRA else 'cypher'

        return QueryRoute(
            backend_type=fallback_type,
            query_language=query_language,
            confidence=0.7,
            reasoning=f"Fallback from {failed_backend.value} to {fallback_type.value}"
        )

    def get_available_backends(self) -> List[BackendType]:
        """Get list of available backends.

        Returns:
            List of enabled backend types
        """
        return [bt for bt, bc in self.backends.items() if bc.enabled]

    def is_backend_enabled(self, backend_type: BackendType) -> bool:
        """Check if a backend is enabled.

        Args:
            backend_type: Backend to check

        Returns:
            True if backend is enabled
        """
        backend_config = self.backends.get(backend_type)
        return backend_config is not None and backend_config.enabled

    def update_backend_status(self, backend_type: BackendType, enabled: bool):
        """Update backend enabled status.

        Args:
            backend_type: Backend to update
            enabled: New enabled status
        """
        if backend_type in self.backends:
            self.backends[backend_type].enabled = enabled
            logger.info(f"Backend {backend_type.value} {'enabled' if enabled else 'disabled'}")
        else:
            logger.warning(f"Unknown backend type: {backend_type}")

    def get_backend_config(self, backend_type: BackendType) -> Optional[Dict[str, Any]]:
        """Get configuration for a backend.

        Args:
            backend_type: Backend type

        Returns:
            Configuration dictionary or None
        """
        backend_config = self.backends.get(backend_type)
        return backend_config.config if backend_config else None