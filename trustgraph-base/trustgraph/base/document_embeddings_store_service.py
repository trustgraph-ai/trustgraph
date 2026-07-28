"""
Document embeddings store base class
"""

from __future__ import annotations

from argparse import ArgumentParser

import logging
import time
from prometheus_client import Counter, Histogram

from .. schema import DocumentEmbeddings
from .. base import FlowProcessor, ConsumerSpec
from .. exceptions import TooManyRequests

# Module logger
logger = logging.getLogger(__name__)

default_ident = "document-embeddings-write"

class DocumentEmbeddingsStoreService(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")

        super(DocumentEmbeddingsStoreService, self).__init__(
            **params | { "id": id }
        )

        if not hasattr(__class__, "_metrics_initialized"):
            from . metrics import BUCKETS_STANDARD
            __class__._metrics_initialized = True
            __class__.store_write_duration_metric = Histogram(
                'tg_document_embeddings_store_write_duration_seconds',
                'Document embeddings store write latency per batch',
                ["processor"],
                buckets=BUCKETS_STANDARD,
            )
            __class__.store_write_batch_metric = Histogram(
                'tg_document_embeddings_store_write_batch_size',
                'Number of embeddings per write batch',
                ["processor"],
                buckets=[1, 5, 10, 20, 50, 100, 200, 500],
            )
            __class__.store_write_error_metric = Counter(
                'tg_document_embeddings_store_write_error_total',
                'Document embeddings store write errors',
                ["processor"],
            )

        self.register_specification(
            ConsumerSpec(
                name = "input",
                schema = DocumentEmbeddings,
                handler = self.on_message
            )
        )

    async def on_message(self, msg, consumer, flow):

        try:

            request = msg.value()

            t0 = time.monotonic()

            # Workspace comes from the flow the message arrived on.
            await self.store_document_embeddings(flow.workspace, request)

            __class__.store_write_duration_metric.labels(
                processor=self.id,
            ).observe(time.monotonic() - t0)
            __class__.store_write_batch_metric.labels(
                processor=self.id,
            ).observe(len(request.vectors) if request.vectors else 0)

        except TooManyRequests as e:
            raise e

        except Exception as e:
            __class__.store_write_error_metric.labels(
                processor=self.id,
            ).inc()
            logger.error(f"Exception in document embeddings store service: {e}", exc_info=True)
            raise e

    @staticmethod
    def add_args(parser: ArgumentParser) -> None:

        FlowProcessor.add_args(parser)

