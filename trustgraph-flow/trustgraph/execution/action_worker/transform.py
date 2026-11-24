
import logging

from . common import ActionHandler, HandlerError, term_dict_to_str

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


class RerankHandler(ActionHandler):

    inputs = {
        "query": {"artifact-type": "TextBlobArtifact"},
        "data": {
            "artifact-type": [
                "EntityListArtifact",
                "SubgraphArtifact",
                "KeywordsArtifact",
            ],
        },
        "top-k": {"artifact-type": "TextBlobArtifact", "optional": True},
    }
    outputs = {
        "data": {
            "artifact-type": [
                "EntityListArtifact",
                "SubgraphArtifact",
                "KeywordsArtifact",
            ],
        },
    }

    async def execute(self, inputs, flow):

        query = inputs["query"]["text"]
        data = inputs["data"]
        top_k = int(inputs["top-k"]["text"]) if "top-k" in inputs else 10

        serialiser = None
        artifact_type = None
        for atype, ser in _RERANK_SERIALISERS.items():
            if ser["items_key"] in data:
                artifact_type = atype
                serialiser = ser
                break

        if serialiser is None:
            raise HandlerError(
                "rerank input data does not match any known "
                "artifact structure"
            )

        items_key = serialiser["items_key"]
        to_text = serialiser["to_text"]
        items = data.get(items_key, [])

        if not items:
            return {
                "data": {
                    "artifact-type": artifact_type,
                    "artifact": data,
                }
            }

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
        reranked_items = reranked_items[:top_k]

        logger.info(
            f"Rerank: {len(items)} → {len(reranked_items)} {items_key}"
        )

        result = dict(data)
        result[items_key] = reranked_items
        return {
            "data": {
                "artifact-type": artifact_type,
                "artifact": result,
            }
        }


class TabularRedactHandler(ActionHandler):

    inputs = {
        "data": {"artifact-type": "TabularArtifact"},
        "columns": {"artifact-type": "TextBlobArtifact"},
        "method": {"artifact-type": "TextBlobArtifact", "optional": True},
    }
    outputs = {
        "data": {"artifact-type": "TabularArtifact"},
    }

    async def execute(self, inputs, flow):

        data = inputs["data"]

        redact_columns = [
            c.strip()
            for c in inputs["columns"]["text"].split(",")
            if c.strip()
        ]

        method = (
            inputs["method"]["text"] if "method" in inputs else "strip"
        )

        columns = data.get("columns", [])
        rows = data.get("rows", [])

        if method == "strip":
            columns = [
                c for c in columns
                if c.get("name") not in redact_columns
            ]
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

        return {
            "data": {
                "columns": columns,
                "rows": rows,
            }
        }


class TabularJoinHandler(ActionHandler):

    inputs = {
        "tabular": {"artifact-type": "TabularArtifact"},
        "graph": {"artifact-type": "SubgraphArtifact"},
        "join-key": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
    }
    outputs = {
        "data": {"artifact-type": "TabularArtifact"},
    }

    async def execute(self, inputs, flow):

        tabular = inputs["tabular"]
        graph = inputs["graph"]
        join_key = (
            inputs["join-key"]["text"] if "join-key" in inputs else "id"
        )

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
                    col_name = (
                        prop.rsplit("/", 1)[-1].rsplit("#", 1)[-1]
                    )
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

        return {
            "data": {
                "columns": columns,
                "rows": enriched_rows,
            }
        }
