"""
ERP Finance Remote Action Service - mock ERP finance data source.

Demonstrates a remote action service returning structured tabular
artifacts.  In production this would connect to a real ERP system;
here it returns sample budget-vs-actual data.

Params:
    query: The finance query string.

Returns:
    TabularArtifact with budget/actual/variance rows.

Example remote-action config:
{
    "erp-finance-query": "{
        \"request-topic\": \"request:tg:erp-finance\",
        \"response-topic\": \"response:tg:erp-finance\"
    }"
}
"""

import logging

from ... base import RemoteActionService

logger = logging.getLogger(__name__)

default_ident = "erp-finance-action-service"
default_topic = "erp-finance"

MOCK_DATA = {
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


class Processor(RemoteActionService):

    def __init__(self, **params):
        super(Processor, self).__init__(**params)
        logger.info("ERP finance action service initialized")

    async def execute(self, inputs, user_context):

        query = inputs.get("query", {}).get("text", "")

        logger.info(
            f"ERP finance query (mock): {query[:80]}... "
            f"user={user_context.user_id if user_context else 'anonymous'}"
        )

        return {"results": ("TabularArtifact", MOCK_DATA)}

    @staticmethod
    def add_args(parser):
        RemoteActionService.add_args(parser)
        for action in parser._actions:
            if '--topic' in action.option_strings:
                action.default = default_topic
                break


def run():
    Processor.launch(default_ident, __doc__)
