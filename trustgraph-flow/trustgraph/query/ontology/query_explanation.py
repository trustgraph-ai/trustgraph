"""
Query explanation system for OntoRAG.
Provides detailed explanations of how queries are processed and results are derived.
"""

import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime

from .question_analyzer import QuestionComponents, QuestionType
from .ontology_matcher import QueryOntologySubset
from .sparql_generator import SPARQLQuery
from .cypher_generator import CypherQuery
from .sparql_cassandra import SPARQLResult
from .cypher_executor import CypherResult

logger = logging.getLogger(__name__)


@dataclass
class ExplanationStep:
    """Individual step in query explanation."""
    step_number: int
    component: str
    operation: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    explanation: str
    duration_ms: float
    success: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueryExplanation:
    """Complete explanation of query processing."""
    query_id: str
    original_question: str
    processing_steps: List[ExplanationStep]
    final_answer: str
    confidence_score: float
    total_duration_ms: float
    ontologies_used: List[str]
    backend_used: str
    reasoning_chain: List[str]
    technical_details: Dict[str, Any]
    user_friendly_explanation: str


class QueryExplainer:
    """Generates explanations for query processing."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize query explainer.

        Args:
            config: Explainer configuration
        """
        self.config = config or {}
        self.explanation_level = self.config.get('explanation_level', 'detailed')  # basic, detailed, technical
        self.include_technical_details = self.config.get('include_technical_details', True)
        self.max_reasoning_steps = self.config.get('max_reasoning_steps', 10)

        # Templates for different explanation types
        self.step_templates = {
            'question_analysis': {
                'basic': "I analyzed your question to understand what you're asking.",
                'detailed': "I analyzed your question '{question}' and identified it as a {question_type} query about {entities}.",
                'technical': "Question analysis: Type={question_type}, Entities={entities}, Keywords={keywords}, Expected answer={answer_type}"
            },
            'ontology_matching': {
                'basic': "I found relevant knowledge about {entities} in the available ontologies.",
                'detailed': "I searched through {ontology_count} ontologies and found {selected_elements} relevant concepts related to your question.",
                'technical': "Ontology matching: Selected {classes} classes, {properties} properties from {ontologies}"
            },
            'query_generation': {
                'basic': "I generated a query to search for the information.",
                'detailed': "I created a {query_type} query using {query_language} to search the {backend} database.",
                'technical': "Query generation: {query_language} query with {variables} variables, complexity score {complexity}"
            },
            'query_execution': {
                'basic': "I searched the database and found {result_count} results.",
                'detailed': "I executed the query against the {backend} database and retrieved {result_count} results in {duration}ms.",
                'technical': "Query execution: {backend} backend, {result_count} results, execution time {duration}ms"
            },
            'answer_generation': {
                'basic': "I generated a natural language answer from the results.",
                'detailed': "I processed {result_count} results and generated an answer with {confidence}% confidence.",
                'technical': "Answer generation: {result_count} input results, {generation_method} method, confidence {confidence}"
            }
        }

        self.reasoning_templates = {
            'entity_identification': "I identified '{entity}' as a key concept in your question.",
            'ontology_selection': "I selected the '{ontology}' ontology because it contains relevant information about {concepts}.",
            'query_strategy': "I chose a {strategy} query approach because {reason}.",
            'result_filtering': "I filtered the results to show only the most relevant {count} items.",
            'confidence_assessment': "I'm {confidence}% confident in this answer because {reasoning}."
        }

    def explain_query_processing(self,
                                question: str,
                                question_components: QuestionComponents,
                                ontology_subsets: List[QueryOntologySubset],
                                generated_query: Union[SPARQLQuery, CypherQuery],
                                query_results: Union[SPARQLResult, CypherResult],
                                final_answer: str,
                                processing_metadata: Dict[str, Any]) -> QueryExplanation:
        """Generate comprehensive explanation of query processing.

        Args:
            question: Original question
            question_components: Analyzed question components
            ontology_subsets: Selected ontology subsets
            generated_query: Generated query
            query_results: Query execution results
            final_answer: Final generated answer
            processing_metadata: Processing metadata

        Returns:
            Complete query explanation
        """
        query_id = processing_metadata.get('query_id', f"query_{datetime.now().timestamp()}")
        start_time = processing_metadata.get('start_time', datetime.now())

        # Build explanation steps
        steps = []
        step_number = 1

        # Step 1: Question Analysis
        steps.append(self._explain_question_analysis(
            step_number, question, question_components
        ))
        step_number += 1

        # Step 2: Ontology Matching
        steps.append(self._explain_ontology_matching(
            step_number, question_components, ontology_subsets
        ))
        step_number += 1

        # Step 3: Query Generation
        steps.append(self._explain_query_generation(
            step_number, generated_query, processing_metadata
        ))
        step_number += 1

        # Step 4: Query Execution
        steps.append(self._explain_query_execution(
            step_number, generated_query, query_results, processing_metadata
        ))
        step_number += 1

        # Step 5: Answer Generation
        steps.append(self._explain_answer_generation(
            step_number, query_results, final_answer, processing_metadata
        ))

        # Build reasoning chain
        reasoning_chain = self._build_reasoning_chain(
            question_components, ontology_subsets, generated_query, processing_metadata
        )

        # Calculate overall confidence
        confidence_score = self._calculate_explanation_confidence(
            question_components, query_results, processing_metadata
        )

        # Generate user-friendly explanation
        user_friendly_explanation = self._generate_user_friendly_explanation(
            question, question_components, ontology_subsets, final_answer
        )

        # Calculate total duration
        total_duration = processing_metadata.get('total_duration_ms', 0)

        return QueryExplanation(
            query_id=query_id,
            original_question=question,
            processing_steps=steps,
            final_answer=final_answer,
            confidence_score=confidence_score,
            total_duration_ms=total_duration,
            ontologies_used=[subset.metadata.get('ontology_id', 'unknown') for subset in ontology_subsets],
            backend_used=processing_metadata.get('backend_used', 'unknown'),
            reasoning_chain=reasoning_chain,
            technical_details=self._extract_technical_details(processing_metadata),
            user_friendly_explanation=user_friendly_explanation
        )

    def _explain_question_analysis(self,
                                  step_number: int,
                                  question: str,
                                  question_components: QuestionComponents) -> ExplanationStep:
        """Explain question analysis step."""
        template = self.step_templates['question_analysis'][self.explanation_level]

        if self.explanation_level == 'basic':
            explanation = template
        elif self.explanation_level == 'detailed':
            explanation = template.format(
                question=question,
                question_type=question_components.question_type.value.replace('_', ' '),
                entities=', '.join(question_components.entities[:3])
            )
        else:  # technical
            explanation = template.format(
                question_type=question_components.question_type.value,
                entities=question_components.entities,
                keywords=question_components.keywords,
                answer_type=question_components.expected_answer_type
            )

        return ExplanationStep(
            step_number=step_number,
            component="question_analyzer",
            operation="analyze_question",
            input_data={"question": question},
            output_data={
                "question_type": question_components.question_type.value,
                "entities": question_components.entities,
                "keywords": question_components.keywords
            },
            explanation=explanation,
            duration_ms=0.0,  # Would be tracked in actual implementation
            success=True
        )

    def _explain_ontology_matching(self,
                                  step_number: int,
                                  question_components: QuestionComponents,
                                  ontology_subsets: List[QueryOntologySubset]) -> ExplanationStep:
        """Explain ontology matching step."""
        template = self.step_templates['ontology_matching'][self.explanation_level]

        total_elements = sum(
            len(subset.classes) + len(subset.object_properties) + len(subset.datatype_properties)
            for subset in ontology_subsets
        )

        if self.explanation_level == 'basic':
            explanation = template.format(
                entities=', '.join(question_components.entities[:3])
            )
        elif self.explanation_level == 'detailed':
            explanation = template.format(
                ontology_count=len(ontology_subsets),
                selected_elements=total_elements
            )
        else:  # technical
            total_classes = sum(len(subset.classes) for subset in ontology_subsets)
            total_properties = sum(
                len(subset.object_properties) + len(subset.datatype_properties)
                for subset in ontology_subsets
            )
            ontology_names = [subset.metadata.get('ontology_id', 'unknown') for subset in ontology_subsets]

            explanation = template.format(
                classes=total_classes,
                properties=total_properties,
                ontologies=', '.join(ontology_names)
            )

        return ExplanationStep(
            step_number=step_number,
            component="ontology_matcher",
            operation="select_relevant_subset",
            input_data={"entities": question_components.entities},
            output_data={
                "ontology_count": len(ontology_subsets),
                "total_elements": total_elements
            },
            explanation=explanation,
            duration_ms=0.0,
            success=True
        )

    def _explain_query_generation(self,
                                 step_number: int,
                                 generated_query: Union[SPARQLQuery, CypherQuery],
                                 metadata: Dict[str, Any]) -> ExplanationStep:
        """Explain query generation step."""
        template = self.step_templates['query_generation'][self.explanation_level]

        query_language = "SPARQL" if isinstance(generated_query, SPARQLQuery) else "Cypher"
        backend = metadata.get('backend_used', 'unknown')

        if self.explanation_level == 'basic':
            explanation = template
        elif self.explanation_level == 'detailed':
            explanation = template.format(
                query_type=generated_query.query_type,
                query_language=query_language,
                backend=backend
            )
        else:  # technical
            explanation = template.format(
                query_language=query_language,
                variables=len(generated_query.variables),
                complexity=f"{generated_query.complexity_score:.2f}"
            )

        return ExplanationStep(
            step_number=step_number,
            component="query_generator",
            operation="generate_query",
            input_data={"query_type": generated_query.query_type},
            output_data={
                "query_language": query_language,
                "variables": generated_query.variables,
                "complexity": generated_query.complexity_score
            },
            explanation=explanation,
            duration_ms=0.0,
            success=True,
            metadata={"generated_query": generated_query.query}
        )

    def _explain_query_execution(self,
                                step_number: int,
                                generated_query: Union[SPARQLQuery, CypherQuery],
                                query_results: Union[SPARQLResult, CypherResult],
                                metadata: Dict[str, Any]) -> ExplanationStep:
        """Explain query execution step."""
        template = self.step_templates['query_execution'][self.explanation_level]

        backend = metadata.get('backend_used', 'unknown')
        duration = getattr(query_results, 'execution_time', 0) * 1000  # Convert to ms

        if isinstance(query_results, SPARQLResult):
            result_count = len(query_results.bindings)
        else:  # CypherResult
            result_count = len(query_results.records)

        if self.explanation_level == 'basic':
            explanation = template.format(result_count=result_count)
        elif self.explanation_level == 'detailed':
            explanation = template.format(
                backend=backend,
                result_count=result_count,
                duration=f"{duration:.1f}"
            )
        else:  # technical
            explanation = template.format(
                backend=backend,
                result_count=result_count,
                duration=f"{duration:.1f}"
            )

        return ExplanationStep(
            step_number=step_number,
            component="query_executor",
            operation="execute_query",
            input_data={"query": generated_query.query},
            output_data={
                "result_count": result_count,
                "execution_time_ms": duration
            },
            explanation=explanation,
            duration_ms=duration,
            success=result_count >= 0
        )

    def _explain_answer_generation(self,
                                  step_number: int,
                                  query_results: Union[SPARQLResult, CypherResult],
                                  final_answer: str,
                                  metadata: Dict[str, Any]) -> ExplanationStep:
        """Explain answer generation step."""
        template = self.step_templates['answer_generation'][self.explanation_level]

        if isinstance(query_results, SPARQLResult):
            result_count = len(query_results.bindings)
        else:  # CypherResult
            result_count = len(query_results.records)

        confidence = metadata.get('answer_confidence', 0.8) * 100  # Convert to percentage

        if self.explanation_level == 'basic':
            explanation = template
        elif self.explanation_level == 'detailed':
            explanation = template.format(
                result_count=result_count,
                confidence=f"{confidence:.0f}"
            )
        else:  # technical
            generation_method = metadata.get('generation_method', 'template_based')
            explanation = template.format(
                result_count=result_count,
                generation_method=generation_method,
                confidence=f"{confidence:.1f}"
            )

        return ExplanationStep(
            step_number=step_number,
            component="answer_generator",
            operation="generate_answer",
            input_data={"result_count": result_count},
            output_data={
                "answer": final_answer,
                "confidence": confidence / 100
            },
            explanation=explanation,
            duration_ms=0.0,
            success=bool(final_answer)
        )

    def _build_reasoning_chain(self,
                              question_components: QuestionComponents,
                              ontology_subsets: List[QueryOntologySubset],
                              generated_query: Union[SPARQLQuery, CypherQuery],
                              metadata: Dict[str, Any]) -> List[str]:
        """Build reasoning chain explaining the decision process."""
        reasoning = []

        # Entity identification reasoning
        if question_components.entities:
            for entity in question_components.entities[:3]:
                reasoning.append(
                    self.reasoning_templates['entity_identification'].format(entity=entity)
                )

        # Ontology selection reasoning
        if ontology_subsets:
            primary_ontology = ontology_subsets[0]
            ontology_id = primary_ontology.metadata.get('ontology_id', 'primary')
            concepts = list(primary_ontology.classes.keys())[:3]
            reasoning.append(
                self.reasoning_templates['ontology_selection'].format(
                    ontology=ontology_id,
                    concepts=', '.join(concepts)
                )
            )

        # Query strategy reasoning
        query_language = "SPARQL" if isinstance(generated_query, SPARQLQuery) else "Cypher"
        if question_components.question_type == QuestionType.AGGREGATION:
            strategy = "aggregation"
            reason = "you asked for a count or sum"
        elif question_components.question_type == QuestionType.BOOLEAN:
            strategy = "boolean"
            reason = "you asked a yes/no question"
        else:
            strategy = "retrieval"
            reason = "you asked for specific information"

        reasoning.append(
            self.reasoning_templates['query_strategy'].format(
                strategy=strategy,
                reason=reason
            )
        )

        # Confidence assessment
        confidence = metadata.get('answer_confidence', 0.8) * 100
        if confidence > 90:
            confidence_reason = "the query matched well with available data"
        elif confidence > 70:
            confidence_reason = "the query found relevant information with some uncertainty"
        else:
            confidence_reason = "the available data partially matches your question"

        reasoning.append(
            self.reasoning_templates['confidence_assessment'].format(
                confidence=f"{confidence:.0f}",
                reasoning=confidence_reason
            )
        )

        return reasoning[:self.max_reasoning_steps]

    def _calculate_explanation_confidence(self,
                                        question_components: QuestionComponents,
                                        query_results: Union[SPARQLResult, CypherResult],
                                        metadata: Dict[str, Any]) -> float:
        """Calculate confidence score for the explanation."""
        confidence = 0.8  # Base confidence

        # Adjust based on result count
        if isinstance(query_results, SPARQLResult):
            result_count = len(query_results.bindings)
        else:
            result_count = len(query_results.records)

        if result_count > 0:
            confidence += 0.1
        if result_count > 5:
            confidence += 0.05

        # Adjust based on question complexity
        if len(question_components.entities) > 0:
            confidence += 0.05

        # Adjust based on processing success
        if metadata.get('all_steps_successful', True):
            confidence += 0.05

        return min(confidence, 1.0)

    def _generate_user_friendly_explanation(self,
                                          question: str,
                                          question_components: QuestionComponents,
                                          ontology_subsets: List[QueryOntologySubset],
                                          final_answer: str) -> str:
        """Generate user-friendly explanation of the process."""
        explanation_parts = []

        # Introduction
        explanation_parts.append(f"To answer your question '{question}', I followed these steps:")

        # Process summary
        if question_components.question_type == QuestionType.AGGREGATION:
            explanation_parts.append("1. I recognized this as a counting or aggregation question")
        elif question_components.question_type == QuestionType.BOOLEAN:
            explanation_parts.append("1. I recognized this as a yes/no question")
        else:
            explanation_parts.append("1. I analyzed your question to understand what information you need")

        # Ontology usage
        if ontology_subsets:
            ontology_count = len(ontology_subsets)
            if ontology_count == 1:
                explanation_parts.append("2. I searched through the relevant knowledge base")
            else:
                explanation_parts.append(f"2. I searched through {ontology_count} knowledge bases")

        # Result processing
        explanation_parts.append("3. I found the relevant information and generated your answer")

        # Conclusion
        explanation_parts.append(f"The answer is: {final_answer}")

        return " ".join(explanation_parts)

    def _extract_technical_details(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract technical details for debugging and optimization."""
        return {
            'query_optimization': metadata.get('query_optimization', {}),
            'backend_performance': metadata.get('backend_performance', {}),
            'cache_usage': metadata.get('cache_usage', {}),
            'error_handling': metadata.get('error_handling', {}),
            'routing_decision': metadata.get('routing_decision', {})
        }

    def format_explanation_for_display(self,
                                     explanation: QueryExplanation,
                                     format_type: str = 'html') -> str:
        """Format explanation for display.

        Args:
            explanation: Query explanation
            format_type: Output format ('html', 'markdown', 'text')

        Returns:
            Formatted explanation
        """
        if format_type == 'html':
            return self._format_html_explanation(explanation)
        elif format_type == 'markdown':
            return self._format_markdown_explanation(explanation)
        else:
            return self._format_text_explanation(explanation)

    def _format_html_explanation(self, explanation: QueryExplanation) -> str:
        """Format explanation as HTML."""
        html_parts = [
            f"<h2>Query Explanation: {explanation.query_id}</h2>",
            f"<p><strong>Question:</strong> {explanation.original_question}</p>",
            f"<p><strong>Answer:</strong> {explanation.final_answer}</p>",
            f"<p><strong>Confidence:</strong> {explanation.confidence_score:.1%}</p>",
            "<h3>Processing Steps:</h3>",
            "<ol>"
        ]

        for step in explanation.processing_steps:
            html_parts.append(f"<li><strong>{step.component}</strong>: {step.explanation}</li>")

        html_parts.extend([
            "</ol>",
            "<h3>Reasoning:</h3>",
            "<ul>"
        ])

        for reasoning in explanation.reasoning_chain:
            html_parts.append(f"<li>{reasoning}</li>")

        html_parts.append("</ul>")

        return "".join(html_parts)

    def _format_markdown_explanation(self, explanation: QueryExplanation) -> str:
        """Format explanation as Markdown."""
        md_parts = [
            f"## Query Explanation: {explanation.query_id}",
            f"**Question:** {explanation.original_question}",
            f"**Answer:** {explanation.final_answer}",
            f"**Confidence:** {explanation.confidence_score:.1%}",
            "",
            "### Processing Steps:",
            ""
        ]

        for i, step in enumerate(explanation.processing_steps, 1):
            md_parts.append(f"{i}. **{step.component}**: {step.explanation}")

        md_parts.extend([
            "",
            "### Reasoning:",
            ""
        ])

        for reasoning in explanation.reasoning_chain:
            md_parts.append(f"- {reasoning}")

        return "\n".join(md_parts)

    def _format_text_explanation(self, explanation: QueryExplanation) -> str:
        """Format explanation as plain text."""
        text_parts = [
            f"Query Explanation: {explanation.query_id}",
            f"Question: {explanation.original_question}",
            f"Answer: {explanation.final_answer}",
            f"Confidence: {explanation.confidence_score:.1%}",
            "",
            "Processing Steps:",
        ]

        for i, step in enumerate(explanation.processing_steps, 1):
            text_parts.append(f"  {i}. {step.component}: {step.explanation}")

        text_parts.extend([
            "",
            "Reasoning:",
        ])

        for reasoning in explanation.reasoning_chain:
            text_parts.append(f"  - {reasoning}")

        return "\n".join(text_parts)