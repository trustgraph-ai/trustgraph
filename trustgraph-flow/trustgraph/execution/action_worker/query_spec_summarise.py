
import json
import logging

from . common import ActionHandler

logger = logging.getLogger(__name__)


class QuerySpecSummariseHandler(ActionHandler):

    inputs = {
        "query-spec": {"artifact-type": "QuerySpecArtifact"},
        "goal": {"artifact-type": "TextBlobArtifact"},
    }
    outputs = {
        "query-spec": {"artifact-type": "QuerySpecArtifact"},
    }

    async def execute(self, inputs, flow):

        spec = inputs["query-spec"]
        goal = inputs["goal"]["text"]

        logger.info(
            f"Query spec summarise: goal={goal[:80]}..."
        )

        qf = flow("query-formulation-request")

        result = await qf.summarise(
            query_spec=json.dumps(spec),
            goal=goal,
            timeout=300,
        )

        updated_spec = json.loads(result)

        logger.info(
            f"Query spec summarised: "
            f"group_by={updated_spec.get('group_by')}, "
            f"aggregations={len(updated_spec.get('aggregations', []))}"
        )

        return {"query-spec": updated_spec}
