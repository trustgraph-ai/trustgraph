
import json
import logging

logger = logging.getLogger(__name__)


class HandlerError(Exception):
    pass


class ActionHandler:

    inputs = {}
    outputs = {}

    async def execute(self, inputs, flow):
        raise NotImplementedError


def get_param(params, key, required=True):
    value = params.get(key, "")
    if required and not value:
        raise HandlerError(f"Missing required parameter: {key}")
    return value


def term_to_str(term):
    if hasattr(term, 'type'):
        if term.type == 'i':
            return term.iri
        elif term.type == 'l':
            return term.value
        elif term.type == 'b':
            return term.id
    return str(term)


def get_param_list(params, key):
    value = params.get(key, "")
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def get_param_int(params, key, default):
    value = params.get(key, "")
    if not value:
        return default
    return int(value)


def parse_param_json(params, key, expected_type=None):
    value = params.get(key, "")
    if not value:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as e:
        raise HandlerError(
            f"Parameter '{key}' is not valid JSON: {e}"
        )
    if expected_type and not isinstance(parsed, expected_type):
        type_name = expected_type.__name__
        raise HandlerError(
            f"Parameter '{key}' must be a JSON {type_name}, "
            f"got {type(parsed).__name__}"
        )
    return parsed


def schema_term_to_dict(term):
    if term is None:
        return None
    if term.type == 'i':
        return {"type": "iri", "iri": term.iri}
    elif term.type == 'l':
        d = {"type": "literal", "value": term.value}
        if term.language:
            d["language"] = term.language
        if term.datatype:
            d["datatype"] = term.datatype
        return d
    elif term.type == 'b':
        return {"type": "blank", "id": term.id}
    elif term.type == 't' and term.triple:
        return {
            "type": "triple",
            "triple": {
                "s": schema_term_to_dict(term.triple.s),
                "p": schema_term_to_dict(term.triple.p),
                "o": schema_term_to_dict(term.triple.o),
            }
        }
    return {"type": "unknown", "value": str(term)}


def term_dict_to_str(d):
    if not d or not isinstance(d, dict):
        return str(d) if d else ""
    t = d.get("type", "")
    if t == "iri":
        return d.get("iri", "")
    elif t == "literal":
        return d.get("value", "")
    elif t == "blank":
        return d.get("id", "")
    elif t == "triple":
        tri = d.get("triple", {})
        return " ".join([
            term_dict_to_str(tri.get("s")),
            term_dict_to_str(tri.get("p")),
            term_dict_to_str(tri.get("o")),
        ])
    return ""



def format_tabular(artifact):
    columns = artifact.get("columns", [])
    rows = artifact.get("rows", [])
    col_names = [c.get("name", "?") for c in columns]
    lines = [" | ".join(col_names)]
    lines.append(" | ".join("---" for _ in col_names))
    for row in rows:
        lines.append(" | ".join(str(row.get(c, "")) for c in col_names))
    return "\n".join(lines)
