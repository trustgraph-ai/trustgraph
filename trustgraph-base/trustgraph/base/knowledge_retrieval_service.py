"""
Knowledge retrieval service.  Input is concepts, seed entities, or
graph node URIs.  Output is a ranked subgraph of edges retrieved
via embedding lookup, graph traversal, and cross-encoder reranking.
"""

from __future__ import annotations

from argparse import ArgumentParser

import time
import logging
from prometheus_client import Histogram, Counter

from .. schema import (
    KnowledgeRetrievalRequest, KnowledgeRetrievalResponse, Error,
)

from . flow_processor import FlowProcessor
from . consumer_spec import ConsumerSpec
from . producer_spec import ProducerSpec

logger = logging.getLogger(__name__)

default_ident = "knowledge-retrieval"
default_concurrency = 1


class KnowledgeRetrievalService(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")
        concurrency = params.get("concurrency", default_concurrency)

        super(KnowledgeRetrievalService, self).__init__(
            **params | { "id": id }
        )

        self.register_specification(
            ConsumerSpec(
                name = "request",
                schema = KnowledgeRetrievalRequest,
                handler = self.on_message,
                concurrency = concurrency,
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "response",
                schema = KnowledgeRetrievalResponse,
            )
        )

        if not hasattr(__class__, "retrieval_duration_metric"):
            from . metrics import BUCKETS_LLM
            __class__.retrieval_duration_metric = Histogram(
                'tg_knowledge_retrieval_duration_seconds',
                'Knowledge retrieval latency (seconds)',
                ["processor"],
                buckets=BUCKETS_LLM,
            )
            __class__.retrieval_count_metric = Counter(
                'tg_knowledge_retrieval_total',
                'Number of knowledge retrieval requests',
                ["processor"],
            )
            __class__.retrieval_edges_metric = Counter(
                'tg_knowledge_retrieval_edges_total',
                'Total edges returned by knowledge retrieval',
                ["processor"],
            )

    async def on_message(self, msg, consumer, flow):

        try:

            request = msg.value()

            id = msg.properties()["id"]

            logger.debug(f"Handling knowledge retrieval request {id}...")

            workspace = flow.workspace

            t0 = time.monotonic()
            response = await self.retrieve(workspace, request, flow)
            __class__.retrieval_duration_metric.labels(
                processor=self.id,
            ).observe(time.monotonic() - t0)
            __class__.retrieval_count_metric.labels(
                processor=self.id,
            ).inc()
            __class__.retrieval_edges_metric.labels(
                processor=self.id,
            ).inc(len(response.edges))

            logger.debug("Sending knowledge retrieval response...")
            await flow("response").send(response, properties={"id": id})
            logger.debug("Knowledge retrieval request completed")

        except Exception as e:

            logger.error(
                f"Exception in knowledge retrieval service: {e}",
                exc_info=True,
            )

            logger.info("Sending error response...")

            r = KnowledgeRetrievalResponse(
                error = Error(
                    type = "knowledge-retrieval-error",
                    message = str(e),
                ),
            )

            await flow("response").send(r, properties={"id": id})

    async def retrieve(self, workspace, request, flow):
        raise NotImplementedError("Subclasses must implement retrieve")

    @staticmethod
    def add_args(parser: ArgumentParser) -> None:

        FlowProcessor.add_args(parser)


def run() -> None:

    Processor.launch(default_ident, __doc__)
