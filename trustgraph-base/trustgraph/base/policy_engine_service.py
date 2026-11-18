"""
Policy engine service.  Input is a subject (plan, step, or artifact)
plus principal context.  Output is a policy attestation with verdict,
disclosure posture, and optional redaction directives.
"""

from __future__ import annotations

from argparse import ArgumentParser

import time
import logging
from prometheus_client import Histogram, Counter

from .. schema import PolicyEngineRequest, PolicyEngineResponse, Error

from . flow_processor import FlowProcessor
from . consumer_spec import ConsumerSpec
from . producer_spec import ProducerSpec

logger = logging.getLogger(__name__)

default_ident = "policy"
default_concurrency = 10


class PolicyEngineService(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")
        concurrency = params.get("concurrency", default_concurrency)

        super(PolicyEngineService, self).__init__(**params | { "id": id })

        self.register_specification(
            ConsumerSpec(
                name = "request",
                schema = PolicyEngineRequest,
                handler = self.on_message,
                concurrency = concurrency,
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "response",
                schema = PolicyEngineResponse,
            )
        )

        if not hasattr(__class__, "eval_duration_metric"):
            from . metrics import BUCKETS_STANDARD
            __class__.eval_duration_metric = Histogram(
                'tg_policy_engine_duration_seconds',
                'Policy engine evaluation latency (seconds)',
                ["processor"],
                buckets=BUCKETS_STANDARD,
            )
            __class__.eval_verdict_metric = Counter(
                'tg_policy_engine_verdict_total',
                'Policy engine verdicts by type',
                ["processor", "verdict"],
            )

    async def on_message(self, msg, consumer, flow):

        try:

            request = msg.value()

            id = msg.properties()["id"]

            logger.debug(f"Handling policy engine request {id}...")

            workspace = flow.workspace

            t0 = time.monotonic()
            response = await self.evaluate(workspace, request, flow)
            __class__.eval_duration_metric.labels(
                processor=self.id,
            ).observe(time.monotonic() - t0)
            __class__.eval_verdict_metric.labels(
                processor=self.id,
                verdict=response.verdict,
            ).inc()

            logger.debug("Sending policy engine response...")
            await flow("response").send(response, properties={"id": id})
            logger.debug("Policy engine request completed")

        except Exception as e:

            logger.error(
                f"Exception in policy engine service: {e}", exc_info=True
            )

            logger.info("Sending error response...")

            r = PolicyEngineResponse(
                error = Error(
                    type = "policy-error",
                    message = str(e),
                ),
            )

            await flow("response").send(r, properties={"id": id})

    async def evaluate(self, workspace, request, flow):
        raise NotImplementedError("Subclasses must implement evaluate")

    @staticmethod
    def add_args(parser: ArgumentParser) -> None:

        FlowProcessor.add_args(parser)


def run() -> None:

    Processor.launch(default_ident, __doc__)
