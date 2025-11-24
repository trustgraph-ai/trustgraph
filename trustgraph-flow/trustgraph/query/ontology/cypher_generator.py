"""
Cypher query generator for ontology-sensitive queries.
Converts natural language questions to Cypher queries for graph databases.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from .question_analyzer import QuestionComponents, QuestionType
from .ontology_matcher import QueryOntologySubset

logger = logging.getLogger(__name__)


@dataclass
class CypherQuery:
    """Generated Cypher query with metadata."""
    query: str
    parameters: Dict[str, Any]
    variables: List[str]
    explanation: str
    complexity_score: float
    database_hints: Dict[str, Any] = None  # Database-specific optimization hints


class CypherGenerator:
    """Generates Cypher queries from natural language questions using LLM assistance."""

    def __init__(self, prompt_service=None):
        """Initialize Cypher generator.

        Args:
            prompt_service: Service for LLM-based query generation
        """
        self.prompt_service = prompt_service

        # Cypher query templates for common patterns
        self.templates = {
            'simple_node_query': """
MATCH (n:{node_label})
RETURN n.name AS name, n.{property} AS {property}
LIMIT {limit}""",

            'relationship_query': """
MATCH (a:{source_label})-[r:{relationship}]->(b:{target_label})
WHERE a.name = $source_name
RETURN b.name AS name, r.{rel_property} AS property""",

            'path_query': """
MATCH path = (start:{start_label})-[*1..{max_depth}]->(end:{end_label})
WHERE start.name = $start_name
RETURN path, length(path) AS path_length
ORDER BY path_length""",

            'count_query': """
MATCH (n:{node_label})
{where_clause}
RETURN count(n) AS count""",

            'aggregation_query': """
MATCH (n:{node_label})
{where_clause}
RETURN
  count(n) AS count,
  avg(n.{numeric_property}) AS average,
  sum(n.{numeric_property}) AS total""",

            'boolean_query': """
MATCH (a:{source_label})-[:{relationship}]->(b:{target_label})
WHERE a.name = $source_name AND b.name = $target_name
RETURN count(*) > 0 AS exists""",

            'hierarchy_query': """
MATCH (child:{child_label})-[:SUBCLASS_OF*]->(parent:{parent_label})
WHERE parent.name = $parent_name
RETURN child.name AS child_name, parent.name AS parent_name""",

            'property_filter_query': """
