"""
Query formulation service.  Takes a natural language question and a
schema name, calls the prompt service to produce a QuerySpecArtifact.
"""

import copy
import json
import logging

from ... schema import QueryFormulationResponse, Error
from ... base import QueryFormulationService, PromptClientSpec

logger = logging.getLogger(__name__)

default_ident = "query-formulation"

FILTER_OPS = {"eq", "ne", "lt", "lte", "gt", "gte", "in", "like", "is_null", "is_not_null"}
NULLARY_OPS = {"is_null", "is_not_null"}
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
        if op not in NULLARY_OPS and "value" not in f:
            raise ValueError(
                f"Filter on '{col}' with op '{op}' requires a value"
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
    if "left" not in spec or "right" not in spec:
        raise ValueError("Join spec must have 'left' and 'right'")

    on = spec.get("on")
    if not on:
        raise ValueError("Join spec must have at least one 'on' clause")

    for clause in on:
        if "left_column" not in clause or "right_column" not in clause:
            raise ValueError(
                "Each 'on' clause must have 'left_column' and "
                "'right_column'"
            )

    for sub_key in ("left", "right"):
        sub = spec[sub_key]
        sub_type = sub.get("type")
        if sub_type not in ("select", "join"):
            raise ValueError(
                f"Join {sub_key}: unknown query type '{sub_type}'"
            )


def collect_schemas(spec):
    if spec.get("type") == "select":
        schema = spec.get("schema")
        return [schema] if schema else []
    elif spec.get("type") == "join":
        return collect_schemas(spec["left"]) + collect_schemas(spec["right"])
    return []


def find_column_table(schemas, column_name):
    for schema in schemas:
        field_names = {f["name"] for f in schema.get("fields", [])}
        if column_name in field_names:
            return schema.get("name")
    return None


def ensure_column(spec, table_name, column_name):
    if spec.get("type") == "select":
        schema = spec.get("schema", {})
        if schema.get("name") == table_name:
            if column_name not in spec.get("columns", []):
                spec = copy.copy(spec)
                spec["columns"] = list(spec["columns"]) + [column_name]
        return spec
    elif spec.get("type") == "join":
        new_left = ensure_column(spec["left"], table_name, column_name)
        new_right = ensure_column(spec["right"], table_name, column_name)
        if new_left is not spec["left"] or new_right is not spec["right"]:
            spec = copy.copy(spec)
            spec["left"] = new_left
            spec["right"] = new_right
        return spec
    return spec


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
            schema=schema,
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

        query_spec["schema"] = schema

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

    async def summarise(self, workspace, request, flow):

        spec = json.loads(request.query_spec)

        schemas = collect_schemas(spec)
        if not schemas:
            raise RuntimeError(
                "QuerySpec has no embedded schema for summarisation"
            )

        logger.info(
            f"Summarising query spec: {request.question[:80]}..."
        )

        result = await flow("prompt-request").query_summarisation(
            goal=request.question,
            schemas=schemas,
        )

        if result.response_type == "json" and result.object:
            aggregation = result.object
        elif result.response_type == "text" and result.text:
            aggregation = json.loads(result.text)
        else:
            raise RuntimeError(
                "Prompt service returned no usable response"
            )

        group_by = aggregation.get("group_by", [])
        aggregations = aggregation.get("aggregations", [])

        if not group_by:
            raise ValueError("Summarisation must have group_by columns")
        if not aggregations:
            raise ValueError("Summarisation must have aggregations")

        for col in group_by:
            table = find_column_table(schemas, col)
            if table:
                spec = ensure_column(spec, table, col)
        for agg in aggregations:
            table = find_column_table(schemas, agg["column"])
            if table:
                spec = ensure_column(spec, table, agg["column"])

        spec["group_by"] = group_by
        spec["aggregations"] = aggregations
        spec["columns"] = group_by + [
            a["alias"] for a in aggregations
        ]

        logger.info(
            f"Summarisation applied: group_by={group_by}, "
            f"aggregations="
            f"{[a['function'] + ':' + a['column'] for a in aggregations]}"
        )

        return QueryFormulationResponse(
            run_id=request.run_id,
            step_id=request.step_id,
            query_spec=json.dumps(spec),
        )

    @staticmethod
    def add_args(parser):
        QueryFormulationService.add_args(parser)


def run():
    Processor.launch(default_ident, __doc__)
