"""
Ontology selection algorithm for OntoRAG system.
Selects relevant ontology subsets based on text similarity.
"""

import logging
from typing import List, Dict, Any, Set, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

from .ontology_loader import Ontology, OntologyLoader
from .ontology_embedder import OntologyEmbedder
from .text_processor import TextSegment
from .vector_store import SearchResult

logger = logging.getLogger(__name__)


@dataclass
class OntologySubset:
    """Represents a subset of an ontology relevant to a text chunk."""
    ontology_id: str
    classes: Dict[str, Any]
    object_properties: Dict[str, Any]
    datatype_properties: Dict[str, Any]
    metadata: Dict[str, Any]
    relevance_score: float = 0.0


class OntologySelector:
    """Selects relevant ontology elements for text segments using vector similarity."""

    def __init__(self, ontology_embedder: OntologyEmbedder,
                 ontology_loader: OntologyLoader,
                 top_k: int = 10,
                 similarity_threshold: float = 0.7):
        """Initialize the ontology selector.

        Args:
            ontology_embedder: Embedder with vector store
            ontology_loader: Loader with ontology definitions
            top_k: Number of top results to retrieve per segment
            similarity_threshold: Minimum similarity score
        """
        self.embedder = ontology_embedder
        self.loader = ontology_loader
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold

    async def select_ontology_subset(self, segments: List[TextSegment]) -> List[OntologySubset]:
        """Select relevant ontology subsets for text segments.

        Args:
            segments: List of text segments to match

        Returns:
            List of ontology subsets with relevant elements
        """
        # Collect all relevant elements
        relevant_elements = await self._find_relevant_elements(segments)

        # Group by ontology and build subsets
        ontology_subsets = self._build_ontology_subsets(relevant_elements)

        # Resolve dependencies
        for subset in ontology_subsets:
            self._resolve_dependencies(subset)

        logger.info(f"Selected {len(ontology_subsets)} ontology subsets")
        return ontology_subsets

    async def _find_relevant_elements(self, segments: List[TextSegment]) -> Set[Tuple[str, str, str, Dict]]:
        """Find relevant ontology elements for text segments.

        Args:
            segments: Text segments to match

        Returns:
            Set of (ontology_id, element_type, element_id, definition) tuples
        """
        relevant_elements = set()
        element_scores = defaultdict(float)

        # Process each segment
        for segment in segments:
            # Get embedding for segment
            embedding = await self.embedder.embed_text(segment.text)
            if embedding is None:
                logger.warning(f"Failed to embed segment: {segment.text[:50]}...")
                continue

            # Search vector store
            results = self.embedder.get_vector_store().search(
                embedding=embedding,
                top_k=self.top_k,
                threshold=self.similarity_threshold
            )

            # Process results
            for result in results:
                metadata = result.metadata
                element_key = (
                    metadata['ontology'],
                    metadata['type'],
                    metadata['element'],
                    str(metadata['definition'])  # Convert dict to string for hashability
                )
                relevant_elements.add(element_key)
                # Track scores for ranking
                element_scores[element_key] = max(element_scores[element_key], result.score)

        logger.debug(f"Found {len(relevant_elements)} relevant elements from {len(segments)} segments")
        return relevant_elements

    def _build_ontology_subsets(self, relevant_elements: Set[Tuple[str, str, str, Dict]]) -> List[OntologySubset]:
        """Build ontology subsets from relevant elements.

        Args:
            relevant_elements: Set of relevant element tuples

        Returns:
            List of ontology subsets
        """
        # Group elements by ontology
        ontology_groups = defaultdict(lambda: {
            'classes': {},
            'object_properties': {},
            'datatype_properties': {},
            'scores': []
        })

        for ont_id, elem_type, elem_id, definition in relevant_elements:
            # Parse definition back from string if needed
            if isinstance(definition, str):
                import json
                try:
                    definition = json.loads(definition.replace("'", '"'))
                except:
                    definition = eval(definition)  # Fallback for dict-like strings

            # Get the actual ontology and element
            ontology = self.loader.get_ontology(ont_id)
            if not ontology:
                logger.warning(f"Ontology {ont_id} not found in loader")
                continue

            # Add element to appropriate category
            if elem_type == 'class':
                cls = ontology.get_class(elem_id)
                if cls:
                    ontology_groups[ont_id]['classes'][elem_id] = cls.__dict__
            elif elem_type == 'objectProperty':
                prop = ontology.object_properties.get(elem_id)
                if prop:
                    ontology_groups[ont_id]['object_properties'][elem_id] = prop.__dict__
            elif elem_type == 'datatypeProperty':
                prop = ontology.datatype_properties.get(elem_id)
                if prop:
                    ontology_groups[ont_id]['datatype_properties'][elem_id] = prop.__dict__

        # Create OntologySubset objects
        subsets = []
        for ont_id, elements in ontology_groups.items():
            ontology = self.loader.get_ontology(ont_id)
            if ontology:
                subset = OntologySubset(
                    ontology_id=ont_id,
                    classes=elements['classes'],
                    object_properties=elements['object_properties'],
                    datatype_properties=elements['datatype_properties'],
                    metadata=ontology.metadata,
                    relevance_score=sum(elements['scores']) / len(elements['scores']) if elements['scores'] else 0.0
                )
                subsets.append(subset)

        return subsets

    def _resolve_dependencies(self, subset: OntologySubset):
        """Resolve dependencies for ontology subset elements.

        Args:
            subset: Ontology subset to resolve dependencies for
        """
        ontology = self.loader.get_ontology(subset.ontology_id)
        if not ontology:
            return

        # Track classes to add
        classes_to_add = set()

        # Resolve class hierarchies
        for class_id in list(subset.classes.keys()):
            # Add parent classes
            parents = ontology.get_parent_classes(class_id)
            for parent_id in parents:
                parent_class = ontology.get_class(parent_id)
                if parent_class and parent_id not in subset.classes:
                    classes_to_add.add(parent_id)

        # Resolve property domains and ranges
        for prop_id, prop_def in subset.object_properties.items():
            # Add domain class
            if 'domain' in prop_def and prop_def['domain']:
                domain_id = prop_def['domain']
                if domain_id not in subset.classes:
                    domain_class = ontology.get_class(domain_id)
                    if domain_class:
                        classes_to_add.add(domain_id)

            # Add range class
            if 'range' in prop_def and prop_def['range']:
                range_id = prop_def['range']
                if range_id not in subset.classes:
                    range_class = ontology.get_class(range_id)
                    if range_class:
                        classes_to_add.add(range_id)

        # Resolve datatype property domains
        for prop_id, prop_def in subset.datatype_properties.items():
            if 'domain' in prop_def and prop_def['domain']:
                domain_id = prop_def['domain']
                if domain_id not in subset.classes:
                    domain_class = ontology.get_class(domain_id)
                    if domain_class:
                        classes_to_add.add(domain_id)

        # Add inverse properties
        for prop_id, prop_def in list(subset.object_properties.items()):
            if 'inverse_of' in prop_def and prop_def['inverse_of']:
                inverse_id = prop_def['inverse_of']
                if inverse_id not in subset.object_properties:
                    inverse_prop = ontology.object_properties.get(inverse_id)
                    if inverse_prop:
                        subset.object_properties[inverse_id] = inverse_prop.__dict__

        # Add collected classes
        for class_id in classes_to_add:
            cls = ontology.get_class(class_id)
            if cls:
                subset.classes[class_id] = cls.__dict__

        logger.debug(f"Resolved dependencies for subset {subset.ontology_id}: "
                    f"added {len(classes_to_add)} classes")

    def merge_subsets(self, subsets: List[OntologySubset]) -> OntologySubset:
        """Merge multiple ontology subsets into one.

        Args:
            subsets: List of subsets to merge

        Returns:
            Merged ontology subset
        """
        if not subsets:
            return None
        if len(subsets) == 1:
            return subsets[0]

        # Use first subset as base
        merged = OntologySubset(
            ontology_id="merged",
            classes={},
            object_properties={},
            datatype_properties={},
            metadata={},
            relevance_score=0.0
        )

        # Merge all subsets
        total_score = 0.0
        for subset in subsets:
            # Merge classes
            for class_id, class_def in subset.classes.items():
                key = f"{subset.ontology_id}:{class_id}"
                merged.classes[key] = class_def

            # Merge object properties
            for prop_id, prop_def in subset.object_properties.items():
                key = f"{subset.ontology_id}:{prop_id}"
                merged.object_properties[key] = prop_def

            # Merge datatype properties
            for prop_id, prop_def in subset.datatype_properties.items():
                key = f"{subset.ontology_id}:{prop_id}"
                merged.datatype_properties[key] = prop_def

            total_score += subset.relevance_score

        # Average relevance score
        merged.relevance_score = total_score / len(subsets)

        logger.info(f"Merged {len(subsets)} subsets into one with "
                   f"{len(merged.classes)} classes, "
                   f"{len(merged.object_properties)} object properties, "
                   f"{len(merged.datatype_properties)} datatype properties")

        return merged