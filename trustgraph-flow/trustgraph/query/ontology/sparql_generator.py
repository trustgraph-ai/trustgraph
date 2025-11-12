"""
SPARQL query generator for ontology-sensitive queries.
Converts natural language questions to SPARQL queries for Cassandra execution.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from .question_analyzer import QuestionComponents, QuestionType
from .ontology_matcher import QueryOntologySubset

logger = logging.getLogger(__name__)


@dataclass
class SPARQLQuery:
    """Generated SPARQL query with metadata."""
    query: str
    variables: List[str]
    query_type: str  # SELECT, ASK, CONSTRUCT, DESCRIBE
    explanation: str
    complexity_score: float


class SPARQLGenerator:
    """Generates SPARQL queries from natural language questions using LLM assistance."""

    def __init__(self, prompt_service=None):
        """Initialize SPARQL generator.

        Args:
            prompt_service: Service for LLM-based query generation
        """
        self.prompt_service = prompt_service

        # SPARQL query templates for common patterns
        self.templates = {
            'simple_class_query': """
PREFIX : <{namespace}>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?entity ?label WHERE {{
  ?entity rdf:type :{class_name} .
  OPTIONAL {{ ?entity rdfs:label ?label }}
}}""",

            'property_query': """
PREFIX : <{namespace}>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?subject ?object WHERE {{
  ?subject :{property} ?object .
  ?subject rdf:type :{subject_class} .
}}""",

            'hierarchy_query': """
PREFIX : <{namespace}>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?subclass ?superclass WHERE {{
  ?subclass rdfs:subClassOf* ?superclass .
  ?superclass rdf:type :{root_class} .
}}""",

            'count_query': """
PREFIX : <{namespace}>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT (COUNT(?entity) AS ?count) WHERE {{
  ?entity rdf:type :{class_name} .
  {additional_constraints}
}}""",

            'boolean_query': """
PREFIX : <{namespace}>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

