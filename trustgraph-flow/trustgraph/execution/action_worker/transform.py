
import logging

from . common import (
    HandlerError, get_param, get_param_int, get_input_artifact,
    term_dict_to_str,
)

logger = logging.getLogger(__name__)


_RERANK_SERIALISERS = {
    "EntityListArtifact": {
        "items_key": "entities",
        "to_text": lambda item: " ".join(filter(None, [
            item.get("entity", ""),
            " ".join(item.get("rdf_type", [])),
            " ".join(
                f"{k}={v}" for k, v in item.get("attributes", {}).items()
            ),
        ])),
    },
    "SubgraphArtifact": {
        "items_key": "triples",
        "to_text": lambda item: " ".join([
            term_dict_to_str(item.get("s")),
            term_dict_to_str(item.get("p")),
            term_dict_to_str(item.get("o")),
        ]),
    },
    "KeywordsArtifact": {
        "items_key": "keywords",
        "to_text": lambda item: item,
    },
}


class RerankHandler:

    async def execute(self, params, input_artifacts, flow):

        query = get_param(params, "query")
        top_k = get_param_int(params, "top-k", 10)

        artifact_type = None
        artifact = None
        serialiser = None

        for atype, ser in _RERANK_SERIALISERS.items():
            art = get_input_artifact(input_artifacts, atype)
            if art is not None:
                artifact_type = atype
                artifact = art
                serialiser = ser
                break

        if artifact is None:
            raise HandlerError(
                "rerank requires an input artifact of type: "
                + ", ".join(_RERANK_SERIALISERS.keys())
            )

        items_key = serialiser["items_key"]
        to_text = serialiser["to_text"]
        items = artifact.get(items_key, [])

        if not items:
            return artifact_type, artifact

        documents = [
            {"id": str(i), "text": to_text(item)}
            for i, item in enumerate(items)
        ]

        logger.info(
            f"Rerank: {len(documents)} {items_key} against "
            f"query {query[:80]}..."
        )

        reranker = flow("reranker-request")
        results = await reranker.rerank(
            queries=[{"id": "q", "text": query}],
            documents=documents,
            limit=top_k,
            timeout=300,
        )

        ranked_indices = [int(r.document_id) for r in results]
        reranked_items = [
            items[i] for i in ranked_indices if i < len(items)
        ]
        # FIXME: limit not being applied by reranker service, enforce here
        reranked_items = reranked_items[:top_k]

        logger.info(
            f"Rerank: {len(items)} → {len(reranked_items)} {items_key}"
        )

        result = dict(artifact)
        result[items_key] = reranked_items
        return artifact_type, result


class TabularRedactHandler:

    async def execute(self, params, input_artifacts, flow):

        data = get_input_artifact(input_artifacts, "TabularArtifact")
        if not data:
            raise HandlerError(
                "tabular-redact requires a TabularArtifact input"
            )

        redact_columns = [
            c.strip()
            for c in get_param(params, "columns", required=False).split(",")
            if c.strip()
        ]

        method = get_param(params, "method", required=False) or "strip"

        columns = data.get("columns", [])
        rows = data.get("rows", [])

        if method == "strip":
            columns = [c for c in columns if c.get("name") not in redact_columns]
            rows = [
                {k: v for k, v in row.items() if k not in redact_columns}
                for row in rows
            ]
        elif method == "mask":
            rows = [
                {
                    k: ("***" if k in redact_columns else v)
                    for k, v in row.items()
                }
                for row in rows
            ]

        logger.info(
            f"Tabular redact: {len(redact_columns)} columns, "
            f"method={method}"
        )

        return "TabularArtifact", {
            "columns": columns,
            "rows": rows,
        }


class TabularJoinHandler:

    async def execute(self, params, input_artifacts, flow):

        tabular = get_input_artifact(
            input_artifacts, "TabularArtifact",
        )
        if not tabular:
            raise HandlerError(
                "tabular-join requires a TabularArtifact input"
            )

        graph = get_input_artifact(
            input_artifacts, "SubgraphArtifact",
        )
        if not graph:
            raise HandlerError(
                "tabular-join requires a SubgraphArtifact input"
            )

        join_key = get_param(params, "join-key", required=False) or "id"

        columns = list(tabular.get("columns", []))
        rows = list(tabular.get("rows", []))

        graph_data = {}
        for triple in graph.get("triples", []):
            s = term_dict_to_str(triple.get("s"))
            p = term_dict_to_str(triple.get("p"))
            o = term_dict_to_str(triple.get("o"))
            if s not in graph_data:
                graph_data[s] = {}
            graph_data[s][p] = o

        new_columns = set()
        enriched_rows = []
        for row in rows:
            new_row = dict(row)
            key_value = row.get(join_key, "")
            if key_value in graph_data:
                for prop, val in graph_data[key_value].items():
                    col_name = prop.rsplit("/", 1)[-1].rsplit("#", 1)[-1]
                    new_row[col_name] = val
                    new_columns.add(col_name)
            enriched_rows.append(new_row)

        for col_name in sorted(new_columns):
            if not any(c.get("name") == col_name for c in columns):
                columns.append({"name": col_name, "type": "string"})

        logger.info(
            f"Tabular join: {len(enriched_rows)} rows, "
            f"{len(new_columns)} new columns from graph"
        )

        return "TabularArtifact", {
            "columns": columns,
            "rows": enriched_rows,
        }
