"""
Ontology matcher for query system.
Identifies relevant ontology subsets for answering questions.
"""

import logging
from typing import List, Dict, Any, Set, Optional
from dataclasses import dataclass

from ...extract.kg.ontology.ontology_loader import Ontology, OntologyLoader
from ...extract.kg.ontology.ontology_embedder import OntologyEmbedder
from ...extract.kg.ontology.text_processor import TextSegment
from ...extract.kg.ontology.ontology_selector import OntologySelector, OntologySubset
from .question_analyzer import QuestionComponents, QuestionType

logger = logging.getLogger(__name__)


@dataclass
class QueryOntologySubset(OntologySubset):
    """Extended ontology subset for query processing."""
    traversal_properties: Dict[str, Any] = None  # Additional properties for graph traversal
    inference_rules: List[Dict[str, Any]] = None  # Inference rules for reasoning


class OntologyMatcherForQueries(OntologySelector):
    """
    Specialized ontology matcher for question answering.
    Extends OntologySelector with query-specific logic.
    """

    def __init__(self, ontology_embedder: OntologyEmbedder,
                 ontology_loader: OntologyLoader,
                 top_k: int = 15,  # Higher k for queries
                 similarity_threshold: float = 0.6):  # Lower threshold for broader coverage
        """Initialize query-specific ontology matcher.

        Args:
            ontology_embedder: Embedder with vector store
            ontology_loader: Loader with ontology definitions
            top_k: Number of top results to retrieve
            similarity_threshold: Minimum similarity score
        """
        super().__init__(ontology_embedder, ontology_loader, top_k, similarity_threshold)

    async def match_question_to_ontology(self,
                                        question_components: QuestionComponents,
                                        question_segments: List[str]) -> List[QueryOntologySubset]:
        """Match question components to relevant ontology elements.

        Args:
            question_components: Analyzed question components
            question_segments: Text segments from question

        Returns:
            List of query-optimized ontology subsets
        """
        # Convert question segments to TextSegment objects
        text_segments = [
            TextSegment(text=seg, type='question', position=i)
            for i, seg in enumerate(question_segments)
        ]

        # Get base ontology subsets using parent class method
        base_subsets = await self.select_ontology_subset(text_segments)

        # Enhance subsets for query processing
        query_subsets = []
        for subset in base_subsets:
            query_subset = self._enhance_for_query(subset, question_components)
            query_subsets.append(query_subset)

        return query_subsets

    def _enhance_for_query(self, subset: OntologySubset,
                          question_components: QuestionComponents) -> QueryOntologySubset:
        """Enhance ontology subset with query-specific elements.

        Args:
            subset: Base ontology subset
            question_components: Analyzed question components

        Returns:
            Enhanced query ontology subset
        """
        # Create query subset
        query_subset = QueryOntologySubset(
            ontology_id=subset.ontology_id,
            classes=dict(subset.classes),
            object_properties=dict(subset.object_properties),
            datatype_properties=dict(subset.datatype_properties),
            metadata=subset.metadata,
            relevance_score=subset.relevance_score,
            traversal_properties={},
            inference_rules=[]
        )

        # Add traversal properties based on question type
        self._add_traversal_properties(query_subset, question_components)

        # Add related properties for exploration
        self._add_related_properties(query_subset)

        # Add inference rules if needed
        self._add_inference_rules(query_subset, question_components)

        return query_subset

    def _add_traversal_properties(self, subset: QueryOntologySubset,
                                 question_components: QuestionComponents):
        """Add properties useful for graph traversal.

        Args:
            subset: Query ontology subset to enhance
            question_components: Question analysis
        """
        ontology = self.loader.get_ontology(subset.ontology_id)
        if not ontology:
            return

        # For relationship questions, add all properties connecting mentioned classes
        if question_components.question_type == QuestionType.RELATIONSHIP:
            for prop_id, prop_def in ontology.object_properties.items():
                domain = prop_def.domain
                range_val = prop_def.range

                # Check if property connects relevant classes
                if domain in subset.classes or range_val in subset.classes:
                    if prop_id not in subset.object_properties:
                        subset.traversal_properties[prop_id] = prop_def.__dict__
                        logger.debug(f"Added traversal property: {prop_id}")

        # For retrieval questions, add properties that might filter results
        elif question_components.question_type == QuestionType.RETRIEVAL:
            # Add all properties with domains in our classes
            for prop_id, prop_def in ontology.object_properties.items():
                if prop_def.domain in subset.classes:
                    if prop_id not in subset.object_properties:
                        subset.traversal_properties[prop_id] = prop_def.__dict__

            for prop_id, prop_def in ontology.datatype_properties.items():
                if prop_def.domain in subset.classes:
                    if prop_id not in subset.datatype_properties:
                        subset.traversal_properties[prop_id] = prop_def.__dict__

        # For aggregation questions, ensure we have counting properties
        elif question_components.question_type == QuestionType.AGGREGATION:
            # Add properties that might be counted
            for prop_id, prop_def in ontology.datatype_properties.items():
                if 'count' in prop_id.lower() or 'number' in prop_id.lower():
                    if prop_id not in subset.datatype_properties:
                        subset.traversal_properties[prop_id] = prop_def.__dict__

    def _add_related_properties(self, subset: QueryOntologySubset):
        """Add properties related to already selected ones.

        Args:
            subset: Query ontology subset to enhance
        """
        ontology = self.loader.get_ontology(subset.ontology_id)
        if not ontology:
            return

        # Add inverse properties
        for prop_id in list(subset.object_properties.keys()):
            prop = ontology.object_properties.get(prop_id)
            if prop and prop.inverse_of:
                inverse_prop = ontology.object_properties.get(prop.inverse_of)
                if inverse_prop and prop.inverse_of not in subset.object_properties:
                    subset.object_properties[prop.inverse_of] = inverse_prop.__dict__
                    logger.debug(f"Added inverse property: {prop.inverse_of}")

        # Add sibling properties (same domain)
        domains_in_subset = set()
        for prop_def in subset.object_properties.values():
            if 'domain' in prop_def and prop_def['domain']:
                domains_in_subset.add(prop_def['domain'])

        for domain in domains_in_subset:
            for prop_id, prop_def in ontology.object_properties.items():
                if prop_def.domain == domain and prop_id not in subset.object_properties:
                    # Add up to 3 sibling properties
                    if len(subset.traversal_properties) < 3:
                        subset.traversal_properties[prop_id] = prop_def.__dict__

    def _add_inference_rules(self, subset: QueryOntologySubset,
                            question_components: QuestionComponents):
        """Add inference rules for reasoning.

        Args:
            subset: Query ontology subset to enhance
            question_components: Question analysis
        """
        # Add transitivity rules for subclass relationships
        if any(cls.get('subclass_of') for cls in subset.classes.values()):
            subset.inference_rules.append({
                'type': 'transitivity',
                'property': 'rdfs:subClassOf',
                'description': 'Subclass relationships are transitive'
            })

        # Add symmetry rules for equivalent classes
        if any(cls.get('equivalent_classes') for cls in subset.classes.values()):
            subset.inference_rules.append({
                'type': 'symmetry',
                'property': 'owl:equivalentClass',
                'description': 'Equivalent class relationships are symmetric'
            })

        # Add inverse property rules
        for prop_id, prop_def in subset.object_properties.items():
            if 'inverse_of' in prop_def and prop_def['inverse_of']:
                subset.inference_rules.append({
                    'type': 'inverse',
                    'property': prop_id,
                    'inverse': prop_def['inverse_of'],
                    'description': f'{prop_id} is inverse of {prop_def["inverse_of"]}'
                })

    def expand_for_hierarchical_queries(self, subset: QueryOntologySubset) -> QueryOntologySubset:
        """Expand subset to include full class hierarchies.

        Args:
            subset: Query ontology subset

        Returns:
            Expanded subset with complete hierarchies
        """
        ontology = self.loader.get_ontology(subset.ontology_id)
        if not ontology:
            return subset

        # Add all parent and child classes
        classes_to_add = set()
        for class_id in list(subset.classes.keys()):
            # Add all parents
            parents = ontology.get_parent_classes(class_id)
            for parent_id in parents:
                if parent_id not in subset.classes:
                    parent_class = ontology.get_class(parent_id)
                    if parent_class:
                        classes_to_add.add(parent_id)

            # Add all children
            for other_class_id, other_class in ontology.classes.items():
                if other_class.subclass_of == class_id and other_class_id not in subset.classes:
                    classes_to_add.add(other_class_id)

        # Add collected classes
        for class_id in classes_to_add:
            cls = ontology.get_class(class_id)
            if cls:
                subset.classes[class_id] = cls.__dict__

        logger.debug(f"Expanded hierarchy: added {len(classes_to_add)} classes")
        return subset