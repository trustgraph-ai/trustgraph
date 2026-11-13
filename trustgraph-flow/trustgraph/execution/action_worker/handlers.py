"""
Capability handlers for the action worker.  Each handler wraps an
existing TrustGraph service, mapping between the execution framework's
artifact model and the service's native request/response format.
"""

import logging

logger = logging.getLogger(__name__)


class HandlerError(Exception):
    pass


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


def get_input_artifact(input_artifacts, artifact_type):
    for artifact in input_artifacts:
        if artifact.get("artifact-type") == artifact_type:
            return artifact.get("artifact", {})
    return None


class KnowledgeGraphQueryHandler:

    async def execute(self, params, input_artifacts, flow):

        query = get_param(params, "query")

        logger.info(f"Knowledge graph query: {query[:80]}...")

        graph_rag = flow("graph-rag-request")

        triples_collected = []

        async def on_explain(explain_id, explain_graph, explain_triples):
            for t in explain_triples:
                triples_collected.append({
                    "s": term_to_str(t.s),
                    "p": term_to_str(t.p),
                    "o": term_to_str(t.o),
                })

        response = await graph_rag.rag(
            query=query,
            explain_callback=on_explain,
            timeout=300,
        )

        return "SubgraphArtifact", {
            "triples": triples_collected,
            "query": query,
            "summary": response,
        }


class DocumentRetrievalHandler:

    async def execute(self, params, input_artifacts, flow):

        query = get_param(params, "query")

        logger.info(f"Document retrieval: {query[:80]}...")

        prompt_client = flow("prompt-request")

        result = await prompt_client.document_prompt(
            query=query,
            documents=[],
            timeout=300,
        )

        return "TextBlobArtifact", {
            "text": result.text or "",
            "query": query,
        }


class LlmSynthesisHandler:

    async def execute(self, params, input_artifacts, flow):

        system = get_param(params, "system", required=False) or (
            "You are an analyst. Synthesise a clear, structured report "
            "from the provided data and context."
        )

        prompt_parts = []

        data_artifact = get_input_artifact(
            input_artifacts, "TabularArtifact",
        )
        if data_artifact:
            prompt_parts.append(
                "Data:\n" + _format_tabular(data_artifact)
            )

        context_artifact = get_input_artifact(
            input_artifacts, "TextBlobArtifact",
        )
        if context_artifact:
            prompt_parts.append(
                "Context:\n" + context_artifact.get("text", "")
            )

        goal = get_param(params, "goal", required=False)
        if goal:
            prompt_parts.append(f"Goal: {goal}")

        prompt = get_param(params, "prompt", required=False)
        if prompt:
            prompt_parts.append(prompt)

        if not prompt_parts:
            raise HandlerError(
                "LLM synthesis requires at least one input artifact "
                "or a prompt parameter"
            )

        full_prompt = "\n\n".join(prompt_parts)

        logger.info(f"LLM synthesis: {len(full_prompt)} chars input")

        completion = flow("text-completion-request")

        result = await completion.text_completion(
            system=system,
            prompt=full_prompt,
            timeout=600,
        )

        return "ReportArtifact", {
            "format": "markdown",
            "narrative": result.text or "",
        }


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
            s = triple.get("s", "")
            p = triple.get("p", "")
            o = triple.get("o", "")
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


class ErpFinanceQueryHandler:

    async def execute(self, params, input_artifacts, flow):

        query = get_param(params, "query")

        logger.info(f"ERP finance query (mock): {query[:80]}...")

        return "TabularArtifact", {
            "columns": [
                {"name": "cost_centre", "type": "string"},
                {"name": "department", "type": "string"},
                {"name": "budget_q3", "type": "number"},
                {"name": "actual_q3", "type": "number"},
                {"name": "variance", "type": "number"},
            ],
            "rows": [
                {
                    "cost_centre": "CC-1001",
                    "department": "Engineering",
                    "budget_q3": "500000",
                    "actual_q3": "485000",
                    "variance": "-15000",
                },
                {
                    "cost_centre": "CC-1002",
                    "department": "Research",
                    "budget_q3": "300000",
                    "actual_q3": "312000",
                    "variance": "12000",
                },
                {
                    "cost_centre": "CC-1003",
                    "department": "Operations",
                    "budget_q3": "750000",
                    "actual_q3": "743000",
                    "variance": "-7000",
                },
            ],
        }


def _format_tabular(artifact):
    columns = artifact.get("columns", [])
    rows = artifact.get("rows", [])
    col_names = [c.get("name", "?") for c in columns]
    lines = [" | ".join(col_names)]
    lines.append(" | ".join("---" for _ in col_names))
    for row in rows:
        lines.append(" | ".join(str(row.get(c, "")) for c in col_names))
    return "\n".join(lines)


BUILTIN_HANDLERS = {
    "knowledge-graph-query": KnowledgeGraphQueryHandler(),
    "document-retrieval": DocumentRetrievalHandler(),
    "llm-synthesis": LlmSynthesisHandler(),
    "tabular-redact": TabularRedactHandler(),
    "tabular-join": TabularJoinHandler(),
    "erp-finance-query": ErpFinanceQueryHandler(),
}