ASK {{
  {triple_pattern}
}}"""
        }

    async def generate_sparql(self,
                            question_components: QuestionComponents,
                            ontology_subset: QueryOntologySubset) -> SPARQLQuery:
        """Generate SPARQL query for a question.

        Args:
            question_components: Analyzed question components
            ontology_subset: Relevant ontology subset

        Returns:
            Generated SPARQL query
        """
        # Try template-based generation first
        template_query = self._try_template_generation(question_components, ontology_subset)
        if template_query:
            logger.debug("Generated SPARQL using template")
            return template_query

        # Fall back to LLM-based generation
        if self.prompt_service:
            llm_query = await self._generate_with_llm(question_components, ontology_subset)
            if llm_query:
                logger.debug("Generated SPARQL using LLM")
                return llm_query

        # Final fallback to simple pattern
        logger.warning("Falling back to simple SPARQL pattern")
        return self._generate_fallback_query(question_components, ontology_subset)

    def _try_template_generation(self,
                               question_components: QuestionComponents,
                               ontology_subset: QueryOntologySubset) -> Optional[SPARQLQuery]:
        """Try to generate query using templates.

        Args:
            question_components: Question analysis
            ontology_subset: Ontology subset

        Returns:
            Generated query or None if no template matches
        """
        namespace = ontology_subset.metadata.get('namespace', 'http://example.org/')

        # Simple class query (What are the animals?)
        if (question_components.question_type == QuestionType.RETRIEVAL and
            len(question_components.entities) == 1 and
            question_components.entities[0].lower() in [c.lower() for c in ontology_subset.classes]):

            class_name = self._find_matching_class(question_components.entities[0], ontology_subset)
            if class_name:
                query = self.templates['simple_class_query'].format(
                    namespace=namespace,
                    class_name=class_name
                )
                return SPARQLQuery(
                    query=query,
                    variables=['entity', 'label'],
                    query_type='SELECT',
                    explanation=f"Retrieve all instances of {class_name}",
                    complexity_score=0.3
                )

        # Count query (How many animals are there?)
        if (question_components.question_type == QuestionType.AGGREGATION and
            'count' in question_components.aggregations and
            len(question_components.entities) >= 1):

            class_name = self._find_matching_class(question_components.entities[0], ontology_subset)
            if class_name:
                query = self.templates['count_query'].format(
                    namespace=namespace,
                    class_name=class_name,
                    additional_constraints=self._build_constraints(question_components, ontology_subset)
                )
                return SPARQLQuery(
                    query=query,
                    variables=['count'],
                    query_type='SELECT',
                    explanation=f"Count instances of {class_name}",
                    complexity_score=0.4
                )

        # Boolean query (Is X a Y?)
        if question_components.question_type == QuestionType.BOOLEAN:
            triple_pattern = self._build_boolean_pattern(question_components, ontology_subset)
            if triple_pattern:
                query = self.templates['boolean_query'].format(
                    namespace=namespace,
                    triple_pattern=triple_pattern
                )
                return SPARQLQuery(
                    query=query,
                    variables=[],
                    query_type='ASK',
                    explanation="Boolean query for fact checking",
                    complexity_score=0.2
                )

        return None

    async def _generate_with_llm(self,
                               question_components: QuestionComponents,
                               ontology_subset: QueryOntologySubset) -> Optional[SPARQLQuery]:
        """Generate SPARQL using LLM.

        Args:
            question_components: Question analysis
            ontology_subset: Ontology subset

        Returns:
            Generated query or None if failed
        """
        try:
            prompt = self._build_sparql_prompt(question_components, ontology_subset)
            response = await self.prompt_service.generate_sparql(prompt=prompt)

            if response and isinstance(response, dict):
                query = response.get('query', '').strip()
                if query.upper().startswith(('SELECT', 'ASK', 'CONSTRUCT', 'DESCRIBE')):
                    return SPARQLQuery(
                        query=query,
                        variables=self._extract_variables(query),
                        query_type=query.split()[0].upper(),
                        explanation=response.get('explanation', 'Generated by LLM'),
                        complexity_score=self._calculate_complexity(query)
                    )

        except Exception as e:
            logger.error(f"LLM SPARQL generation failed: {e}")

        return None

    def _build_sparql_prompt(self,
                           question_components: QuestionComponents,
                           ontology_subset: QueryOntologySubset) -> str:
        """Build prompt for LLM SPARQL generation.

        Args:
            question_components: Question analysis
            ontology_subset: Ontology subset

        Returns:
            Formatted prompt string
        """
        namespace = ontology_subset.metadata.get('namespace', 'http://example.org/')

        # Format ontology elements
        classes_str = self._format_classes_for_prompt(ontology_subset.classes, namespace)
        props_str = self._format_properties_for_prompt(
            ontology_subset.object_properties,
            ontology_subset.datatype_properties,
            namespace
        )

        prompt = f"""Generate a SPARQL query for the following question using the provided ontology.

QUESTION: {question_components.original_question}

ONTOLOGY NAMESPACE: {namespace}

AVAILABLE CLASSES:
{classes_str}

AVAILABLE PROPERTIES:
{props_str}

RULES:
- Use proper SPARQL syntax
- Include appropriate prefixes
- Use property paths for hierarchical queries (rdfs:subClassOf*)
- Add FILTER clauses for constraints
- Optimize for Cassandra backend
- Return both query and explanation

QUERY TYPE HINTS:
- Question type: {question_components.question_type.value}
- Expected answer: {question_components.expected_answer_type}
- Entities mentioned: {', '.join(question_components.entities)}
- Aggregations: {', '.join(question_components.aggregations)}

