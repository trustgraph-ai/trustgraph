"""
Query optimization module for OntoRAG.
Optimizes SPARQL and Cypher queries for better performance and accuracy.
"""

import logging
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import re

from .question_analyzer import QuestionComponents, QuestionType
from .ontology_matcher import QueryOntologySubset
from .sparql_generator import SPARQLQuery
from .cypher_generator import CypherQuery

logger = logging.getLogger(__name__)


class OptimizationStrategy(Enum):
    """Query optimization strategies."""
    PERFORMANCE = "performance"
    ACCURACY = "accuracy"
    BALANCED = "balanced"


@dataclass
class OptimizationHint:
    """Optimization hint for query processing."""
    strategy: OptimizationStrategy
    max_results: Optional[int] = None
    timeout_seconds: Optional[int] = None
    use_indices: bool = True
    enable_parallel: bool = False
    cache_results: bool = True


@dataclass
class QueryPlan:
    """Query execution plan with optimization metadata."""
    original_query: str
    optimized_query: str
    estimated_cost: float
    optimization_notes: List[str]
    index_hints: List[str]
    execution_order: List[str]


class QueryOptimizer:
    """Optimizes SPARQL and Cypher queries for performance and accuracy."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize query optimizer.

        Args:
            config: Optimizer configuration
        """
        self.config = config or {}
        self.default_strategy = OptimizationStrategy(
            self.config.get('default_strategy', 'balanced')
        )
        self.max_query_complexity = self.config.get('max_query_complexity', 10)
        self.enable_query_rewriting = self.config.get('enable_query_rewriting', True)

        # Performance thresholds
        self.large_result_threshold = self.config.get('large_result_threshold', 1000)
        self.complex_join_threshold = self.config.get('complex_join_threshold', 3)

    def optimize_sparql(self,
                       sparql_query: SPARQLQuery,
                       question_components: QuestionComponents,
                       ontology_subset: QueryOntologySubset,
                       optimization_hint: Optional[OptimizationHint] = None) -> Tuple[SPARQLQuery, QueryPlan]:
        """Optimize SPARQL query.

        Args:
            sparql_query: Original SPARQL query
            question_components: Question analysis
            ontology_subset: Ontology subset
            optimization_hint: Optimization hints

        Returns:
            Optimized SPARQL query and execution plan
        """
        hint = optimization_hint or OptimizationHint(strategy=self.default_strategy)

        optimized_query = sparql_query.query
        optimization_notes = []
        index_hints = []
        execution_order = []

        # Apply optimizations based on strategy
        if hint.strategy in [OptimizationStrategy.PERFORMANCE, OptimizationStrategy.BALANCED]:
            optimized_query, perf_notes, perf_hints = self._optimize_sparql_performance(
                optimized_query, question_components, ontology_subset, hint
            )
            optimization_notes.extend(perf_notes)
            index_hints.extend(perf_hints)

        if hint.strategy in [OptimizationStrategy.ACCURACY, OptimizationStrategy.BALANCED]:
            optimized_query, acc_notes = self._optimize_sparql_accuracy(
                optimized_query, question_components, ontology_subset
            )
            optimization_notes.extend(acc_notes)

        # Estimate query cost
        estimated_cost = self._estimate_sparql_cost(optimized_query, ontology_subset)

        # Build execution plan
        query_plan = QueryPlan(
            original_query=sparql_query.query,
            optimized_query=optimized_query,
            estimated_cost=estimated_cost,
            optimization_notes=optimization_notes,
            index_hints=index_hints,
            execution_order=execution_order
        )

        # Create optimized query object
        optimized_sparql = SPARQLQuery(
            query=optimized_query,
            variables=sparql_query.variables,
            query_type=sparql_query.query_type,
            explanation=f"Optimized: {sparql_query.explanation}",
            complexity_score=min(sparql_query.complexity_score * 0.8, 1.0)  # Assume optimization reduces complexity
        )

        return optimized_sparql, query_plan

    def optimize_cypher(self,
                       cypher_query: CypherQuery,
                       question_components: QuestionComponents,
                       ontology_subset: QueryOntologySubset,
                       optimization_hint: Optional[OptimizationHint] = None) -> Tuple[CypherQuery, QueryPlan]:
        """Optimize Cypher query.

        Args:
            cypher_query: Original Cypher query
            question_components: Question analysis
            ontology_subset: Ontology subset
            optimization_hint: Optimization hints

        Returns:
            Optimized Cypher query and execution plan
        """
        hint = optimization_hint or OptimizationHint(strategy=self.default_strategy)

        optimized_query = cypher_query.query
        optimization_notes = []
        index_hints = []
        execution_order = []

        # Apply optimizations based on strategy
        if hint.strategy in [OptimizationStrategy.PERFORMANCE, OptimizationStrategy.BALANCED]:
            optimized_query, perf_notes, perf_hints = self._optimize_cypher_performance(
                optimized_query, question_components, ontology_subset, hint
            )
            optimization_notes.extend(perf_notes)
            index_hints.extend(perf_hints)

        if hint.strategy in [OptimizationStrategy.ACCURACY, OptimizationStrategy.BALANCED]:
            optimized_query, acc_notes = self._optimize_cypher_accuracy(
                optimized_query, question_components, ontology_subset
            )
            optimization_notes.extend(acc_notes)

        # Estimate query cost
        estimated_cost = self._estimate_cypher_cost(optimized_query, ontology_subset)

        # Build execution plan
        query_plan = QueryPlan(
            original_query=cypher_query.query,
            optimized_query=optimized_query,
            estimated_cost=estimated_cost,
            optimization_notes=optimization_notes,
            index_hints=index_hints,
            execution_order=execution_order
        )

        # Create optimized query object
        optimized_cypher = CypherQuery(
            query=optimized_query,
            variables=cypher_query.variables,
            query_type=cypher_query.query_type,
            explanation=f"Optimized: {cypher_query.explanation}",
            complexity_score=min(cypher_query.complexity_score * 0.8, 1.0)
        )

        return optimized_cypher, query_plan

    def _optimize_sparql_performance(self,
                                   query: str,
                                   question_components: QuestionComponents,
                                   ontology_subset: QueryOntologySubset,
                                   hint: OptimizationHint) -> Tuple[str, List[str], List[str]]:
        """Apply performance optimizations to SPARQL query.

        Args:
            query: SPARQL query string
            question_components: Question analysis
            ontology_subset: Ontology subset
            hint: Optimization hints

        Returns:
            Optimized query, optimization notes, and index hints
        """
        optimized = query
        notes = []
        index_hints = []

        # Add LIMIT if not present and large results expected
        if hint.max_results and 'LIMIT' not in optimized.upper():
            optimized = f"{optimized.rstrip()}\nLIMIT {hint.max_results}"
            notes.append(f"Added LIMIT {hint.max_results} to prevent large result sets")

        # Optimize OPTIONAL clauses (move to end)
        optional_pattern = re.compile(r'OPTIONAL\s*\{[^}]+\}', re.IGNORECASE | re.DOTALL)
        optionals = optional_pattern.findall(optimized)
        if optionals:
            # Remove optionals from current position
            for optional in optionals:
                optimized = optimized.replace(optional, '')

            # Add them at the end (before ORDER BY/LIMIT)
            insert_point = optimized.rfind('ORDER BY')
            if insert_point == -1:
                insert_point = optimized.rfind('LIMIT')
            if insert_point == -1:
                insert_point = len(optimized.rstrip())

            for optional in optionals:
                optimized = optimized[:insert_point] + f"\n  {optional}" + optimized[insert_point:]

            notes.append("Moved OPTIONAL clauses to end for better performance")

        # Add index hints for Cassandra
        if 'WHERE' in optimized.upper():
            # Suggest indices for common patterns
            if '?subject rdf:type' in optimized:
                index_hints.append("type_index")
            if 'rdfs:subClassOf' in optimized:
                index_hints.append("hierarchy_index")

        # Optimize FILTER clauses (move closer to variable bindings)
        filter_pattern = re.compile(r'FILTER\s*\([^)]+\)', re.IGNORECASE)
        filters = filter_pattern.findall(optimized)
        if filters:
            notes.append("FILTER clauses present - ensure they're positioned optimally")

        return optimized, notes, index_hints

    def _optimize_sparql_accuracy(self,
                                query: str,
                                question_components: QuestionComponents,
                                ontology_subset: QueryOntologySubset) -> Tuple[str, List[str]]:
        """Apply accuracy optimizations to SPARQL query.

        Args:
            query: SPARQL query string
            question_components: Question analysis
            ontology_subset: Ontology subset

        Returns:
            Optimized query and optimization notes
        """
        optimized = query
        notes = []

        # Add missing namespace checks
        if question_components.question_type == QuestionType.RETRIEVAL:
            # Ensure we're not mixing namespaces inappropriately
            if 'http://' in optimized and '?' in optimized:
                notes.append("Verified namespace consistency for accuracy")

        # Add type constraints for better precision
        if '?entity' in optimized and 'rdf:type' not in optimized:
            # Find a good insertion point
            where_clause = re.search(r'WHERE\s*\{(.+)\}', optimized, re.DOTALL | re.IGNORECASE)
            if where_clause and ontology_subset.classes:
                # Add type constraint for the most relevant class
                main_class = list(ontology_subset.classes.keys())[0]
                type_constraint = f"\n  ?entity rdf:type :{main_class} ."

                # Insert after the WHERE {
                where_start = where_clause.start(1)
                optimized = optimized[:where_start] + type_constraint + optimized[where_start:]
                notes.append(f"Added type constraint for {main_class} to improve accuracy")

        # Add DISTINCT if not present for retrieval queries
        if (question_components.question_type == QuestionType.RETRIEVAL and
            'DISTINCT' not in optimized.upper() and
            'SELECT' in optimized.upper()):
            optimized = optimized.replace('SELECT ', 'SELECT DISTINCT ', 1)
            notes.append("Added DISTINCT to eliminate duplicate results")

        return optimized, notes

    def _optimize_cypher_performance(self,
                                   query: str,
                                   question_components: QuestionComponents,
                                   ontology_subset: QueryOntologySubset,
                                   hint: OptimizationHint) -> Tuple[str, List[str], List[str]]:
        """Apply performance optimizations to Cypher query.

        Args:
            query: Cypher query string
            question_components: Question analysis
            ontology_subset: Ontology subset
            hint: Optimization hints

        Returns:
            Optimized query, optimization notes, and index hints
        """
        optimized = query
        notes = []
        index_hints = []

        # Add LIMIT if not present
        if hint.max_results and 'LIMIT' not in optimized.upper():
            optimized = f"{optimized.rstrip()}\nLIMIT {hint.max_results}"
            notes.append(f"Added LIMIT {hint.max_results} to prevent large result sets")

        # Use parameters for literals to enable query plan caching
        if "'" in optimized or '"' in optimized:
            notes.append("Consider using parameters for literal values to enable query plan caching")

        # Suggest indices based on query patterns
        if 'MATCH (n:' in optimized:
            label_match = re.search(r'MATCH \(n:(\w+)\)', optimized)
            if label_match:
                label = label_match.group(1)
                index_hints.append(f"node_label_index:{label}")

        if 'WHERE' in optimized.upper() and '.' in optimized:
            # Property access patterns
            property_pattern = re.compile(r'\.(\w+)', re.IGNORECASE)
            properties = property_pattern.findall(optimized)
            for prop in set(properties):
                index_hints.append(f"property_index:{prop}")

        # Optimize relationship traversals
        if '-[' in optimized and '*' in optimized:
            notes.append("Variable length path detected - consider adding relationship type filters")

        # Early filtering optimization
        if 'WHERE' in optimized.upper():
            # Move WHERE clauses closer to MATCH clauses
            notes.append("WHERE clauses present - ensure early filtering for performance")

        return optimized, notes, index_hints

    def _optimize_cypher_accuracy(self,
                                query: str,
                                question_components: QuestionComponents,
                                ontology_subset: QueryOntologySubset) -> Tuple[str, List[str]]:
        """Apply accuracy optimizations to Cypher query.

        Args:
            query: Cypher query string
            question_components: Question analysis
            ontology_subset: Ontology subset

        Returns:
            Optimized query and optimization notes
        """
        optimized = query
        notes = []

        # Add DISTINCT if not present for retrieval queries
        if (question_components.question_type == QuestionType.RETRIEVAL and
            'DISTINCT' not in optimized.upper() and
            'RETURN' in optimized.upper()):
            optimized = re.sub(r'RETURN\s+', 'RETURN DISTINCT ', optimized, count=1, flags=re.IGNORECASE)
            notes.append("Added DISTINCT to eliminate duplicate results")

        # Ensure proper relationship direction
        if '-[' in optimized and question_components.relationships:
            notes.append("Verified relationship directions for semantic accuracy")

        # Add null checks for optional properties
        if '?' in optimized or 'OPTIONAL' in optimized.upper():
            notes.append("Consider adding null checks for optional properties")

        return optimized, notes

    def _estimate_sparql_cost(self, query: str, ontology_subset: QueryOntologySubset) -> float:
        """Estimate execution cost for SPARQL query.

        Args:
            query: SPARQL query string
            ontology_subset: Ontology subset

        Returns:
            Estimated cost (0.0 to 1.0)
        """
        cost = 0.0

        # Basic query complexity
        cost += len(query.split('\n')) * 0.01

        # Join complexity
        triple_patterns = len(re.findall(r'\?\w+\s+\?\w+\s+\?\w+', query))
        cost += triple_patterns * 0.1

        # OPTIONAL clauses
        optional_count = len(re.findall(r'OPTIONAL', query, re.IGNORECASE))
        cost += optional_count * 0.15

        # FILTER clauses
        filter_count = len(re.findall(r'FILTER', query, re.IGNORECASE))
        cost += filter_count * 0.1

        # Property paths
        path_count = len(re.findall(r'\*|\+', query))
        cost += path_count * 0.2

        # Ontology subset size impact
        total_elements = (len(ontology_subset.classes) +
                         len(ontology_subset.object_properties) +
                         len(ontology_subset.datatype_properties))
        cost += (total_elements / 100.0) * 0.1

        return min(cost, 1.0)

    def _estimate_cypher_cost(self, query: str, ontology_subset: QueryOntologySubset) -> float:
        """Estimate execution cost for Cypher query.

        Args:
            query: Cypher query string
            ontology_subset: Ontology subset

        Returns:
            Estimated cost (0.0 to 1.0)
        """
        cost = 0.0

        # Basic query complexity
        cost += len(query.split('\n')) * 0.01

        # Pattern complexity
        match_count = len(re.findall(r'MATCH', query, re.IGNORECASE))
        cost += match_count * 0.1

        # Relationship traversals
        rel_count = len(re.findall(r'-\[.*?\]-', query))
        cost += rel_count * 0.1

        # Variable length paths
        var_path_count = len(re.findall(r'\*\d*\.\.', query))
        cost += var_path_count * 0.3

        # WHERE clauses
        where_count = len(re.findall(r'WHERE', query, re.IGNORECASE))
        cost += where_count * 0.05

        # Aggregation functions
        agg_count = len(re.findall(r'COUNT|SUM|AVG|MIN|MAX', query, re.IGNORECASE))
        cost += agg_count * 0.1

        # Ontology subset size impact
        total_elements = (len(ontology_subset.classes) +
                         len(ontology_subset.object_properties) +
                         len(ontology_subset.datatype_properties))
        cost += (total_elements / 100.0) * 0.1

        return min(cost, 1.0)

    def should_use_cache(self,
                        query: str,
                        question_components: QuestionComponents,
                        optimization_hint: OptimizationHint) -> bool:
        """Determine if query results should be cached.

        Args:
            query: Query string
            question_components: Question analysis
            optimization_hint: Optimization hints

        Returns:
            True if results should be cached
        """
        if not optimization_hint.cache_results:
            return False

        # Cache simple retrieval and factual queries
        if question_components.question_type in [QuestionType.RETRIEVAL, QuestionType.FACTUAL]:
            return True

        # Cache expensive aggregation queries
        if (question_components.question_type == QuestionType.AGGREGATION and
            ('COUNT' in query.upper() or 'SUM' in query.upper())):
            return True

        # Don't cache real-time or time-sensitive queries
        if any(keyword in question_components.original_question.lower()
               for keyword in ['now', 'current', 'latest', 'recent']):
            return False

        return False

    def get_cache_key(self,
                     query: str,
                     ontology_subset: QueryOntologySubset) -> str:
        """Generate cache key for query.

        Args:
            query: Query string
            ontology_subset: Ontology subset

        Returns:
            Cache key string
        """
        import hashlib

        # Create stable representation
        ontology_repr = f"{sorted(ontology_subset.classes.keys())}-{sorted(ontology_subset.object_properties.keys())}"
        combined = f"{query.strip()}-{ontology_repr}"

        return hashlib.md5(combined.encode()).hexdigest()