"""
Converts simplified extraction format to RDF triples.

Transforms entities, relationships, and attributes into proper RDF triples
with full URIs and correct is_uri flags.
"""

import logging
from typing import List, Optional, Set

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

    def _get_ancestor_classes(self, class_id: str) -> Set[str]:
        ancestors = set()
        current = class_id
        while current:
            cls_def = self.ontology_subset.classes.get(current)
            if not cls_def:
                break
            parent = cls_def.get("subclass_of") if isinstance(cls_def, dict) else getattr(cls_def, "subclass_of", None)
            if not parent or parent in ancestors:
                break
            ancestors.add(parent)
            current = parent
        return ancestors

    def _matches_class_constraint(self, actual_type: str, expected_type: str) -> bool:
        if actual_type == expected_type:
            return True
        return expected_type in self._get_ancestor_classes(actual_type)

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

        # Enforce domain/range constraints when declared
        prop_def = self.ontology_subset.object_properties.get(
            relationship.relation, {}
        )
        domain = prop_def.get("domain") if isinstance(prop_def, dict) else getattr(prop_def, "domain", None)
        range_ = prop_def.get("range") if isinstance(prop_def, dict) else getattr(prop_def, "range", None)

        if domain and not self._matches_class_constraint(relationship.subject_type, domain):
            logger.warning(
                f"Domain violation: '{relationship.relation}' expects "
                f"domain '{domain}', got subject type "
                f"'{relationship.subject_type}', skipping"
            )
            return None

        if range_ and not self._matches_class_constraint(relationship.object_type, range_):
            logger.warning(
                f"Range violation: '{relationship.relation}' expects "
                f"range '{range_}', got object type "
                f"'{relationship.object_type}', skipping"
            )
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

        # Enforce domain constraint when declared
        prop_def = self.ontology_subset.datatype_properties.get(
            attribute.attribute, {}
        )
        domain = prop_def.get("domain") if isinstance(prop_def, dict) else getattr(prop_def, "domain", None)

        if domain and not self._matches_class_constraint(attribute.entity_type, domain):
            logger.warning(
                f"Domain violation: attribute '{attribute.attribute}' "
                f"expects domain '{domain}', got entity type "
                f"'{attribute.entity_type}', skipping"
            )
            return None

        # Generate triple: entity property "literal value"
        return Triple(
            s=Term(type=IRI, iri=entity_uri),
            p=Term(type=IRI, iri=property_uri),
            o=Term(type=LITERAL, value=attribute.value)
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
