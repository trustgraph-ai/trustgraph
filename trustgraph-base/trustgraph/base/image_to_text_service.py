"""
Image-to-text description base class
"""

from __future__ import annotations

from argparse import ArgumentParser

import logging
from prometheus_client import Histogram, Info

from .. schema import ImageToTextRequest, ImageToTextResponse, Error
from .. exceptions import TooManyRequests
from .. base import FlowProcessor, ConsumerSpec, ProducerSpec, ParameterSpec

# Module logger
logger = logging.getLogger(__name__)

default_ident = "image-to-text"
default_concurrency = 1

class ImageDescriptionResult:
    def __init__(
            self, text = None, in_token = None, out_token = None,
            model = None,
    ):
        self.text = text
        self.in_token = in_token
        self.out_token = out_token
        self.model = model
    __slots__ = ["text", "in_token", "out_token", "model"]

class ImageToTextService(FlowProcessor):
    """
    Extensible service processing image description requests.

    This class handles the core logic of dispatching image-to-text
    requests to integrated underlying vision model providers
    (e.g. OpenAI).
    """

    def __init__(self, **params):

        id = params.get("id", default_ident)
        concurrency = params.get("concurrency", 1)

        super(ImageToTextService, self).__init__(**params | {
            "id": id,
            "concurrency": concurrency,
        })

        self.register_specification(
            ConsumerSpec(
                name = "request",
                schema = ImageToTextRequest,
                handler = self.on_request,
                concurrency = concurrency,
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "response",
                schema = ImageToTextResponse
            )
        )

        self.register_specification(
            ParameterSpec(
                name = "model",
            )
        )

        if not hasattr(__class__, "image_to_text_metric"):
            from . metrics import BUCKETS_LLM
            __class__.image_to_text_metric = Histogram(
                'tg_image_to_text_duration_seconds',
                'Image-to-text duration (seconds)',
                ["processor"],
                buckets=BUCKETS_LLM,
            )

        if not hasattr(__class__, "image_to_text_model_metric"):
            __class__.image_to_text_model_metric = Info(
                'tg_image_to_text_model',
                'Image-to-text model',
                ["processor"]
            )

    async def on_request(self, msg, consumer, flow):

        try:

            request = msg.value()

            # Sender-produced ID

            id = msg.properties()["id"]

            model = flow("model")

            with __class__.image_to_text_metric.labels(
                    processor=self.id,
            ).time():

                response = await self.describe_image(
                    request.image, request.mime_type,
                    request.prompt, request.system, model,
                )

            await flow("response").send(
                ImageToTextResponse(
                    error=None,
                    description=response.text,
                    in_token=response.in_token,
                    out_token=response.out_token,
                    model=response.model,
                ),
                properties={"id": id}
            )

            __class__.image_to_text_model_metric.labels(
                processor=self.id,
            ).info({
                "model": str(model) if model is not None else "",
            })

        except TooManyRequests as e:
            raise e

        except Exception as e:

            # Apart from rate limits, treat all exceptions as unrecoverable

            logger.error(f"Image-to-text service exception: {e}", exc_info=True)

            logger.debug("Sending error response...")

            await flow.producer["response"].send(
                ImageToTextResponse(
                    error=Error(
                        type = "image-to-text-error",
                        message = str(e),
                    ),
                    description=None,
                    in_token=None,
                    out_token=None,
                    model=None,
                ),
                properties={"id": id}
            )

    @staticmethod
    def add_args(parser: ArgumentParser) -> None:

        FlowProcessor.add_args(parser)
