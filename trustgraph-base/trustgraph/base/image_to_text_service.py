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
            __class__.image_to_text_metric = Histogram(
                'image_to_text_duration',
                'Image-to-text duration (seconds)',
                ["processor"],
                buckets=[
                    0.25, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0,
                    8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0,
                    17.0, 18.0, 19.0, 20.0, 21.0, 22.0, 23.0, 24.0, 25.0,
                    30.0, 35.0, 40.0, 45.0, 50.0, 60.0, 80.0, 100.0,
                    120.0
                ]
            )

        if not hasattr(__class__, "image_to_text_model_metric"):
            __class__.image_to_text_model_metric = Info(
                'image_to_text_model',
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

        parser.add_argument(
            '-c', '--concurrency',
            type=int,
            default=default_concurrency,
            help=f'Concurrent processing threads (default: {default_concurrency})'
        )

        FlowProcessor.add_args(parser)
