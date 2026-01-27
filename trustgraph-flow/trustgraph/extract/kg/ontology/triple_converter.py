"""
Converts simplified extraction format to RDF triples.

Transforms entities, relationships, and attributes into proper RDF triples
with full URIs and correct is_uri flags.
"""

import logging
from typing import List, Optional

from .... schema import Triple, Term, IRI, LITERAL
from .... rdf import RDF_TYPE, RDF_LABEL

from .simplified_parser import Entity, Relationship, Attribute, ExtractionResult
from .entity_normalizer import EntityRegistry
from .ontology_selector import OntologySubset

logger = logging.getLogger(__name__)


class TripleConverter:
    """Converts extraction results to RDF triples."""

    def __init__(self, ontology_subset: OntologySubset, ontology_id: str):
        """Initialize converter.

        Args:
            ontology_subset: Ontology subset with classes and properties
            ontology_id: Ontology identifier for URI generation
        """
        self.ontology_subset = ontology_subset
        self.ontology_id = ontology_id
        self.entity_registry = EntityRegistry(ontology_id)

    def convert_all(self, extraction: ExtractionResult) -> List[Triple]:
        """Convert complete extraction result to RDF triples.

        Args:
            extraction: Parsed extraction with entities/relationships/attributes

        Returns:
            List of RDF Triple objects
        """
        triples = []

        # Convert entities (generates type + label triples)
        for entity in extraction.entities:
            entity_triples = self.convert_entity(entity)
            triples.extend(entity_triples)

        # Convert relationships
        for relationship in extraction.relationships:
            rel_triple = self.convert_relationship(relationship)
            if rel_triple:
                triples.append(rel_triple)

        # Convert attributes
        for attribute in extraction.attributes:
            attr_triple = self.convert_attribute(attribute)
            if attr_triple:
                triples.append(attr_triple)

        return triples

    def convert_entity(self, entity: Entity) -> List[Triple]:
        """Convert entity to RDF triples (type + label).

        Args:
            entity: Entity object with name and type

        Returns:
            List containing type triple and label triple
        """
        triples = []

        # Get or create URI for this entity
        entity_uri = self.entity_registry.get_or_create_uri(
            entity.entity,
            entity.type
        )

        # Look up class URI from ontology
        class_uri = self._get_class_uri(entity.type)
        if not class_uri:
            logger.warning(f"Unknown entity type '{entity.type}', skipping entity '{entity.entity}'")
            return triples

        # Generate type triple: entity rdf:type ClassURI
        type_triple = Triple(
            s=Term(type=IRI, iri=entity_uri),
            p=Term(type=IRI, iri=RDF_TYPE),
            o=Term(type=IRI, iri=class_uri)
        )
        triples.append(type_triple)

        # Generate label triple: entity rdfs:label "entity name"
        label_triple = Triple(
            s=Term(type=IRI, iri=entity_uri),
            p=Term(type=IRI, iri=RDF_LABEL),
            o=Term(type=LITERAL, value=entity.entity)  # Literal!
        )
        triples.append(label_triple)

        return triples

    def convert_relationship(self, relationship: Relationship) -> Optional[Triple]:
        """Convert relationship to RDF triple.

        Args:
            relationship: Relationship with subject/object entities and relation

        Returns:
            Triple connecting two entity URIs via property URI, or None if invalid
        """
        # Get URIs for subject and object entities
        subject_uri = self.entity_registry.get_or_create_uri(
            relationship.subject,
            relationship.subject_type
        )

        object_uri = self.entity_registry.get_or_create_uri(
            relationship.object,
            relationship.object_type
        )

        # Look up property URI from ontology
        property_uri = self._get_object_property_uri(relationship.relation)
        if not property_uri:
            logger.warning(f"Unknown relationship '{relationship.relation}', skipping")
            return None

        # Generate triple: subject property object
        return Triple(
            s=Term(type=IRI, iri=subject_uri),
            p=Term(type=IRI, iri=property_uri),
            o=Term(type=IRI, iri=object_uri)
        )

    def convert_attribute(self, attribute: Attribute) -> Optional[Triple]:
        """Convert attribute to RDF triple.

        Args:
            attribute: Attribute with entity, attribute name, and literal value

        Returns:
            Triple with entity URI, property URI, and literal value, or None if invalid
        """
        # Get URI for entity
        entity_uri = self.entity_registry.get_or_create_uri(
            attribute.entity,
            attribute.entity_type
        )

        # Look up property URI from ontology
        property_uri = self._get_datatype_property_uri(attribute.attribute)
        if not property_uri:
            logger.warning(f"Unknown attribute '{attribute.attribute}', skipping")
            return None

        # Generate triple: entity property "literal value"
        return Triple(
            s=Term(type=IRI, iri=entity_uri),
            p=Term(type=IRI, iri=property_uri),
            o=Term(type=LITERAL, value=attribute.value)  # Literal!
        )

    def _get_class_uri(self, class_id: str) -> Optional[str]:
        """Get full URI for ontology class.

        Args:
            class_id: Class identifier (e.g., "fo/Recipe")

        Returns:
            Full class URI or None if not found
        """
        if class_id not in self.ontology_subset.classes:
            return None

        class_def = self.ontology_subset.classes[class_id]

        # Extract URI from class definition
        if isinstance(class_def, dict) and 'uri' in class_def:
            return class_def['uri']

        # Fallback: construct URI
        return f"https://trustgraph.ai/ontology/{self.ontology_id}#{class_id}"

    def _get_object_property_uri(self, property_id: str) -> Optional[str]:
        """Get full URI for object property.

        Args:
            property_id: Property identifier (e.g., "fo/has_ingredient")

        Returns:
            Full property URI or None if not found
        """
        if property_id not in self.ontology_subset.object_properties:
            return None

        prop_def = self.ontology_subset.object_properties[property_id]

        # Extract URI from property definition
        if isinstance(prop_def, dict) and 'uri' in prop_def:
            return prop_def['uri']

        # Fallback: construct URI
        return f"https://trustgraph.ai/ontology/{self.ontology_id}#{property_id}"

    def _get_datatype_property_uri(self, property_id: str) -> Optional[str]:
        """Get full URI for datatype property.

        Args:
            property_id: Property identifier (e.g., "fo/serves")

        Returns:
            Full property URI or None if not found
        """
        if property_id not in self.ontology_subset.datatype_properties:
            return None

        prop_def = self.ontology_subset.datatype_properties[property_id]

        # Extract URI from property definition
        if isinstance(prop_def, dict) and 'uri' in prop_def:
            return prop_def['uri']

        # Fallback: construct URI
        return f"https://trustgraph.ai/ontology/{self.ontology_id}#{property_id}"
