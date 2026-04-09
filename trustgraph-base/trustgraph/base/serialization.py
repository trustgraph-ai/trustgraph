"""
JSON serialization helpers for dataclass ↔ dict conversion.

Used by pub/sub backends that use JSON as their wire format.
"""

import types
from dataclasses import asdict, is_dataclass
from typing import Any, get_type_hints


def dataclass_to_dict(obj: Any) -> dict:
    """
    Recursively convert a dataclass to a dictionary, handling None values and bytes.

    None values are excluded from the dictionary (not serialized).
    Bytes values are decoded as UTF-8 strings for JSON serialization.
    Handles nested dataclasses, lists, and dictionaries recursively.
    """
    if obj is None:
        return None

    # Handle bytes - decode to UTF-8 for JSON serialization
    if isinstance(obj, bytes):
        return obj.decode('utf-8')

    # Handle dataclass - convert to dict then recursively process all values
    if is_dataclass(obj):
        result = {}
        for key, value in asdict(obj).items():
            result[key] = dataclass_to_dict(value) if value is not None else None
        return result

    # Handle list - recursively process all items
    if isinstance(obj, list):
        return [dataclass_to_dict(item) for item in obj]

    # Handle dict - recursively process all values
    if isinstance(obj, dict):
        return {k: dataclass_to_dict(v) for k, v in obj.items()}

    # Return primitive types as-is
    return obj


def dict_to_dataclass(data: dict, cls: type) -> Any:
    """
    Convert a dictionary back to a dataclass instance.

    Handles nested dataclasses and missing fields.
    Uses get_type_hints() to resolve forward references (string annotations).
    """
    if data is None:
        return None

    if not is_dataclass(cls):
        return data

    # Get field types from the dataclass, resolving forward references
    # get_type_hints() evaluates string annotations like "Triple | None"
    try:
        field_types = get_type_hints(cls)
    except Exception:
        # Fallback if get_type_hints fails (shouldn't happen normally)
        field_types = {f.name: f.type for f in cls.__dataclass_fields__.values()}
    kwargs = {}

    for key, value in data.items():
        if key in field_types:
            field_type = field_types[key]

            # Handle modern union types (X | Y)
            if isinstance(field_type, types.UnionType):
                # Check if it's Optional (X | None)
                if type(None) in field_type.__args__:
                    # Get the non-None type
                    actual_type = next((t for t in field_type.__args__ if t is not type(None)), None)
                    if actual_type and is_dataclass(actual_type) and isinstance(value, dict):
                        kwargs[key] = dict_to_dataclass(value, actual_type)
                    else:
                        kwargs[key] = value
                else:
                    kwargs[key] = value
            # Check if this is a generic type (list, dict, etc.)
            elif hasattr(field_type, '__origin__'):
                # Handle list[T]
                if field_type.__origin__ == list:
                    item_type = field_type.__args__[0] if field_type.__args__ else None
                    if item_type and is_dataclass(item_type) and isinstance(value, list):
                        kwargs[key] = [
                            dict_to_dataclass(item, item_type) if isinstance(item, dict) else item
                            for item in value
                        ]
                    else:
                        kwargs[key] = value
                # Handle old-style Optional[T] (which is Union[T, None])
                elif hasattr(field_type, '__args__') and type(None) in field_type.__args__:
                    # Get the non-None type from Union
                    actual_type = next((t for t in field_type.__args__ if t is not type(None)), None)
                    if actual_type and is_dataclass(actual_type) and isinstance(value, dict):
                        kwargs[key] = dict_to_dataclass(value, actual_type)
                    else:
                        kwargs[key] = value
                else:
                    kwargs[key] = value
            # Handle direct dataclass fields
            elif is_dataclass(field_type) and isinstance(value, dict):
                kwargs[key] = dict_to_dataclass(value, field_type)
            # Handle bytes fields (UTF-8 encoded strings from JSON)
            elif field_type == bytes and isinstance(value, str):
                kwargs[key] = value.encode('utf-8')
            else:
                kwargs[key] = value

    return cls(**kwargs)
