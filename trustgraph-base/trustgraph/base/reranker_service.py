
from __future__ import annotations

from argparse import ArgumentParser

import time
import logging
from prometheus_client import Counter, Histogram

from .. schema import (
    RerankerRequest, RerankerResponse, RerankerResult, Error,
)
from .. exceptions import TooManyRequests
from .. base import FlowProcessor, ConsumerSpec, ProducerSpec, ParameterSpec

logger = logging.getLogger(__name__)

default_ident = "reranker"
default_concurrency = 1

class RerankerService(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")
        concurrency = params.get("concurrency", 1)

        super(RerankerService, self).__init__(**params | {
            "id": id,
            "concurrency": concurrency,
        })

        self.register_specification(
            ConsumerSpec(
                name = "request",
                schema = RerankerRequest,
                handler = self.on_request,
                concurrency = concurrency,
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "response",
                schema = RerankerResponse
            )
        )

        self.register_specification(
            ParameterSpec(
                name = "model",
            )
        )

        if not hasattr(__class__, "reranker_request_metric"):
            from . metrics import BUCKETS_STANDARD
            __class__.reranker_request_metric = Counter(
                'tg_reranker_request_total',
                'Reranker requests per model',
                ["processor", "model"],
            )
            __class__.reranker_duration_metric = Histogram(
                'tg_reranker_duration_seconds',
                'Rerank call latency (seconds)',
                ["processor", "model"],
                buckets=BUCKETS_STANDARD,
            )
            __class__.reranker_result_count_metric = Histogram(
                'tg_reranker_result_count',
                'Number of results per rerank call',
                ["processor", "model"],
                buckets=[1, 2, 5, 10, 20, 50, 100],
            )

    async def on_request(self, msg, consumer, flow):

        try:

            request = msg.value()

            id = msg.properties()["id"]

            logger.debug(f"Handling reranker request {id}...")

            model = flow("model")
            model_label = str(model) if model else ""

            t0 = time.monotonic()
            results = await self.on_rerank(
                request.queries, request.documents,
                request.limit, model=model,
            )
            duration = time.monotonic() - t0

            labels = dict(processor=self.id, model=model_label)
            __class__.reranker_request_metric.labels(**labels).inc()
            __class__.reranker_duration_metric.labels(**labels).observe(
                duration,
            )
            __class__.reranker_result_count_metric.labels(**labels).observe(
                len(results),
            )

            await flow("response").send(
                RerankerResponse(
                    error = None,
                    results = results,
                ),
                properties={"id": id}
            )

            logger.debug("Reranker request handled successfully")

        except TooManyRequests as e:
            raise e

        except Exception as e:

            logger.error(f"Exception in reranker service: {e}", exc_info=True)

            logger.info("Sending error response...")

            await flow.producer["response"].send(
                RerankerResponse(
                    error=Error(
                        type = "reranker-error",
                        message = str(e),
                    ),
                    results=[],
                ),
                properties={"id": id}
            )

    @staticmethod
    def add_args(parser: ArgumentParser) -> None:

        FlowProcessor.add_args(parser)
