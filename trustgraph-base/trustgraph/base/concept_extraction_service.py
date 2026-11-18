"""
Concept extraction service.  Input is a natural-language query.
Output is a list of key concepts extracted from the query.
"""

from __future__ import annotations

from argparse import ArgumentParser

import time
import logging
from prometheus_client import Histogram, Counter

from .. schema import (
    ConceptExtractionRequest, ConceptExtractionResponse, Error,
)

from . flow_processor import FlowProcessor
from . consumer_spec import ConsumerSpec
from . producer_spec import ProducerSpec

logger = logging.getLogger(__name__)

default_ident = "concept-extraction"
default_concurrency = 10


class ConceptExtractionService(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")
        concurrency = params.get("concurrency", default_concurrency)

        super(ConceptExtractionService, self).__init__(**params | { "id": id })

        self.register_specification(
            ConsumerSpec(
                name = "request",
                schema = ConceptExtractionRequest,
                handler = self.on_message,
                concurrency = concurrency,
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "response",
                schema = ConceptExtractionResponse,
            )
        )

        if not hasattr(__class__, "extract_duration_metric"):
            from . metrics import BUCKETS_LLM
            __class__.extract_duration_metric = Histogram(
                'tg_concept_extraction_duration_seconds',
                'Concept extraction latency (seconds)',
                ["processor"],
                buckets=BUCKETS_LLM,
            )
            __class__.extract_count_metric = Counter(
                'tg_concept_extraction_total',
                'Number of concept extraction requests',
                ["processor"],
            )

    async def on_message(self, msg, consumer, flow):

        try:

            request = msg.value()

            id = msg.properties()["id"]

            logger.debug(f"Handling concept extraction request {id}...")

            workspace = flow.workspace

            t0 = time.monotonic()
            response = await self.extract(workspace, request, flow)
            __class__.extract_duration_metric.labels(
                processor=self.id,
            ).observe(time.monotonic() - t0)
            __class__.extract_count_metric.labels(
                processor=self.id,
            ).inc()

            logger.debug("Sending concept extraction response...")
            await flow("response").send(response, properties={"id": id})
            logger.debug("Concept extraction request completed")

        except Exception as e:

            logger.error(
                f"Exception in concept extraction service: {e}",
                exc_info=True,
            )

            logger.info("Sending error response...")

            r = ConceptExtractionResponse(
                error = Error(
                    type = "concept-extraction-error",
                    message = str(e),
                ),
            )

            await flow("response").send(r, properties={"id": id})

    async def extract(self, workspace, request, flow):
        raise NotImplementedError("Subclasses must implement extract")

    @staticmethod
    def add_args(parser: ArgumentParser) -> None:

        FlowProcessor.add_args(parser)


def run() -> None:

    Processor.launch(default_ident, __doc__)
