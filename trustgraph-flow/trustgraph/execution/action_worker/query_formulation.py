
import json
import logging

from . common import HandlerError, get_param

logger = logging.getLogger(__name__)


class QueryFormulationHandler:

    async def execute(self, params, input_artifacts, flow):

        question = get_param(params, "question")
        schema_name = get_param(params, "schema-name")

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

        return "QuerySpecArtifact", query_spec
