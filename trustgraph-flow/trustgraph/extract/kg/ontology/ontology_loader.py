"""
Ontology loader component for OntoRAG system.
Loads and manages ontologies from configuration service.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class OntologyClass:
    """Represents an OWL-like class in the ontology."""
    uri: str
    type: str = "owl:Class"
    labels: List[Dict[str, str]] = field(default_factory=list)
    comment: Optional[str] = None
    subclass_of: Optional[str] = None
    equivalent_classes: List[str] = field(default_factory=list)
    disjoint_with: List[str] = field(default_factory=list)
    identifier: Optional[str] = None

    @staticmethod
    def from_dict(class_id: str, data: Dict[str, Any]) -> 'OntologyClass':
        """Create OntologyClass from dictionary representation."""
        labels = data.get('rdfs:label', [])
        if isinstance(labels, list):
            labels = labels
        else:
            labels = [labels] if labels else []

        return OntologyClass(
            uri=data.get('uri', ''),
            type=data.get('type', 'owl:Class'),
            labels=labels,
            comment=data.get('rdfs:comment'),
            subclass_of=data.get('rdfs:subClassOf'),
            equivalent_classes=data.get('owl:equivalentClass', []),
            disjoint_with=data.get('owl:disjointWith', []),
            identifier=data.get('dcterms:identifier')
        )


@dataclass
class OntologyProperty:
    """Represents a property (object or datatype) in the ontology."""
    uri: str
    type: str
    labels: List[Dict[str, str]] = field(default_factory=list)
    comment: Optional[str] = None
    domain: Optional[str] = None
    range: Optional[str] = None
    inverse_of: Optional[str] = None
    functional: bool = False
    inverse_functional: bool = False
    min_cardinality: Optional[int] = None
    max_cardinality: Optional[int] = None
    cardinality: Optional[int] = None

    @staticmethod
    def from_dict(prop_id: str, data: Dict[str, Any]) -> 'OntologyProperty':
        """Create OntologyProperty from dictionary representation."""
        labels = data.get('rdfs:label', [])
        if isinstance(labels, list):
            labels = labels
        else:
            labels = [labels] if labels else []

        return OntologyProperty(
            uri=data.get('uri', ''),
            type=data.get('type', ''),
            labels=labels,
            comment=data.get('rdfs:comment'),
            domain=data.get('rdfs:domain'),
            range=data.get('rdfs:range'),
            inverse_of=data.get('owl:inverseOf'),
            functional=data.get('owl:functionalProperty', False),
            inverse_functional=data.get('owl:inverseFunctionalProperty', False),
            min_cardinality=data.get('owl:minCardinality'),
            max_cardinality=data.get('owl:maxCardinality'),
            cardinality=data.get('owl:cardinality')
        )


@dataclass
class Ontology:
    """Represents a complete ontology with metadata, classes, and properties."""
    id: str
    metadata: Dict[str, Any]
    classes: Dict[str, OntologyClass]
    object_properties: Dict[str, OntologyProperty]
    datatype_properties: Dict[str, OntologyProperty]

    def get_class(self, class_id: str) -> Optional[OntologyClass]:
        """Get a class by ID."""
        return self.classes.get(class_id)

    def get_property(self, prop_id: str) -> Optional[OntologyProperty]:
        """Get a property (object or datatype) by ID."""
        prop = self.object_properties.get(prop_id)
        if prop is None:
            prop = self.datatype_properties.get(prop_id)
        return prop

    def get_parent_classes(self, class_id: str) -> List[str]:
        """Get all parent classes (following subClassOf hierarchy)."""
        parents = []
        current = class_id
        visited = set()

        while current and current not in visited:
            visited.add(current)
            cls = self.get_class(current)
            if cls and cls.subclass_of:
                parents.append(cls.subclass_of)
                current = cls.subclass_of
            else:
                break

        return parents

    def validate_structure(self) -> List[str]:
        """Validate ontology structure and return list of issues."""
        issues = []

        # Check for circular inheritance
        for class_id in self.classes:
            visited = set()
            current = class_id
            while current:
                if current in visited:
                    issues.append(f"Circular inheritance detected for class {class_id}")
                    break
                visited.add(current)
                cls = self.get_class(current)
                if cls:
                    current = cls.subclass_of
                else:
                    break

        # Check property domains and ranges exist
        for prop_id, prop in {**self.object_properties, **self.datatype_properties}.items():
            if prop.domain and prop.domain not in self.classes:
                issues.append(f"Property {prop_id} has unknown domain {prop.domain}")
            if prop.type == "owl:ObjectProperty" and prop.range and prop.range not in self.classes:
                issues.append(f"Object property {prop_id} has unknown range class {prop.range}")

        # Check disjoint classes
        for class_id, cls in self.classes.items():
            for disjoint_id in cls.disjoint_with:
                if disjoint_id not in self.classes:
                    issues.append(f"Class {class_id} disjoint with unknown class {disjoint_id}")

        return issues


class OntologyLoader:
    """Loads and manages ontologies from configuration service."""

    def __init__(self, config_store=None):
        """Initialize the ontology loader.

        Args:
            config_store: Configuration store instance (injected dependency)
        """
        self.config_store = config_store
        self.ontologies: Dict[str, Ontology] = {}
        self.refresh_interval = 300  # Default 5 minutes

    async def load_ontologies(self) -> Dict[str, Ontology]:
        """Load all ontologies from configuration service.

        Returns:
            Dictionary of ontology ID to Ontology objects
        """
        if not self.config_store:
            logger.warning("No configuration store available, returning empty ontologies")
            return {}

        try:
            # Get all ontology configurations
            ontology_configs = await self.config_store.get("ontology").values()

            for ont_id, ont_data in ontology_configs.items():
                try:
                    # Parse JSON if string
                    if isinstance(ont_data, str):
                        ont_data = json.loads(ont_data)

                    # Parse classes
                    classes = {}
                    for class_id, class_data in ont_data.get('classes', {}).items():
                        classes[class_id] = OntologyClass.from_dict(class_id, class_data)

                    # Parse object properties
                    object_props = {}
                    for prop_id, prop_data in ont_data.get('objectProperties', {}).items():
                        object_props[prop_id] = OntologyProperty.from_dict(prop_id, prop_data)

                    # Parse datatype properties
                    datatype_props = {}
                    for prop_id, prop_data in ont_data.get('datatypeProperties', {}).items():
                        datatype_props[prop_id] = OntologyProperty.from_dict(prop_id, prop_data)

                    # Create ontology
                    ontology = Ontology(
                        id=ont_id,
                        metadata=ont_data.get('metadata', {}),
                        classes=classes,
                        object_properties=object_props,
                        datatype_properties=datatype_props
                    )

                    # Validate structure
                    issues = ontology.validate_structure()
                    if issues:
                        logger.warning(f"Ontology {ont_id} has validation issues: {issues}")

                    self.ontologies[ont_id] = ontology
                    logger.info(f"Loaded ontology {ont_id} with {len(classes)} classes, "
                               f"{len(object_props)} object properties, "
                               f"{len(datatype_props)} datatype properties")

                except Exception as e:
                    logger.error(f"Failed to load ontology {ont_id}: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Failed to load ontologies from config: {e}", exc_info=True)

        return self.ontologies

    async def refresh_ontologies(self):
        """Refresh ontologies from configuration service."""
        logger.info("Refreshing ontologies...")
        return await self.load_ontologies()

    def get_ontology(self, ont_id: str) -> Optional[Ontology]:
        """Get a specific ontology by ID.

        Args:
            ont_id: Ontology identifier

        Returns:
            Ontology object or None if not found
        """
        return self.ontologies.get(ont_id)

    def get_all_ontologies(self) -> Dict[str, Ontology]:
        """Get all loaded ontologies.

        Returns:
            Dictionary of ontology ID to Ontology objects
        """
        return self.ontologies

    def clear(self):
        """Clear all loaded ontologies."""
        self.ontologies.clear()
        logger.info("Cleared all loaded ontologies")