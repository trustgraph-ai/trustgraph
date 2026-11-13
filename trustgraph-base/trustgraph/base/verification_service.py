"""
Verification service.  Input is a step artifact and expected port
contract.  Output is a pass/fail verdict with violations.
"""

from __future__ import annotations

from argparse import ArgumentParser

import time
import logging
from prometheus_client import Histogram, Counter

from .. schema import VerificationRequest, VerificationResponse, Error

from . flow_processor import FlowProcessor
from . consumer_spec import ConsumerSpec
from . producer_spec import ProducerSpec

logger = logging.getLogger(__name__)

default_ident = "verification"
default_concurrency = 10


class VerificationService(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")
        concurrency = params.get("concurrency", default_concurrency)

        super(VerificationService, self).__init__(**params | { "id": id })

        self.register_specification(
            ConsumerSpec(
                name = "request",
                schema = VerificationRequest,
                handler = self.on_message,
                concurrency = concurrency,
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "response",
                schema = VerificationResponse,
            )
        )

        if not hasattr(__class__, "verify_duration_metric"):
            from . metrics import BUCKETS_STANDARD
            __class__.verify_duration_metric = Histogram(
                'tg_verification_duration_seconds',
                'Verification request latency (seconds)',
                ["processor"],
                buckets=BUCKETS_STANDARD,
            )
            __class__.verify_pass_metric = Counter(
                'tg_verification_pass_total',
                'Number of artifacts that passed verification',
                ["processor"],
            )
            __class__.verify_fail_metric = Counter(
                'tg_verification_fail_total',
                'Number of artifacts that failed verification',
                ["processor"],
            )

    async def on_message(self, msg, consumer, flow):

        try:

            request = msg.value()

            id = msg.properties()["id"]

            logger.debug(f"Handling verification request {id}...")

            workspace = flow.workspace

            t0 = time.monotonic()
            response = await self.verify(workspace, request, flow)
            __class__.verify_duration_metric.labels(
                processor=self.id,
            ).observe(time.monotonic() - t0)

            if response.valid:
                __class__.verify_pass_metric.labels(
                    processor=self.id,
                ).inc()
            else:
                __class__.verify_fail_metric.labels(
                    processor=self.id,
                ).inc()

            logger.debug("Sending verification response...")
            await flow("response").send(response, properties={"id": id})
            logger.debug("Verification request completed")

        except Exception as e:

            logger.error(
                f"Exception in verification service: {e}", exc_info=True
            )

            logger.info("Sending error response...")

            r = VerificationResponse(
                error = Error(
                    type = "verification-error",
                    message = str(e),
                ),
            )

            await flow("response").send(r, properties={"id": id})

    async def verify(self, workspace, request, flow):
        raise NotImplementedError("Subclasses must implement verify")

    @staticmethod
    def add_args(parser: ArgumentParser) -> None:

        FlowProcessor.add_args(parser)


def run() -> None:

    Processor.launch(default_ident, __doc__)