MATCH (n:{node_label})
WHERE n.{property} {operator} ${property}_value
RETURN n.name AS name, n.{property} AS {property}
ORDER BY n.{property}"""
        }

    async def generate_cypher(self,
                            question_components: QuestionComponents,
                            ontology_subset: QueryOntologySubset,
                            database_type: str = "neo4j") -> CypherQuery:
        """Generate Cypher query for a question.

        Args:
            question_components: Analyzed question components
            ontology_subset: Relevant ontology subset
            database_type: Target database (neo4j, memgraph, falkordb)

        Returns:
            Generated Cypher query
        """
        # Try template-based generation first
        template_query = self._try_template_generation(
            question_components, ontology_subset, database_type
        )
        if template_query:
            logger.debug("Generated Cypher using template")
            return template_query

        # Fall back to LLM-based generation
        if self.prompt_service:
            llm_query = await self._generate_with_llm(
                question_components, ontology_subset, database_type
            )
            if llm_query:
                logger.debug("Generated Cypher using LLM")
                return llm_query

        # Final fallback to simple pattern
        logger.warning("Falling back to simple Cypher pattern")
        return self._generate_fallback_query(question_components, ontology_subset)

    def _try_template_generation(self,
                               question_components: QuestionComponents,
                               ontology_subset: QueryOntologySubset,
                               database_type: str) -> Optional[CypherQuery]:
        """Try to generate query using templates.

        Args:
            question_components: Question analysis
            ontology_subset: Ontology subset
            database_type: Target database type

        Returns:
            Generated query or None if no template matches
        """
        # Simple node query (What are the animals?)
        if (question_components.question_type == QuestionType.RETRIEVAL and
            len(question_components.entities) == 1):

            node_label = self._find_matching_node_label(
                question_components.entities[0], ontology_subset
            )
            if node_label:
                query = self.templates['simple_node_query'].format(
                    node_label=node_label,
                    property='name',
                    limit=100
                )
                return CypherQuery(
                    query=query,
                    parameters={},
                    variables=['name'],
                    explanation=f"Retrieve all nodes of type {node_label}",
                    complexity_score=0.2,
                    database_hints=self._get_database_hints(database_type, 'simple')
                )

        # Count query (How many animals are there?)
        if (question_components.question_type == QuestionType.AGGREGATION and
            'count' in question_components.aggregations):

            node_label = self._find_matching_node_label(
                question_components.entities[0] if question_components.entities else 'Entity',
                ontology_subset
            )
            if node_label:
                where_clause = self._build_where_clause(question_components)
                query = self.templates['count_query'].format(
                    node_label=node_label,
                    where_clause=where_clause
                )
                return CypherQuery(
                    query=query,
                    parameters=self._extract_parameters(question_components),
                    variables=['count'],
                    explanation=f"Count nodes of type {node_label}",
                    complexity_score=0.3,
                    database_hints=self._get_database_hints(database_type, 'aggregation')
                )

        # Relationship query (Which documents were authored by John Smith?)
        if (question_components.question_type == QuestionType.RETRIEVAL and
            len(question_components.entities) >= 2):

            source_label = self._find_matching_node_label(
                question_components.entities[1], ontology_subset
            )
            target_label = self._find_matching_node_label(
                question_components.entities[0], ontology_subset
            )
            relationship = self._find_matching_relationship(
                question_components, ontology_subset
            )

            if source_label and target_label and relationship:
                query = self.templates['relationship_query'].format(
                    source_label=source_label,
                    target_label=target_label,
                    relationship=relationship,
                    rel_property='name'
                )
                return CypherQuery(
                    query=query,
                    parameters={'source_name': question_components.entities[1]},
                    variables=['name'],
                    explanation=f"Find {target_label} related to {source_label} via {relationship}",
                    complexity_score=0.4,
                    database_hints=self._get_database_hints(database_type, 'relationship')
                )

        # Boolean query (Is X related to Y?)
        if question_components.question_type == QuestionType.BOOLEAN:
            if len(question_components.entities) >= 2:
                source_label = self._find_matching_node_label(
                    question_components.entities[0], ontology_subset
                )
                target_label = self._find_matching_node_label(
                    question_components.entities[1], ontology_subset
                )
                relationship = self._find_matching_relationship(
                    question_components, ontology_subset
                )

                if source_label and target_label and relationship:
                    query = self.templates['boolean_query'].format(
                        source_label=source_label,
                        target_label=target_label,
                        relationship=relationship
                    )
                    return CypherQuery(
                        query=query,
                        parameters={
                            'source_name': question_components.entities[0],
                            'target_name': question_components.entities[1]
                        },
                        variables=['exists'],
                        explanation="Boolean check for relationship existence",
                        complexity_score=0.3,
                        database_hints=self._get_database_hints(database_type, 'boolean')
                    )

        return None

    async def _generate_with_llm(self,
                               question_components: QuestionComponents,
                               ontology_subset: QueryOntologySubset,
                               database_type: str) -> Optional[CypherQuery]:
        """Generate Cypher using LLM.

        Args:
            question_components: Question analysis
            ontology_subset: Ontology subset
            database_type: Target database type

        Returns:
            Generated query or None if failed
        """
        try:
            prompt = self._build_cypher_prompt(
                question_components, ontology_subset, database_type
            )
            response = await self.prompt_service.generate_cypher(prompt=prompt)

            if response and isinstance(response, dict):
                query = response.get('query', '').strip()
                if query.upper().startswith(('MATCH', 'CREATE', 'MERGE', 'DELETE', 'RETURN')):
                    return CypherQuery(
                        query=query,
                        parameters=response.get('parameters', {}),
                        variables=self._extract_variables(query),
                        explanation=response.get('explanation', 'Generated by LLM'),
                        complexity_score=self._calculate_complexity(query),
                        database_hints=self._get_database_hints(database_type, 'complex')
                    )

        except Exception as e:
            logger.error(f"LLM Cypher generation failed: {e}")

        return None

    def _build_cypher_prompt(self,
                           question_components: QuestionComponents,
                           ontology_subset: QueryOntologySubset,
                           database_type: str) -> str:
        """Build prompt for LLM Cypher generation.

        Args:
            question_components: Question analysis
            ontology_subset: Ontology subset
            database_type: Target database type

        Returns:
            Formatted prompt string
        """
        # Format ontology elements as node labels and relationships
        node_labels = self._format_node_labels(ontology_subset.classes)
        relationships = self._format_relationships(
            ontology_subset.object_properties,
            ontology_subset.datatype_properties
        )

        prompt = f"""Generate a Cypher query for the following question using the provided ontology.

QUESTION: {question_components.original_question}

TARGET DATABASE: {database_type}

