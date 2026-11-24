
import json
import logging

from . common import ActionHandler

logger = logging.getLogger(__name__)


class QueryFormulationHandler(ActionHandler):

    inputs = {
        "question": {"artifact-type": "TextBlobArtifact"},
        "schema-name": {"artifact-type": "TextBlobArtifact"},
    }
    outputs = {
        "query-spec": {"artifact-type": "QuerySpecArtifact"},
    }

    async def execute(self, inputs, flow):

        question = inputs["question"]["text"]
        schema_name = inputs["schema-name"]["text"]

        logger.info(
            f"Query formulation: schema={schema_name}, "
            f"question={question[:80]}..."
        )

        qf = flow("query-formulation-request")

        query_spec_str = await qf.formulate(
            question=question,
            schema_name=schema_name,
            timeout=300,
        )

        query_spec = json.loads(query_spec_str)

        logger.info(
            f"Query formulation: table={query_spec.get('table', '?')}, "
            f"type={query_spec.get('type', '?')}"
        )

        return {"query-spec": query_spec}
