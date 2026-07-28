"""
Document embeddings query service.  Input is vectors.  Output is list of
embeddings.
"""

from __future__ import annotations

from argparse import ArgumentParser

import time
import logging
from prometheus_client import Histogram

from .. schema import DocumentEmbeddingsRequest, DocumentEmbeddingsResponse
from .. schema import Error, Term

from . flow_processor import FlowProcessor
from . consumer_spec import ConsumerSpec
from . producer_spec import ProducerSpec

# Module logger
logger = logging.getLogger(__name__)

default_ident = "doc-embeddings-query"
default_concurrency = 10

class DocumentEmbeddingsQueryService(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")
        concurrency = params.get("concurrency", default_concurrency)

        super(DocumentEmbeddingsQueryService, self).__init__(
            **params | { "id": id }
        )

        self.register_specification(
            ConsumerSpec(
                name = "request",
                schema = DocumentEmbeddingsRequest,
                handler = self.on_message,
                concurrency = concurrency,
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "response",
                schema = DocumentEmbeddingsResponse,
            )
        )

        if not hasattr(__class__, "query_duration_metric"):
            from . metrics import BUCKETS_STANDARD
            __class__.query_duration_metric = Histogram(
                'tg_document_embeddings_query_duration_seconds',
                'Document embeddings query backend latency (seconds)',
                ["processor"],
                buckets=BUCKETS_STANDARD,
            )
            __class__.query_result_count_metric = Histogram(
                'tg_document_embeddings_query_result_count',
                'Number of chunks returned per query',
                ["processor"],
                buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000],
            )

    async def on_message(self, msg, consumer, flow):

        try:

            request = msg.value()

            # Sender-produced ID
            id = msg.properties()["id"]

            logger.debug(f"Handling document embeddings query request {id}...")

            t0 = time.monotonic()
            docs = await self.query_document_embeddings(
                flow.workspace, request,
            )
            __class__.query_duration_metric.labels(
                processor=self.id,
            ).observe(time.monotonic() - t0)
            __class__.query_result_count_metric.labels(
                processor=self.id,
            ).observe(len(docs))

            logger.debug("Sending document embeddings query response...")
            r = DocumentEmbeddingsResponse(chunks=docs, error=None)
            await flow("response").send(r, properties={"id": id})

            logger.debug("Document embeddings query request completed")

        except Exception as e:

            logger.error(f"Exception in document embeddings query service: {e}", exc_info=True)

            logger.info("Sending error response...")

            r = DocumentEmbeddingsResponse(
                error=Error(
                    type = "document-embeddings-query-error",
                    message = str(e),
                ),
                chunks=[],
            )

            await flow("response").send(r, properties={"id": id})

    @staticmethod
    def add_args(parser: ArgumentParser) -> None:

        FlowProcessor.add_args(parser)

def run() -> None:

    Processor.launch(default_ident, __doc__)

