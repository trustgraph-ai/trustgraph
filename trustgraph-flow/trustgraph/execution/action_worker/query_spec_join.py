
import copy
import logging

from . common import ActionHandler, HandlerError

logger = logging.getLogger(__name__)


def collect_schemas(spec):
    if spec.get("type") == "select":
        schema = spec.get("schema")
        if schema:
            return [schema]
        return []
    elif spec.get("type") == "join":
        return collect_schemas(spec["left"]) + collect_schemas(spec["right"])
    return []


def find_join_keys(left_schemas, right_schemas):
    for left_schema in left_schemas:
        left_table = left_schema.get("name", "")
        for right_schema in right_schemas:
            right_table = right_schema.get("name", "")

            for field in left_schema.get("fields", []):
                fk = field.get("foreign_key", {})
                if right_table in fk:
                    return (
                        left_table, field["name"],
                        right_table, fk[right_table],
                    )

            for field in right_schema.get("fields", []):
                fk = field.get("foreign_key", {})
                if left_table in fk:
                    return (
                        left_table, fk[left_table],
                        right_table, field["name"],
                    )

    return None, None, None, None


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


class QuerySpecJoinHandler(ActionHandler):

    inputs = {
        "left": {"artifact-type": "QuerySpecArtifact"},
        "right": {"artifact-type": "QuerySpecArtifact"},
    }
    outputs = {
        "query-spec": {"artifact-type": "QuerySpecArtifact"},
    }

    async def execute(self, inputs, flow):

        left = inputs["left"]
        right = inputs["right"]

        left_schemas = collect_schemas(left)
        right_schemas = collect_schemas(right)

        if not left_schemas or not right_schemas:
            raise HandlerError(
                "Both query specs must have embedded schemas "
                "for join key discovery"
            )

        left_table, left_col, right_table, right_col = find_join_keys(
            left_schemas, right_schemas,
        )

        if left_col is None:
            left_names = [s.get("name") for s in left_schemas]
            right_names = [s.get("name") for s in right_schemas]
            raise HandlerError(
                f"No foreign key relationship found between "
                f"{left_names} and {right_names}"
            )

        left = ensure_column(left, left_table, left_col)
        right = ensure_column(right, right_table, right_col)

        logger.info(
            f"Query spec join: "
            f"{left_table}.{left_col} = {right_table}.{right_col}"
        )

        return {
            "query-spec": {
                "version": "1",
                "type": "join",
                "left": left,
                "right": right,
                "on": [
                    {
                        "left_column": left_col,
                        "right_column": right_col,
                    }
                ],
            }
        }
