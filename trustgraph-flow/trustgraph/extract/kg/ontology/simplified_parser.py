"""
Parser for simplified ontology extraction JSON format.

Parses the new entity-relationship-attribute format from LLM responses.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Entity:
    """Represents an extracted entity."""
    entity: str
    type: str


@dataclass
class Relationship:
    """Represents an extracted relationship."""
    subject: str
    subject_type: str
    relation: str
    object: str
    object_type: str


@dataclass
class Attribute:
    """Represents an extracted attribute."""
    entity: str
    entity_type: str
    attribute: str
    value: str


@dataclass
class ExtractionResult:
    """Complete extraction result."""
    entities: List[Entity]
    relationships: List[Relationship]
    attributes: List[Attribute]


def parse_extraction_response(response: Any) -> Optional[ExtractionResult]:
    """Parse LLM extraction response into structured format.

    Args:
        response: LLM response (string JSON or already parsed dict)

    Returns:
        ExtractionResult with parsed entities/relationships/attributes,
        or None if parsing fails
    """
    # Handle string response (parse JSON)
    if isinstance(response, str):
        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response was: {response[:500]}")
            return None
    elif isinstance(response, dict):
        data = response
    else:
        logger.error(f"Unexpected response type: {type(response)}")
        return None

    # Validate structure
    if not isinstance(data, dict):
        logger.error(f"Expected dict, got {type(data)}")
        return None

    # Parse entities
    entities = []
    entities_data = data.get('entities', [])
    if not isinstance(entities_data, list):
        logger.warning(f"'entities' is not a list: {type(entities_data)}")
        entities_data = []

    for entity_data in entities_data:
        try:
            entity = parse_entity(entity_data)
            if entity:
                entities.append(entity)
        except Exception as e:
            logger.warning(f"Failed to parse entity {entity_data}: {e}")

    # Parse relationships
    relationships = []
    relationships_data = data.get('relationships', [])
    if not isinstance(relationships_data, list):
        logger.warning(f"'relationships' is not a list: {type(relationships_data)}")
        relationships_data = []

    for rel_data in relationships_data:
        try:
            relationship = parse_relationship(rel_data)
            if relationship:
                relationships.append(relationship)
        except Exception as e:
            logger.warning(f"Failed to parse relationship {rel_data}: {e}")

    # Parse attributes
    attributes = []
    attributes_data = data.get('attributes', [])
    if not isinstance(attributes_data, list):
        logger.warning(f"'attributes' is not a list: {type(attributes_data)}")
        attributes_data = []

    for attr_data in attributes_data:
        try:
            attribute = parse_attribute(attr_data)
            if attribute:
                attributes.append(attribute)
        except Exception as e:
            logger.warning(f"Failed to parse attribute {attr_data}: {e}")

    return ExtractionResult(
        entities=entities,
        relationships=relationships,
        attributes=attributes
    )


def parse_entity(data: Dict[str, Any]) -> Optional[Entity]:
    """Parse entity from dict.

    Supports both kebab-case and snake_case field names for compatibility.

    Args:
        data: Entity dict with 'entity' and 'type' fields

    Returns:
        Entity object or None if invalid
    """
    if not isinstance(data, dict):
        logger.warning(f"Entity data is not a dict: {type(data)}")
        return None

    entity = data.get('entity')
    entity_type = data.get('type')

    if not entity or not entity_type:
        logger.warning(f"Missing required fields in entity: {data}")
        return None

    if not isinstance(entity, str) or not isinstance(entity_type, str):
        logger.warning(f"Entity fields must be strings: {data}")
        return None

    return Entity(entity=entity, type=entity_type)


def parse_relationship(data: Dict[str, Any]) -> Optional[Relationship]:
    """Parse relationship from dict.

    Supports both kebab-case and snake_case field names for compatibility.

    Args:
        data: Relationship dict with subject, subject-type, relation, object, object-type

    Returns:
        Relationship object or None if invalid
    """
    if not isinstance(data, dict):
        logger.warning(f"Relationship data is not a dict: {type(data)}")
        return None

    subject = data.get('subject')
    subject_type = data.get('subject-type') or data.get('subject_type')
    relation = data.get('relation')
    obj = data.get('object')
    object_type = data.get('object-type') or data.get('object_type')

    if not all([subject, subject_type, relation, obj, object_type]):
        logger.warning(f"Missing required fields in relationship: {data}")
        return None

    if not all(isinstance(v, str) for v in [subject, subject_type, relation, obj, object_type]):
        logger.warning(f"Relationship fields must be strings: {data}")
        return None

    return Relationship(
        subject=subject,
        subject_type=subject_type,
        relation=relation,
        object=obj,
        object_type=object_type
    )


def parse_attribute(data: Dict[str, Any]) -> Optional[Attribute]:
    """Parse attribute from dict.

    Supports both kebab-case and snake_case field names for compatibility.

    Args:
        data: Attribute dict with entity, entity-type, attribute, value

    Returns:
        Attribute object or None if invalid
    """
    if not isinstance(data, dict):
        logger.warning(f"Attribute data is not a dict: {type(data)}")
        return None

    entity = data.get('entity')
    entity_type = data.get('entity-type') or data.get('entity_type')
    attribute = data.get('attribute')
    value = data.get('value')

    if not all([entity, entity_type, attribute, value is not None]):
        logger.warning(f"Missing required fields in attribute: {data}")
        return None

    if not all(isinstance(v, str) for v in [entity, entity_type, attribute]):
        logger.warning(f"Attribute fields must be strings: {data}")
        return None

    # Value can be string, number, bool - convert to string
    if not isinstance(value, str):
        value = str(value)

    return Attribute(
        entity=entity,
        entity_type=entity_type,
        attribute=attribute,
        value=value
    )
