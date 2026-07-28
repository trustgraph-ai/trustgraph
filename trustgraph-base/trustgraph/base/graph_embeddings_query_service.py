"""
Graph embeddings query service.  Input is vectors.  Output is list of
embeddings.
"""

from __future__ import annotations

from argparse import ArgumentParser

import time
import logging
from prometheus_client import Histogram

from .. schema import GraphEmbeddingsRequest, GraphEmbeddingsResponse
from .. schema import Error, Term

from . flow_processor import FlowProcessor
from . consumer_spec import ConsumerSpec
from . producer_spec import ProducerSpec

# Module logger
logger = logging.getLogger(__name__)

default_ident = "graph-embeddings-query"
default_concurrency = 10

class GraphEmbeddingsQueryService(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")
        concurrency = params.get("concurrency", default_concurrency)

        super(GraphEmbeddingsQueryService, self).__init__(
            **params | { "id": id }
        )

        self.register_specification(
            ConsumerSpec(
                name = "request",
                schema = GraphEmbeddingsRequest,
                handler = self.on_message,
                concurrency = concurrency,
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "response",
                schema = GraphEmbeddingsResponse,
            )
        )

        if not hasattr(__class__, "query_duration_metric"):
            from . metrics import BUCKETS_STANDARD
            __class__.query_duration_metric = Histogram(
                'tg_graph_embeddings_query_duration_seconds',
                'Graph embeddings query backend latency (seconds)',
                ["processor"],
                buckets=BUCKETS_STANDARD,
            )
            __class__.query_result_count_metric = Histogram(
                'tg_graph_embeddings_query_result_count',
                'Number of entities returned per query',
                ["processor"],
                buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000],
            )

    async def on_message(self, msg, consumer, flow):

        try:

            request = msg.value()

            # Sender-produced ID
            id = msg.properties()["id"]

            logger.debug(f"Handling graph embeddings query request {id}...")

            t0 = time.monotonic()
            entities = await self.query_graph_embeddings(
                flow.workspace, request,
            )
            __class__.query_duration_metric.labels(
                processor=self.id,
            ).observe(time.monotonic() - t0)
            __class__.query_result_count_metric.labels(
                processor=self.id,
            ).observe(len(entities))

            logger.debug("Sending graph embeddings query response...")
            r = GraphEmbeddingsResponse(entities=entities, error=None)
            await flow("response").send(r, properties={"id": id})

            logger.debug("Graph embeddings query request completed")

        except Exception as e:

            logger.error(f"Exception in graph embeddings query service: {e}", exc_info=True)

            logger.info("Sending error response...")

            r = GraphEmbeddingsResponse(
                error=Error(
                    type = "graph-embeddings-query-error",
                    message = str(e),
                ),
                response=None,
            )

            await flow("response").send(r, properties={"id": id})

    @staticmethod
    def add_args(parser: ArgumentParser) -> None:

        FlowProcessor.add_args(parser)

def run() -> None:

    Processor.launch(default_ident, __doc__)

