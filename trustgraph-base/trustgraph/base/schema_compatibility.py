
import logging

logger = logging.getLogger(__name__)


def is_strict_mode_compatible(schema):
    """
    Check whether a JSON schema is compatible with LLM structured-output
    strict mode.  Returns True if the schema can be passed directly to
    providers like OpenAI, vLLM, etc.
    """

    if schema is None:
        return False

    try:
        _check_node(schema)
        return True
    except _IncompatibleSchema as e:
        logger.debug("Schema not strict-mode compatible: %s", e)
        return False


class _IncompatibleSchema(Exception):
    pass


def _check_node(node):

    if not isinstance(node, dict):
        return

    node_type = node.get("type")

    if node_type == "object" or (
        node_type is None and "properties" in node
    ):
        _check_object(node)

    if node_type == "array":
        items = node.get("items")
        if items:
            _check_node(items)

    for keyword in ("oneOf", "anyOf", "allOf"):
        for child in node.get(keyword, []):
            _check_node(child)

    _check_unsupported_constraints(node)


def _check_object(node):

    props = node.get("properties")
    if props is None:
        raise _IncompatibleSchema(
            "object without properties (open-ended)"
        )

    if node.get("additionalProperties") is not False:
        raise _IncompatibleSchema(
            "object missing additionalProperties: false"
        )

    required = set(node.get("required", []))
    for key in props:
        if key not in required:
            raise _IncompatibleSchema(
                f"property '{key}' not in required"
            )

    for value in props.values():
        _check_node(value)


UNSUPPORTED_KEYWORDS = {
    "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
    "minLength", "maxLength", "pattern",
    "minItems", "maxItems",
    "minProperties", "maxProperties",
}


def _check_unsupported_constraints(node):
    found = UNSUPPORTED_KEYWORDS & node.keys()
    if found:
        raise _IncompatibleSchema(
            f"unsupported constraints: {', '.join(sorted(found))}"
        )
