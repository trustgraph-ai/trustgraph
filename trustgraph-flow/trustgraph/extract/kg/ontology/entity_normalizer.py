"""
Entity URI normalization for ontology-based knowledge extraction.

Converts entity names and types into consistent, collision-free URIs.
"""

import re
from typing import Tuple


def normalize_entity_name(entity_name: str) -> str:
    """Normalize entity name to URI-safe identifier.

    Args:
        entity_name: Natural language entity name (e.g., "Cornish pasty")

    Returns:
        Normalized identifier (e.g., "cornish-pasty")
    """
    # Convert to lowercase
    normalized = entity_name.lower()

    # Replace spaces and underscores with hyphens
    normalized = re.sub(r'[\s_]+', '-', normalized)

    # Remove any characters that aren't alphanumeric, hyphens, or periods
    normalized = re.sub(r'[^a-z0-9\-.]', '', normalized)

    # Remove leading/trailing hyphens
    normalized = normalized.strip('-')

    # Collapse multiple hyphens
    normalized = re.sub(r'-+', '-', normalized)

    return normalized


def normalize_type_identifier(type_id: str) -> str:
    """Normalize ontology type identifier to URI-safe format.

    Handles prefixed types like "fo/Recipe" by converting to "fo-recipe".

    Args:
        type_id: Ontology type identifier (e.g., "fo/Recipe", "Food")

    Returns:
        Normalized type identifier (e.g., "fo-recipe", "food")
    """
    # Convert to lowercase
    normalized = type_id.lower()

    # Replace slashes, colons, and spaces with hyphens
    normalized = re.sub(r'[/:.\s_]+', '-', normalized)

    # Remove any remaining non-alphanumeric characters except hyphens
    normalized = re.sub(r'[^a-z0-9\-]', '', normalized)

    # Remove leading/trailing hyphens
    normalized = normalized.strip('-')

    # Collapse multiple hyphens
    normalized = re.sub(r'-+', '-', normalized)

    return normalized


def build_entity_uri(entity_name: str, entity_type: str, ontology_id: str,
                    base_uri: str = "https://trustgraph.ai") -> str:
    """Build a unique URI for an entity based on its name and type.

    The type is included in the URI to prevent collisions when the same
    name refers to different entity types (e.g., "Cornish pasty" as both
    Recipe and Food).

    Args:
        entity_name: Natural language entity name (e.g., "Cornish pasty")
        entity_type: Ontology type (e.g., "fo/Recipe")
        ontology_id: Ontology identifier (e.g., "food")
        base_uri: Base URI for entity URIs (default: "https://trustgraph.ai")

    Returns:
        Full entity URI (e.g., "https://trustgraph.ai/food/fo-recipe-cornish-pasty")

    Examples:
        >>> build_entity_uri("Cornish pasty", "fo/Recipe", "food")
        'https://trustgraph.ai/food/fo-recipe-cornish-pasty'

        >>> build_entity_uri("Cornish pasty", "fo/Food", "food")
        'https://trustgraph.ai/food/fo-food-cornish-pasty'

        >>> build_entity_uri("beef", "fo/Food", "food")
        'https://trustgraph.ai/food/fo-food-beef'
    """
    type_part = normalize_type_identifier(entity_type)
    name_part = normalize_entity_name(entity_name)

    # Combine type and name to ensure uniqueness
    entity_id = f"{type_part}-{name_part}"

    # Build full URI
    return f"{base_uri}/{ontology_id}/{entity_id}"


class EntityRegistry:
    """Registry to track entity name/type tuples and their assigned URIs.

    Ensures that the same (entity_name, entity_type) tuple always maps
    to the same URI, enabling deduplication across the extraction process.
    """

    def __init__(self, ontology_id: str, base_uri: str = "https://trustgraph.ai"):
        """Initialize the entity registry.

        Args:
            ontology_id: Ontology identifier (e.g., "food")
            base_uri: Base URI for entity URIs
        """
        self.ontology_id = ontology_id
        self.base_uri = base_uri
        self._registry = {}  # (entity_name, entity_type) -> uri

    def get_or_create_uri(self, entity_name: str, entity_type: str) -> str:
        """Get existing URI or create new one for entity.

        Args:
            entity_name: Natural language entity name
            entity_type: Ontology type identifier

        Returns:
            URI for this entity (same URI for same name/type tuple)
        """
        key = (entity_name, entity_type)

        if key not in self._registry:
            uri = build_entity_uri(
                entity_name,
                entity_type,
                self.ontology_id,
                self.base_uri
            )
            self._registry[key] = uri

        return self._registry[key]

    def lookup(self, entity_name: str, entity_type: str) -> str:
        """Look up URI for entity (returns None if not registered).

        Args:
            entity_name: Natural language entity name
            entity_type: Ontology type identifier

        Returns:
            URI for this entity, or None if not found
        """
        key = (entity_name, entity_type)
        return self._registry.get(key)

    def clear(self):
        """Clear all registered entities."""
        self._registry.clear()

    def size(self) -> int:
        """Get number of registered entities."""
        return len(self._registry)