Generate a complete SPARQL query:"""

        return prompt

    def _generate_fallback_query(self,
                               question_components: QuestionComponents,
                               ontology_subset: QueryOntologySubset) -> SPARQLQuery:
        """Generate simple fallback query.

        Args:
            question_components: Question analysis
            ontology_subset: Ontology subset

        Returns:
            Basic SPARQL query
        """
        namespace = ontology_subset.metadata.get('namespace', 'http://example.org/')

        # Very basic SELECT query
        query = f"""PREFIX : <{namespace}>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?subject ?predicate ?object WHERE {{
  ?subject ?predicate ?object .
  FILTER(CONTAINS(STR(?subject), "{question_components.keywords[0] if question_components.keywords else 'entity'}"))
}}
LIMIT 10"""

        return SPARQLQuery(
            query=query,
            variables=['subject', 'predicate', 'object'],
            query_type='SELECT',
            explanation="Fallback query for basic pattern matching",
            complexity_score=0.1
        )

    def _find_matching_class(self, entity: str, ontology_subset: QueryOntologySubset) -> Optional[str]:
        """Find matching class in ontology subset.

        Args:
            entity: Entity string to match
            ontology_subset: Ontology subset

        Returns:
            Matching class name or None
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

    def _build_constraints(self,
                         question_components: QuestionComponents,
                         ontology_subset: QueryOntologySubset) -> str:
        """Build constraint clauses for SPARQL.

        Args:
            question_components: Question analysis
            ontology_subset: Ontology subset

        Returns:
            SPARQL constraint string
        """
        constraints = []

        for constraint in question_components.constraints:
            # Simple constraint patterns
            if 'greater than' in constraint.lower():
                # Extract number
                import re
                numbers = re.findall(r'\d+', constraint)
                if numbers:
                    constraints.append(f"FILTER(?value > {numbers[0]})")

            elif 'less than' in constraint.lower():
                numbers = re.findall(r'\d+', constraint)
                if numbers:
                    constraints.append(f"FILTER(?value < {numbers[0]})")

        return '\n  '.join(constraints)

    def _build_boolean_pattern(self,
                             question_components: QuestionComponents,
                             ontology_subset: QueryOntologySubset) -> Optional[str]:
        """Build triple pattern for boolean queries.

        Args:
            question_components: Question analysis
            ontology_subset: Ontology subset

        Returns:
            SPARQL triple pattern or None
        """
        if len(question_components.entities) >= 2:
            subject = question_components.entities[0]
            object_val = question_components.entities[1]

            # Try to find connecting property
            for prop_id in ontology_subset.object_properties:
                return f":{subject} :{prop_id} :{object_val} ."

            # Fallback to type check
            return f":{subject} rdf:type :{object_val} ."

        return None

    def _format_classes_for_prompt(self, classes: Dict[str, Any], namespace: str) -> str:
        """Format classes for prompt.

        Args:
            classes: Classes dictionary
            namespace: Ontology namespace

        Returns:
            Formatted classes string
        """
        if not classes:
            return "None"

        lines = []
        for class_id, definition in classes.items():
            comment = definition.get('comment', '')
            parent = definition.get('subclass_of', 'Thing')
            lines.append(f"- :{class_id} (subclass of :{parent}) - {comment}")

        return '\n'.join(lines)

    def _format_properties_for_prompt(self,
                                    object_props: Dict[str, Any],
                                    datatype_props: Dict[str, Any],
                                    namespace: str) -> str:
        """Format properties for prompt.

        Args:
            object_props: Object properties
            datatype_props: Datatype properties
            namespace: Ontology namespace

        Returns:
            Formatted properties string
        """
        lines = []

        for prop_id, definition in object_props.items():
            domain = definition.get('domain', 'Any')
            range_val = definition.get('range', 'Any')
            comment = definition.get('comment', '')
            lines.append(f"- :{prop_id} (:{domain} -> :{range_val}) - {comment}")

        for prop_id, definition in datatype_props.items():
            domain = definition.get('domain', 'Any')
            range_val = definition.get('range', 'xsd:string')
            comment = definition.get('comment', '')
            lines.append(f"- :{prop_id} (:{domain} -> {range_val}) - {comment}")

        return '\n'.join(lines) if lines else "None"

    def _extract_variables(self, query: str) -> List[str]:
        """Extract variables from SPARQL query.

        Args:
            query: SPARQL query string

        Returns:
            List of variable names
        """
        import re
        variables = re.findall(r'\?(\w+)', query)
        return list(set(variables))

    def _calculate_complexity(self, query: str) -> float:
        """Calculate complexity score for SPARQL query.

        Args:
            query: SPARQL query string

        Returns:
            Complexity score (0.0 to 1.0)
        """
        complexity = 0.0

        # Count different SPARQL features
        query_upper = query.upper()

        if 'JOIN' in query_upper or 'UNION' in query_upper:
            complexity += 0.3
        if 'FILTER' in query_upper:
            complexity += 0.2
        if 'OPTIONAL' in query_upper:
            complexity += 0.1
        if 'GROUP BY' in query_upper:
            complexity += 0.2
        if 'ORDER BY' in query_upper:
            complexity += 0.1
        if '*' in query:  # Property paths
            complexity += 0.1

        # Count variables
        variables = self._extract_variables(query)
        complexity += len(variables) * 0.05

        return min(complexity, 1.0)