AVAILABLE NODE LABELS (from classes):
{node_labels}

AVAILABLE RELATIONSHIP TYPES (from properties):
{relationships}

RULES:
- Use MATCH patterns for graph traversal
- Include WHERE clauses for filters
- Use aggregation functions when needed (COUNT, SUM, AVG)
- Optimize for {database_type} performance
- Consider index hints for large datasets
- Use parameters for values (e.g., $name)

QUERY TYPE HINTS:
- Question type: {question_components.question_type.value}
- Expected answer: {question_components.expected_answer_type}
- Entities mentioned: {', '.join(question_components.entities)}
- Aggregations: {', '.join(question_components.aggregations)}

DATABASE-SPECIFIC OPTIMIZATIONS:
{self._get_database_specific_hints(database_type)}

Generate a complete Cypher query with parameters:"""

        return prompt

    def _generate_fallback_query(self,
                               question_components: QuestionComponents,
                               ontology_subset: QueryOntologySubset) -> CypherQuery:
        """Generate simple fallback query.

        Args:
            question_components: Question analysis
            ontology_subset: Ontology subset

        Returns:
            Basic Cypher query
        """
        # Very basic MATCH query
        first_class = list(ontology_subset.classes.keys())[0] if ontology_subset.classes else 'Entity'

        query = f"""MATCH (n:{first_class})
