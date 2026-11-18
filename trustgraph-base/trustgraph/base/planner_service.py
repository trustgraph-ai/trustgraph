"""
Planner service.  Input is a goal and run context.  Output is an
execution plan — a DAG of steps with capability bindings.
"""

from __future__ import annotations

from argparse import ArgumentParser

import time
import logging
from prometheus_client import Histogram

from .. schema import PlannerRequest, PlannerResponse, Error

from . flow_processor import FlowProcessor
from . consumer_spec import ConsumerSpec
from . producer_spec import ProducerSpec

logger = logging.getLogger(__name__)

default_ident = "planner"
default_concurrency = 5


class PlannerService(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")
        concurrency = params.get("concurrency", default_concurrency)

        super(PlannerService, self).__init__(**params | { "id": id })

        self.register_specification(
            ConsumerSpec(
                name = "request",
                schema = PlannerRequest,
                handler = self.on_message,
                concurrency = concurrency,
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "response",
                schema = PlannerResponse,
            )
        )

        if not hasattr(__class__, "plan_duration_metric"):
            from . metrics import BUCKETS_LLM
            __class__.plan_duration_metric = Histogram(
                'tg_planner_duration_seconds',
                'Planner request latency (seconds)',
                ["processor"],
                buckets=BUCKETS_LLM,
            )
            __class__.plan_step_count_metric = Histogram(
                'tg_planner_step_count',
                'Number of steps in generated plan',
                ["processor"],
                buckets=[1, 2, 3, 5, 8, 13, 21, 34],
            )

    async def on_message(self, msg, consumer, flow):

        try:

            request = msg.value()

            id = msg.properties()["id"]

            logger.debug(f"Handling planner request {id}...")

            workspace = flow.workspace

            t0 = time.monotonic()
            response = await self.create_plan(workspace, request, flow)
            __class__.plan_duration_metric.labels(
                processor=self.id,
            ).observe(time.monotonic() - t0)
            __class__.plan_step_count_metric.labels(
                processor=self.id,
            ).observe(len(response.steps))

            logger.debug("Sending planner response...")
            await flow("response").send(response, properties={"id": id})
            logger.debug("Planner request completed")

        except Exception as e:

            logger.error(
                f"Exception in planner service: {e}", exc_info=True
            )

            logger.info("Sending error response...")

            r = PlannerResponse(
                error = Error(
                    type = "planner-error",
                    message = str(e),
                ),
            )

            await flow("response").send(r, properties={"id": id})

    async def create_plan(self, workspace, request, flow):
        raise NotImplementedError("Subclasses must implement create_plan")

    @staticmethod
    def add_args(parser: ArgumentParser) -> None:

        FlowProcessor.add_args(parser)


def run() -> None:

    Processor.launch(default_ident, __doc__)
