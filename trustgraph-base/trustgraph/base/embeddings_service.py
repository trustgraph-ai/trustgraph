"""
Embeddings resolution base class
"""

from __future__ import annotations

from argparse import ArgumentParser

import time
import logging
from prometheus_client import Counter, Histogram

from .. schema import EmbeddingsRequest, EmbeddingsResponse, Error
from .. exceptions import TooManyRequests
from .. base import FlowProcessor, ConsumerSpec, ProducerSpec, ParameterSpec

# Module logger
logger = logging.getLogger(__name__)

default_ident = "embeddings"
default_concurrency = 1

class EmbeddingsService(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")
        concurrency = params.get("concurrency", 1)

        super(EmbeddingsService, self).__init__(**params | {
            "id": id,
            "concurrency": concurrency,
        })

        self.register_specification(
            ConsumerSpec(
                name = "request",
                schema = EmbeddingsRequest,
                handler = self.on_request,
                concurrency = concurrency,
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "response",
                schema = EmbeddingsResponse
            )
        )

        self.register_specification(
            ParameterSpec(
                name = "model",
            )
        )

        if not hasattr(__class__, "embeddings_request_metric"):
            from . metrics import BUCKETS_STANDARD
            __class__.embeddings_request_metric = Counter(
                'tg_embeddings_request_total',
                'Embeddings requests per model',
                ["processor", "model"],
            )
            __class__.embeddings_duration_metric = Histogram(
                'tg_embeddings_duration_seconds',
                'Embeddings call latency (seconds)',
                ["processor", "model"],
                buckets=BUCKETS_STANDARD,
            )
            __class__.embeddings_batch_size_metric = Histogram(
                'tg_embeddings_batch_size',
                'Number of texts per embedding request',
                ["processor", "model"],
                buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000],
            )

    async def on_request(self, msg, consumer, flow):

        try:

            request = msg.value()

            # Sender-produced ID

            id = msg.properties()["id"]

            logger.debug(f"Handling embeddings request {id}...")

            model = flow("model")
            model_label = str(model) if model else ""

            t0 = time.monotonic()
            vectors = await self.on_embeddings(request.texts, model=model)
            duration = time.monotonic() - t0

            labels = dict(processor=self.id, model=model_label)
            __class__.embeddings_request_metric.labels(**labels).inc()
            __class__.embeddings_duration_metric.labels(**labels).observe(
                duration,
            )
            __class__.embeddings_batch_size_metric.labels(**labels).observe(
                len(request.texts),
            )

            await flow("response").send(
                EmbeddingsResponse(
                    error = None,
                    vectors = vectors,
                ),
                properties={"id": id}
            )

            logger.debug("Embeddings request handled successfully")

        except TooManyRequests as e:
            raise e

        except Exception as e:

            # Apart from rate limits, treat all exceptions as unrecoverable

            logger.error(f"Exception in embeddings service: {e}", exc_info=True)

            logger.info("Sending error response...")

            await flow.producer["response"].send(
                EmbeddingsResponse(
                    error=Error(
                        type = "embeddings-error",
                        message = str(e),
                    ),
                    vectors=[],
                ),
                properties={"id": id}
            )

    @staticmethod
    def add_args(parser: ArgumentParser) -> None:

        FlowProcessor.add_args(parser)


