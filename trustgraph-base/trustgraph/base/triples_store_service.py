"""
Triples store base class
"""

from __future__ import annotations

from argparse import ArgumentParser

import logging
import time
from prometheus_client import Counter, Histogram

from .. schema import Triples
from .. base import FlowProcessor, ConsumerSpec
from .. exceptions import TooManyRequests

# Module logger
logger = logging.getLogger(__name__)

default_ident = "triples-write"

class TriplesStoreService(FlowProcessor):
    """
    Component for maintaining the triples store.

    This service acts as a processor in the flow that receives knowledge triples
    and writes them persistently into an overarching graph database or equivalent backend.
    """

    def __init__(self, **params):

        id = params.get("id")

        super(TriplesStoreService, self).__init__(**params | { "id": id })

        if not hasattr(__class__, "_metrics_initialized"):
            from . metrics import BUCKETS_STANDARD
            __class__._metrics_initialized = True
            __class__.store_write_duration_metric = Histogram(
                'tg_triples_store_write_duration_seconds',
                'Triples store write latency per batch',
                ["processor"],
                buckets=BUCKETS_STANDARD,
            )
            __class__.store_write_batch_metric = Histogram(
                'tg_triples_store_write_batch_size',
                'Number of triples per write batch',
                ["processor"],
                buckets=[1, 5, 10, 20, 50, 100, 200, 500],
            )
            __class__.store_write_error_metric = Counter(
                'tg_triples_store_write_error_total',
                'Triples store write errors',
                ["processor"],
            )

        self.register_specification(
            ConsumerSpec(
                name = "input",
                schema = Triples,
                handler = self.on_message
            )
        )

    async def on_message(self, msg, consumer, flow):

        try:

            request = msg.value()

            t0 = time.monotonic()

            # Workspace is derived from the flow the message arrived on,
            # not from fields in the message payload. Topic routing is
            # the isolation boundary.
            await self.store_triples(flow.workspace, request)

            __class__.store_write_duration_metric.labels(
                processor=self.id,
            ).observe(time.monotonic() - t0)
            __class__.store_write_batch_metric.labels(
                processor=self.id,
            ).observe(len(request.triples) if request.triples else 0)

        except TooManyRequests as e:
            raise e

        except Exception as e:
            __class__.store_write_error_metric.labels(
                processor=self.id,
            ).inc()
            logger.error(f"Exception in triples store service: {e}", exc_info=True)
            raise e

    @staticmethod
    def add_args(parser: ArgumentParser) -> None:

        FlowProcessor.add_args(parser)

