"""
Answer generator for natural language responses.
Converts query results into natural language answers using LLM assistance.
"""

import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime

from .question_analyzer import QuestionComponents, QuestionType
from .ontology_matcher import QueryOntologySubset
from .sparql_cassandra import SPARQLResult
from .cypher_executor import CypherResult

logger = logging.getLogger(__name__)


@dataclass
class AnswerMetadata:
    """Metadata about answer generation."""
    query_type: str
    backend_used: str
    execution_time: float
    result_count: int
    confidence: float
    explanation: str
    sources: List[str]


@dataclass
class GeneratedAnswer:
    """Generated natural language answer."""
    answer: str
    metadata: AnswerMetadata
    supporting_facts: List[str]
    raw_results: Union[SPARQLResult, CypherResult]
    generation_time: float


class AnswerGenerator:
    """Generates natural language answers from query results."""

    def __init__(self, prompt_service=None):
        """Initialize answer generator.

        Args:
            prompt_service: Service for LLM-based answer generation
        """
        self.prompt_service = prompt_service

        # Answer templates for different question types
        self.templates = {
            'count': "There are {count} {entity_type}.",
            'boolean_true': "Yes, {statement} is true.",
            'boolean_false': "No, {statement} is not true.",
            'list': "The {entity_type} are: {items}.",
            'single': "The {property} of {entity} is {value}.",
            'none': "No results were found for your query.",
            'error': "I encountered an error processing your query: {error}"
        }

    async def generate_answer(self,
                            question_components: QuestionComponents,
                            query_results: Union[SPARQLResult, CypherResult],
                            ontology_subset: QueryOntologySubset,
                            backend_used: str) -> GeneratedAnswer:
        """Generate natural language answer from query results.

        Args:
            question_components: Original question analysis
            query_results: Results from query execution
            ontology_subset: Ontology subset used
            backend_used: Backend that executed the query

        Returns:
            Generated answer with metadata
        """
        start_time = datetime.now()

        try:
            # Try LLM-based generation first
            if self.prompt_service:
                llm_answer = await self._generate_with_llm(
                    question_components, query_results, ontology_subset
                )
                if llm_answer:
                    execution_time = (datetime.now() - start_time).total_seconds()
                    return self._build_answer_response(
                        llm_answer, question_components, query_results,
                        backend_used, execution_time
                    )

            # Fall back to template-based generation
            template_answer = self._generate_with_template(
                question_components, query_results, ontology_subset
            )

            execution_time = (datetime.now() - start_time).total_seconds()
            return self._build_answer_response(
                template_answer, question_components, query_results,
                backend_used, execution_time
            )

        except Exception as e:
            logger.error(f"Answer generation failed: {e}")
            execution_time = (datetime.now() - start_time).total_seconds()
            error_answer = self.templates['error'].format(error=str(e))
            return self._build_answer_response(
                error_answer, question_components, query_results,
                backend_used, execution_time, confidence=0.0
            )

    async def _generate_with_llm(self,
                               question_components: QuestionComponents,
                               query_results: Union[SPARQLResult, CypherResult],
                               ontology_subset: QueryOntologySubset) -> Optional[str]:
        """Generate answer using LLM.

        Args:
            question_components: Question analysis
            query_results: Query results
            ontology_subset: Ontology subset

        Returns:
            Generated answer or None if failed
        """
        try:
            prompt = self._build_answer_prompt(
                question_components, query_results, ontology_subset
            )
            response = await self.prompt_service.generate_answer(prompt=prompt)

            if response and isinstance(response, dict):
                return response.get('answer', '').strip()
            elif isinstance(response, str):
                return response.strip()

        except Exception as e:
            logger.error(f"LLM answer generation failed: {e}")

        return None

    def _generate_with_template(self,
                              question_components: QuestionComponents,
                              query_results: Union[SPARQLResult, CypherResult],
                              ontology_subset: QueryOntologySubset) -> str:
        """Generate answer using templates.

        Args:
            question_components: Question analysis
            query_results: Query results
            ontology_subset: Ontology subset

        Returns:
            Template-based answer
        """
        # Handle empty results
        if not self._has_results(query_results):
            return self.templates['none']

        # Handle boolean queries
        if question_components.question_type == QuestionType.BOOLEAN:
            if hasattr(query_results, 'ask_result'):
                # SPARQL ASK result
                statement = self._extract_boolean_statement(question_components)
                if query_results.ask_result:
                    return self.templates['boolean_true'].format(statement=statement)
                else:
                    return self.templates['boolean_false'].format(statement=statement)
            else:
                # Cypher boolean (check if any results)
                has_results = len(query_results.records) > 0
                statement = self._extract_boolean_statement(question_components)
                if has_results:
                    return self.templates['boolean_true'].format(statement=statement)
                else:
                    return self.templates['boolean_false'].format(statement=statement)

        # Handle count queries
        if question_components.question_type == QuestionType.AGGREGATION:
            count = self._extract_count(query_results)
            entity_type = self._infer_entity_type(question_components, ontology_subset)
            return self.templates['count'].format(count=count, entity_type=entity_type)

        # Handle retrieval queries
        if question_components.question_type == QuestionType.RETRIEVAL:
            items = self._extract_items(query_results)
            if len(items) == 1:
                # Single result
                entity = question_components.entities[0] if question_components.entities else "entity"
                property_name = "value"
                return self.templates['single'].format(
                    property=property_name, entity=entity, value=items[0]
                )
            else:
                # Multiple results
                entity_type = self._infer_entity_type(question_components, ontology_subset)
                items_str = ", ".join(items)
                return self.templates['list'].format(entity_type=entity_type, items=items_str)

        # Handle factual queries
        if question_components.question_type == QuestionType.FACTUAL:
            facts = self._extract_facts(query_results)
            return ". ".join(facts) if facts else self.templates['none']

        # Default fallback
        items = self._extract_items(query_results)
        if items:
            return f"Found: {', '.join(items[:5])}" + ("..." if len(items) > 5 else "")
        else:
            return self.templates['none']

    def _build_answer_prompt(self,
                           question_components: QuestionComponents,
                           query_results: Union[SPARQLResult, CypherResult],
                           ontology_subset: QueryOntologySubset) -> str:
        """Build prompt for LLM answer generation.

        Args:
            question_components: Question analysis
            query_results: Query results
            ontology_subset: Ontology subset

        Returns:
            Formatted prompt string
        """
        # Format results for prompt
        results_str = self._format_results_for_prompt(query_results)

        # Extract ontology context
        context_classes = list(ontology_subset.classes.keys())[:5]
        context_properties = list(ontology_subset.object_properties.keys())[:5]

        prompt = f"""Generate a natural language answer for the following question based on the query results.

ORIGINAL QUESTION: {question_components.original_question}

QUESTION TYPE: {question_components.question_type.value}
EXPECTED ANSWER: {question_components.expected_answer_type}

ONTOLOGY CONTEXT:
- Classes: {', '.join(context_classes)}
- Properties: {', '.join(context_properties)}

QUERY RESULTS:
{results_str}

INSTRUCTIONS:
- Provide a clear, concise answer in natural language
- Use the original question's tone and style
- Include specific facts from the results
- If no results, explain that no information was found
- Be accurate and don't make assumptions beyond the data
- Limit response to 2-3 sentences unless the question requires more detail

ANSWER:"""

        return prompt

    def _format_results_for_prompt(self, query_results: Union[SPARQLResult, CypherResult]) -> str:
        """Format query results for prompt inclusion.

        Args:
            query_results: Query results to format

        Returns:
            Formatted results string
        """
        if isinstance(query_results, SPARQLResult):
            if hasattr(query_results, 'ask_result') and query_results.ask_result is not None:
                return f"Boolean result: {query_results.ask_result}"

            if not query_results.bindings:
                return "No results found"

            # Format SPARQL bindings
            lines = []
            for binding in query_results.bindings[:10]:  # Limit to first 10
                formatted = []
                for var, value in binding.items():
                    if isinstance(value, dict):
                        formatted.append(f"{var}: {value.get('value', value)}")
                    else:
                        formatted.append(f"{var}: {value}")
                lines.append("- " + ", ".join(formatted))

            if len(query_results.bindings) > 10:
                lines.append(f"... and {len(query_results.bindings) - 10} more results")

            return "\n".join(lines)

        else:  # CypherResult
            if not query_results.records:
                return "No results found"

            # Format Cypher records
            lines = []
            for record in query_results.records[:10]:  # Limit to first 10
                if isinstance(record, dict):
                    formatted = [f"{k}: {v}" for k, v in record.items()]
                    lines.append("- " + ", ".join(formatted))
                else:
                    lines.append(f"- {record}")

            if len(query_results.records) > 10:
                lines.append(f"... and {len(query_results.records) - 10} more results")

            return "\n".join(lines)

    def _has_results(self, query_results: Union[SPARQLResult, CypherResult]) -> bool:
        """Check if query results contain data.

        Args:
            query_results: Query results to check

        Returns:
            True if results contain data
        """
        if isinstance(query_results, SPARQLResult):
            return bool(query_results.bindings) or query_results.ask_result is not None
        else:  # CypherResult
            return bool(query_results.records)

    def _extract_count(self, query_results: Union[SPARQLResult, CypherResult]) -> int:
        """Extract count from aggregation query results.

        Args:
            query_results: Query results

        Returns:
            Count value
        """
        if isinstance(query_results, SPARQLResult):
            if query_results.bindings:
                binding = query_results.bindings[0]
                # Look for count variable
                for var, value in binding.items():
                    if 'count' in var.lower():
                        if isinstance(value, dict):
                            return int(value.get('value', 0))
                        return int(value)
            return len(query_results.bindings)
        else:  # CypherResult
            if query_results.records:
                record = query_results.records[0]
                if isinstance(record, dict):
                    # Look for count key
                    for key, value in record.items():
                        if 'count' in key.lower():
                            return int(value)
                elif isinstance(record, (int, float)):
                    return int(record)
            return len(query_results.records)

    def _extract_items(self, query_results: Union[SPARQLResult, CypherResult]) -> List[str]:
        """Extract items from query results.

        Args:
            query_results: Query results

        Returns:
            List of extracted items
        """
        items = []

        if isinstance(query_results, SPARQLResult):
            for binding in query_results.bindings:
                for var, value in binding.items():
                    if isinstance(value, dict):
                        item_value = value.get('value', str(value))
                    else:
                        item_value = str(value)

                    # Clean up URIs
                    if item_value.startswith('http'):
                        item_value = item_value.split('/')[-1].split('#')[-1]

                    items.append(item_value)
                    break  # Take first value per binding

        else:  # CypherResult
            for record in query_results.records:
                if isinstance(record, dict):
                    # Take first value from record
                    for key, value in record.items():
                        items.append(str(value))
                        break
                else:
                    items.append(str(record))

        return items

    def _extract_facts(self, query_results: Union[SPARQLResult, CypherResult]) -> List[str]:
        """Extract facts from query results.

        Args:
            query_results: Query results

        Returns:
            List of facts
        """
        facts = []

        if isinstance(query_results, SPARQLResult):
            for binding in query_results.bindings:
                fact_parts = []
                for var, value in binding.items():
                    if isinstance(value, dict):
                        val_str = value.get('value', str(value))
                    else:
                        val_str = str(value)

                    # Clean up URIs
                    if val_str.startswith('http'):
                        val_str = val_str.split('/')[-1].split('#')[-1]

                    fact_parts.append(f"{var}: {val_str}")

                facts.append(", ".join(fact_parts))

        else:  # CypherResult
            for record in query_results.records:
                if isinstance(record, dict):
                    fact_parts = [f"{k}: {v}" for k, v in record.items()]
                    facts.append(", ".join(fact_parts))
                else:
                    facts.append(str(record))

        return facts

    def _extract_boolean_statement(self, question_components: QuestionComponents) -> str:
        """Extract statement for boolean answer.

        Args:
            question_components: Question analysis

        Returns:
            Statement string
        """
        # Extract the key assertion from the question
        question = question_components.original_question.lower()

        # Remove question words
        statement = question.replace('is ', '').replace('are ', '').replace('does ', '')
        statement = statement.replace('?', '').strip()

        return statement

    def _infer_entity_type(self,
                          question_components: QuestionComponents,
                          ontology_subset: QueryOntologySubset) -> str:
        """Infer entity type from question and ontology.

        Args:
            question_components: Question analysis
            ontology_subset: Ontology subset

        Returns:
            Entity type string
        """
        # Try to match entities to ontology classes
        for entity in question_components.entities:
            entity_lower = entity.lower()
            for class_id in ontology_subset.classes:
                if class_id.lower() == entity_lower or entity_lower in class_id.lower():
                    return class_id

        # Fallback to first entity or generic term
        if question_components.entities:
            return question_components.entities[0]
        else:
            return "entities"

    def _build_answer_response(self,
                             answer: str,
                             question_components: QuestionComponents,
                             query_results: Union[SPARQLResult, CypherResult],
                             backend_used: str,
                             execution_time: float,
                             confidence: float = 0.8) -> GeneratedAnswer:
        """Build final answer response.

        Args:
            answer: Generated answer text
            question_components: Question analysis
            query_results: Query results
            backend_used: Backend used for query
            execution_time: Answer generation time
            confidence: Confidence score

        Returns:
            Complete answer response
        """
        # Extract supporting facts
        supporting_facts = self._extract_facts(query_results)

        # Build metadata
        result_count = 0
        if isinstance(query_results, SPARQLResult):
            result_count = len(query_results.bindings)
        else:  # CypherResult
            result_count = len(query_results.records)

        metadata = AnswerMetadata(
            query_type=question_components.question_type.value,
            backend_used=backend_used,
            execution_time=execution_time,
            result_count=result_count,
            confidence=confidence,
            explanation=f"Generated answer using {backend_used} backend",
            sources=[]  # Could be populated with data source information
        )

        return GeneratedAnswer(
            answer=answer,
            metadata=metadata,
            supporting_facts=supporting_facts[:5],  # Limit to top 5
            raw_results=query_results,
            generation_time=execution_time
        )