WHERE n.name CONTAINS $keyword
RETURN n.name AS name, labels(n) AS types
LIMIT 10"""

        return CypherQuery(
            query=query,
            parameters={'keyword': question_components.keywords[0] if question_components.keywords else 'entity'},
            variables=['name', 'types'],
            explanation="Fallback query for basic pattern matching",
            complexity_score=0.1
        )

    def _find_matching_node_label(self, entity: str, ontology_subset: QueryOntologySubset) -> Optional[str]:
        """Find matching node label in ontology subset.

        Args:
            entity: Entity string to match
            ontology_subset: Ontology subset

        Returns:
            Matching node label or None
        """
        entity_lower = entity.lower()

        # Direct match
        for class_id in ontology_subset.classes:
            if class_id.lower() == entity_lower:
                return class_id

        # Label match
        for class_id, class_def in ontology_subset.classes.items():
            labels = class_def.get('labels', [])
            for label in labels:
                if isinstance(label, dict):
                    label_value = label.get('value', '').lower()
                    if label_value == entity_lower:
                        return class_id

        # Partial match
        for class_id in ontology_subset.classes:
            if entity_lower in class_id.lower() or class_id.lower() in entity_lower:
                return class_id

        return None

    def _find_matching_relationship(self,
                                  question_components: QuestionComponents,
                                  ontology_subset: QueryOntologySubset) -> Optional[str]:
        """Find matching relationship type.

        Args:
            question_components: Question analysis
            ontology_subset: Ontology subset

        Returns:
            Matching relationship type or None
        """
        # Look for relationship keywords
        for keyword in question_components.keywords:
            keyword_lower = keyword.lower()

            # Check object properties
            for prop_id in ontology_subset.object_properties:
                if keyword_lower in prop_id.lower() or prop_id.lower() in keyword_lower:
                    return prop_id.upper().replace('-', '_')

        # Common relationship mappings
        relationship_mappings = {
            'author': 'AUTHORED_BY',
            'created': 'CREATED_BY',
            'owns': 'OWNS',
            'has': 'HAS',
            'contains': 'CONTAINS',
            'parent': 'PARENT_OF',
            'child': 'CHILD_OF',
            'related': 'RELATED_TO'
        }

        for keyword in question_components.keywords:
            if keyword.lower() in relationship_mappings:
                return relationship_mappings[keyword.lower()]

        # Default relationship
        return 'RELATED_TO'

    def _build_where_clause(self, question_components: QuestionComponents) -> str:
        """Build WHERE clause for Cypher query.

        Args:
            question_components: Question analysis

        Returns:
            WHERE clause string
        """
        conditions = []

        for constraint in question_components.constraints:
            if 'greater than' in constraint.lower():
                import re
                numbers = re.findall(r'\d+', constraint)
                if numbers:
                    conditions.append(f"n.value > {numbers[0]}")
            elif 'less than' in constraint.lower():
                numbers = re.findall(r'\d+', constraint)
                if numbers:
                    conditions.append(f"n.value < {numbers[0]}")

        if conditions:
            return f"WHERE {' AND '.join(conditions)}"
        return ""

    def _extract_parameters(self, question_components: QuestionComponents) -> Dict[str, Any]:
        """Extract parameters from question components.

        Args:
            question_components: Question analysis

        Returns:
            Parameters dictionary
        """
        parameters = {}

        # Extract numeric values
        import re
        for constraint in question_components.constraints:
            numbers = re.findall(r'\d+', constraint)
            for i, number in enumerate(numbers):
                parameters[f'value_{i}'] = int(number)

        return parameters

    def _format_node_labels(self, classes: Dict[str, Any]) -> str:
        """Format classes as node labels for prompt.

        Args:
            classes: Classes dictionary

        Returns:
            Formatted node labels string
        """
        if not classes:
            return "None"

        lines = []
        for class_id, definition in classes.items():
            comment = definition.get('comment', '')
            lines.append(f"- :{class_id} - {comment}")

        return '\n'.join(lines)

    def _format_relationships(self,
                            object_props: Dict[str, Any],
                            datatype_props: Dict[str, Any]) -> str:
        """Format properties as relationships for prompt.

        Args:
            object_props: Object properties
            datatype_props: Datatype properties

        Returns:
            Formatted relationships string
        """
        lines = []

        for prop_id, definition in object_props.items():
            domain = definition.get('domain', 'Any')
            range_val = definition.get('range', 'Any')
            comment = definition.get('comment', '')
            rel_type = prop_id.upper().replace('-', '_')
            lines.append(f"- :{rel_type} ({domain} -> {range_val}) - {comment}")

        return '\n'.join(lines) if lines else "None"

    def _extract_variables(self, query: str) -> List[str]:
        """Extract variables from Cypher query.

        Args:
            query: Cypher query string

        Returns:
            List of variable names
        """
        import re
        # Extract RETURN clause variables
        return_match = re.search(r'RETURN\s+(.+?)(?:ORDER|LIMIT|$)', query, re.IGNORECASE | re.DOTALL)
        if return_match:
            return_clause = return_match.group(1)
            variables = re.findall(r'(\w+)(?:\s+AS\s+(\w+))?', return_clause)
            return [var[1] if var[1] else var[0] for var in variables]
        return []

    def _calculate_complexity(self, query: str) -> float:
        """Calculate complexity score for Cypher query.

        Args:
            query: Cypher query string

        Returns:
            Complexity score (0.0 to 1.0)
        """
        complexity = 0.0
        query_upper = query.upper()

        # Count different Cypher features
        if 'JOIN' in query_upper or 'UNION' in query_upper:
            complexity += 0.3
        if 'WHERE' in query_upper:
            complexity += 0.2
        if 'OPTIONAL' in query_upper:
            complexity += 0.1
        if 'ORDER BY' in query_upper:
            complexity += 0.1
        if '*' in query:  # Variable length paths
            complexity += 0.2
        if any(agg in query_upper for agg in ['COUNT', 'SUM', 'AVG', 'MAX', 'MIN']):
            complexity += 0.2

        # Count path length
        path_matches = re.findall(r'\[.*?\*(\d+)\.\.(\d+).*?\]', query)
        for start, end in path_matches:
            complexity += (int(end) - int(start)) * 0.05

        return min(complexity, 1.0)

    def _get_database_hints(self, database_type: str, query_category: str) -> Dict[str, Any]:
        """Get database-specific optimization hints.

        Args:
            database_type: Target database
            query_category: Category of query

        Returns:
            Optimization hints
        """
        hints = {}

        if database_type == "neo4j":
            hints.update({
                'use_index': True,
                'explain_plan': 'EXPLAIN',
                'profile_query': 'PROFILE'
            })
        elif database_type == "memgraph":
            hints.update({
                'use_index': True,
                'explain_plan': 'EXPLAIN',
                'memory_limit': '1GB'
            })
        elif database_type == "falkordb":
            hints.update({
                'use_index': False,  # Redis-based, different indexing
                'cache_result': True
            })

        return hints

    def _get_database_specific_hints(self, database_type: str) -> str:
        """Get database-specific optimization hints as text.

        Args:
            database_type: Target database

        Returns:
            Hints as formatted string
        """
        if database_type == "neo4j":
            return """- Use USING INDEX hints for large datasets
- Consider PROFILE for query optimization
- Prefer MERGE over CREATE when appropriate"""
        elif database_type == "memgraph":
            return """- Leverage in-memory processing advantages
- Use streaming for large result sets
- Consider query parallelization"""
        elif database_type == "falkordb":
            return """- Optimize for Redis memory constraints
- Use simple patterns for best performance
- Leverage Redis data structures when possible"""
        else:
            return "- Use standard Cypher optimization patterns"