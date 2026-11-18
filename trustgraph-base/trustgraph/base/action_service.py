"""
Action worker service.  Dispatches step execution to capability
handlers.  Single service handles all capabilities via a pluggable
handler registry.
"""

from __future__ import annotations

from argparse import ArgumentParser

import time
import logging
from prometheus_client import Histogram, Counter

from .. schema import ActionRequest, ActionResponse, Error

from . flow_processor import FlowProcessor
from . consumer_spec import ConsumerSpec
from . producer_spec import ProducerSpec

logger = logging.getLogger(__name__)

default_ident = "action"
default_concurrency = 10


class ActionService(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")
        concurrency = params.get("concurrency", default_concurrency)

        super(ActionService, self).__init__(**params | { "id": id })

        self.register_specification(
            ConsumerSpec(
                name = "request",
                schema = ActionRequest,
                handler = self.on_message,
                concurrency = concurrency,
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "response",
                schema = ActionResponse,
            )
        )

        if not hasattr(__class__, "action_duration_metric"):
            from . metrics import BUCKETS_LLM
            __class__.action_duration_metric = Histogram(
                'tg_action_duration_seconds',
                'Action worker execution latency (seconds)',
                ["processor", "capability"],
                buckets=BUCKETS_LLM,
            )
            __class__.action_count_metric = Counter(
                'tg_action_total',
                'Action worker executions by capability',
                ["processor", "capability"],
            )

    async def on_message(self, msg, consumer, flow):

        try:

            request = msg.value()

            id = msg.properties()["id"]

            logger.debug(
                f"Handling action request {id} "
                f"({request.capability})..."
            )

            workspace = flow.workspace

            t0 = time.monotonic()
            response = await self.execute(workspace, request, flow)
            __class__.action_duration_metric.labels(
                processor=self.id,
                capability=request.capability,
            ).observe(time.monotonic() - t0)
            __class__.action_count_metric.labels(
                processor=self.id,
                capability=request.capability,
            ).inc()

            logger.debug("Sending action response...")
            await flow("response").send(response, properties={"id": id})
            logger.debug("Action request completed")

        except Exception as e:

            logger.error(
                f"Exception in action service: {e}", exc_info=True
            )

            logger.info("Sending error response...")

            r = ActionResponse(
                error = Error(
                    type = "action-error",
                    message = str(e),
                ),
            )

            await flow("response").send(r, properties={"id": id})

    async def execute(self, workspace, request, flow):
        raise NotImplementedError("Subclasses must implement execute")

    @staticmethod
    def add_args(parser: ArgumentParser) -> None:

        FlowProcessor.add_args(parser)


def run() -> None:

    Processor.launch(default_ident, __doc__)
