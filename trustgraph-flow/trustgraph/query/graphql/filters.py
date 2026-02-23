"""
Filter parsing utilities for GraphQL row queries.

Provides functions to parse GraphQL filter objects into a normalized
format that can be used by different query backends.
"""

import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)


def parse_filter_key(filter_key: str) -> Tuple[str, str]:
    """
    Parse GraphQL filter key into field name and operator.

    Supports common GraphQL filter patterns:
    - field_name -> (field_name, "eq")
    - field_name_gt -> (field_name, "gt")
    - field_name_gte -> (field_name, "gte")
    - field_name_lt -> (field_name, "lt")
    - field_name_lte -> (field_name, "lte")
    - field_name_in -> (field_name, "in")

    Args:
        filter_key: The filter key string from GraphQL

    Returns:
        Tuple of (field_name, operator)
    """
    if not filter_key:
        return ("", "eq")

    operators = ["_gte", "_lte", "_gt", "_lt", "_in", "_eq"]

    for op_suffix in operators:
        if filter_key.endswith(op_suffix):
            field_name = filter_key[:-len(op_suffix)]
            operator = op_suffix[1:]  # Remove the leading underscore
            return (field_name, operator)

    # Default to equality if no operator suffix found
    return (filter_key, "eq")


def parse_where_clause(where_obj) -> Dict[str, Any]:
    """
    Parse the idiomatic nested GraphQL filter structure into a flat dict.

    Converts Strawberry filter objects (StringFilter, IntFilter, etc.)
    into a dictionary mapping field names with operators to values.

    Example:
        Input: where_obj with email.eq = "foo@bar.com"
        Output: {"email": "foo@bar.com"}

        Input: where_obj with age.gt = 21
        Output: {"age_gt": 21}

    Args:
        where_obj: The GraphQL where clause object

    Returns:
        Dictionary mapping field_operator keys to values
    """
    if not where_obj:
        return {}

    conditions = {}

    logger.debug(f"Parsing where clause: {where_obj}")

    for field_name, filter_obj in where_obj.__dict__.items():
        if filter_obj is None:
            continue

        logger.debug(f"Processing field {field_name} with filter_obj: {filter_obj}")

        if hasattr(filter_obj, '__dict__'):
            # This is a filter object (StringFilter, IntFilter, etc.)
            for operator, value in filter_obj.__dict__.items():
                if value is not None:
                    logger.debug(f"Found operator {operator} with value {value}")
                    # Map GraphQL operators to our internal format
                    if operator == "eq":
                        conditions[field_name] = value
                    elif operator in ["gt", "gte", "lt", "lte"]:
                        conditions[f"{field_name}_{operator}"] = value
                    elif operator == "in_":
                        conditions[f"{field_name}_in"] = value
                    elif operator == "contains":
                        conditions[f"{field_name}_contains"] = value
                    elif operator == "startsWith":
                        conditions[f"{field_name}_startsWith"] = value
                    elif operator == "endsWith":
                        conditions[f"{field_name}_endsWith"] = value
                    elif operator == "not_":
                        conditions[f"{field_name}_not"] = value
                    elif operator == "not_in":
                        conditions[f"{field_name}_not_in"] = value

    logger.debug(f"Final parsed conditions: {conditions}")
    return conditions
