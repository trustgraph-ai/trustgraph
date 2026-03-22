
"""
Section grouping strategies for the universal document decoder.

Each strategy takes a list of unstructured elements and returns a list
of element groups. Each group becomes one TextDocument output.
"""

import logging

logger = logging.getLogger(__name__)


def group_whole_document(elements, **kwargs):
    """
    Emit the entire document as a single section.

    The downstream chunker handles all splitting.
    """
    if not elements:
        return []
    return [elements]


def group_by_heading(elements, **kwargs):
    """
    Split at heading elements (Title category).

    Each section is a heading plus all content until the next heading.
    Falls back to whole-document if no headings are found.
    """
    if not elements:
        return []

    # Check if any headings exist
    has_headings = any(
        getattr(el, 'category', '') == 'Title' for el in elements
    )

    if not has_headings:
        logger.debug("No headings found, falling back to whole-document")
        return group_whole_document(elements)

    groups = []
    current_group = []

    for el in elements:
        if getattr(el, 'category', '') == 'Title' and current_group:
            groups.append(current_group)
            current_group = []
        current_group.append(el)

    if current_group:
        groups.append(current_group)

    return groups


def group_by_element_type(elements, **kwargs):
    """
    Split on transitions between narrative text and tables.

    Consecutive elements of the same broad category stay grouped.
    """
    if not elements:
        return []

    def is_table(el):
        return getattr(el, 'category', '') == 'Table'

    groups = []
    current_group = []
    current_is_table = None

    for el in elements:
        el_is_table = is_table(el)
        if current_is_table is not None and el_is_table != current_is_table:
            groups.append(current_group)
            current_group = []
        current_group.append(el)
        current_is_table = el_is_table

    if current_group:
        groups.append(current_group)

    return groups


def group_by_count(elements, element_count=20, **kwargs):
    """
    Group a fixed number of elements per section.

    Args:
        elements: List of unstructured elements
        element_count: Number of elements per group (default: 20)
    """
    if not elements:
        return []

    groups = []
    for i in range(0, len(elements), element_count):
        groups.append(elements[i:i + element_count])

    return groups


def group_by_size(elements, max_size=4000, **kwargs):
    """
    Accumulate elements until a character limit is reached.

    Respects element boundaries — never splits mid-element. If a
    single element exceeds the limit, it becomes its own section.

    Args:
        elements: List of unstructured elements
        max_size: Max characters per section (default: 4000)
    """
    if not elements:
        return []

    groups = []
    current_group = []
    current_size = 0

    for el in elements:
        el_text = getattr(el, 'text', '') or ''
        el_size = len(el_text)

        if current_group and current_size + el_size > max_size:
            groups.append(current_group)
            current_group = []
            current_size = 0

        current_group.append(el)
        current_size += el_size

    if current_group:
        groups.append(current_group)

    return groups


# Strategy registry
STRATEGIES = {
    'whole-document': group_whole_document,
    'heading': group_by_heading,
    'element-type': group_by_element_type,
    'count': group_by_count,
    'size': group_by_size,
}


def get_strategy(name):
    """
    Get a section grouping strategy by name.

    Args:
        name: Strategy name (whole-document, heading, element-type, count, size)

    Returns:
        Strategy function

    Raises:
        ValueError: If strategy name is not recognized
    """
    if name not in STRATEGIES:
        raise ValueError(
            f"Unknown section strategy: {name}. "
            f"Available: {', '.join(STRATEGIES.keys())}"
        )
    return STRATEGIES[name]
