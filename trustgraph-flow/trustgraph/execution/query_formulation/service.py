"""
Query formulation service.  Takes a natural language question and a
schema name, calls the prompt service to produce a QuerySpecArtifact.
"""

import json
import logging

from ... schema import QueryFormulationResponse, Error
from ... base import QueryFormulationService, PromptClientSpec

logger = logging.getLogger(__name__)

default_ident = "query-formulation"

FILTER_OPS = {"eq", "ne", "lt", "lte", "gt", "gte", "in", "like"}
ORDER_DIRECTIONS = {"asc", "desc"}


def validate_query_spec(spec, schema):
    """Validate a query spec against a schema definition."""

    if spec.get("version") != "1":
        raise ValueError(
            f"Unsupported query spec version: {spec.get('version')}"
        )

    spec_type = spec.get("type")

    if spec_type == "select":
        validate_select(spec, schema)
    elif spec_type == "join":
        validate_join(spec, schema)
    else:
        raise ValueError(f"Unknown query spec type: {spec_type}")


def validate_select(spec, schema):

    schema_fields = {f["name"] for f in schema.get("fields", [])}
    table_name = schema.get("name", "")

    columns = spec.get("columns", [])
    if not columns:
        raise ValueError("Query spec must have at least one column")

    for col in columns:
        if col not in schema_fields:
            raise ValueError(
                f"Column '{col}' not found in schema "
                f"'{table_name}'. "
                f"Available: {sorted(schema_fields)}"
            )

    for f in spec.get("filters", []):
        col = f.get("column", "")
        if col not in schema_fields:
            raise ValueError(
                f"Filter column '{col}' not found in schema "
                f"'{table_name}'"
            )
        op = f.get("op", "")
        if op not in FILTER_OPS:
            raise ValueError(
                f"Unknown filter operator '{op}'. "
                f"Must be one of: {sorted(FILTER_OPS)}"
            )

    for o in spec.get("order_by", []):
        col = o.get("column", "")
        if col not in schema_fields:
            raise ValueError(
                f"Order column '{col}' not found in schema "
                f"'{table_name}'"
            )
        direction = o.get("direction", "")
        if direction not in ORDER_DIRECTIONS:
            raise ValueError(
                f"Order direction must be 'asc' or 'desc', "
                f"got '{direction}'"
            )


def validate_join(spec, schema):
    # Join validation is minimal for now — just check structure
    if "left" not in spec or "right" not in spec:
        raise ValueError("Join spec must have 'left' and 'right'")
    if not spec.get("on"):
        raise ValueError("Join spec must have at least one 'on' key")


class Processor(QueryFormulationService):

    def __init__(self, **params):

        super(Processor, self).__init__(**params)

        self.register_specification(
            PromptClientSpec(
                request_name="prompt-request",
                response_name="prompt-response",
            )
        )

    async def formulate(self, workspace, request, flow):

        schema = self.get_schema(workspace, request.schema_name)

        logger.info(
            f"Formulating query for schema '{request.schema_name}': "
            f"{request.question[:80]}..."
        )

        result = await flow("prompt-request").query_formulation(
            question=request.question,
            schema=json.dumps(schema),
        )

        if result.response_type == "json" and result.object:
            query_spec = result.object
        elif result.response_type == "text" and result.text:
            query_spec = json.loads(result.text)
        else:
            raise RuntimeError(
                "Prompt service returned no usable response"
            )

        validate_query_spec(query_spec, schema)

        logger.info(
            f"Query formulated: type={query_spec.get('type')}, "
            f"table={query_spec.get('table', 'n/a')}, "
            f"columns={len(query_spec.get('columns', []))}, "
            f"filters={len(query_spec.get('filters', []))}"
        )

        return QueryFormulationResponse(
            run_id=request.run_id,
            step_id=request.step_id,
            query_spec=json.dumps(query_spec),
        )

    @staticmethod
    def add_args(parser):
        QueryFormulationService.add_args(parser)


def run():
    Processor.launch(default_ident, __doc__)
