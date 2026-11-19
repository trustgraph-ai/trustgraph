
import logging

from . common import get_param

logger = logging.getLogger(__name__)


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
