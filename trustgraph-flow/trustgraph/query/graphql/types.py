"""
GraphQL filter and sort types for row queries.

These types are used to build dynamic GraphQL schemas for querying
structured row data.
"""

from typing import Optional, List
from enum import Enum

import strawberry


@strawberry.input
class IntFilter:
    """Filter type for integer fields."""
    eq: Optional[int] = None
    gt: Optional[int] = None
    gte: Optional[int] = None
    lt: Optional[int] = None
    lte: Optional[int] = None
    in_: Optional[List[int]] = strawberry.field(name="in", default=None)
    not_: Optional[int] = strawberry.field(name="not", default=None)
    not_in: Optional[List[int]] = None


@strawberry.input
class StringFilter:
    """Filter type for string fields."""
    eq: Optional[str] = None
    contains: Optional[str] = None
    startsWith: Optional[str] = None
    endsWith: Optional[str] = None
    in_: Optional[List[str]] = strawberry.field(name="in", default=None)
    not_: Optional[str] = strawberry.field(name="not", default=None)
    not_in: Optional[List[str]] = None


@strawberry.input
class FloatFilter:
    """Filter type for float fields."""
    eq: Optional[float] = None
    gt: Optional[float] = None
    gte: Optional[float] = None
    lt: Optional[float] = None
    lte: Optional[float] = None
    in_: Optional[List[float]] = strawberry.field(name="in", default=None)
    not_: Optional[float] = strawberry.field(name="not", default=None)
    not_in: Optional[List[float]] = None


@strawberry.enum
class SortDirection(Enum):
    """Sort direction for query results."""
    ASC = "asc"
    DESC = "desc"
