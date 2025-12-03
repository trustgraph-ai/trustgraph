
"""
LLM text completion base class
"""

import time
import logging
from prometheus_client import Histogram, Info

from .. schema import TextCompletionRequest, TextCompletionResponse, Error
from .. exceptions import TooManyRequests
from .. base import FlowProcessor, ConsumerSpec, ProducerSpec, ParameterSpec

# Module logger
logger = logging.getLogger(__name__)

default_ident = "text-completion"
default_concurrency = 1

class LlmResult:
    def __init__(
            self, text = None, in_token = None, out_token = None,
            model = None,
    ):
        self.text = text
        self.in_token = in_token
        self.out_token = out_token
        self.model = model
    __slots__ = ["text", "in_token", "out_token", "model"]

class LlmChunk:
    """Represents a streaming chunk from an LLM"""
    def __init__(
            self, text = None, in_token = None, out_token = None,
            model = None, is_final = False,
    ):
        self.text = text
        self.in_token = in_token
        self.out_token = out_token
        self.model = model
        self.is_final = is_final
    __slots__ = ["text", "in_token", "out_token", "model", "is_final"]

class LlmService(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id", default_ident)
        concurrency = params.get("concurrency", 1)

        super(LlmService, self).__init__(**params | {
            "id": id,
            "concurrency": concurrency,
        })

        self.register_specification(
            ConsumerSpec(
                name = "request",
                schema = TextCompletionRequest,
                handler = self.on_request,
                concurrency = concurrency,
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "response",
                schema = TextCompletionResponse
            )
        )

        self.register_specification(
            ParameterSpec(
                name = "model",
            )
        )

        self.register_specification(
            ParameterSpec(
                name = "temperature",
            )
        )

        if not hasattr(__class__, "text_completion_metric"):
            __class__.text_completion_metric = Histogram(
                'text_completion_duration',
                'Text completion duration (seconds)',
                ["id", "flow"],
                buckets=[
                    0.25, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0,
                    8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0,
                    17.0, 18.0, 19.0, 20.0, 21.0, 22.0, 23.0, 24.0, 25.0,
                    30.0, 35.0, 40.0, 45.0, 50.0, 60.0, 80.0, 100.0,
                    120.0
                ]
            )

        if not hasattr(__class__, "text_completion_model_metric"):
            __class__.text_completion_model_metric = Info(
                'text_completion_model',
                'Text completion model',
                ["processor", "flow"]
            )

    async def on_request(self, msg, consumer, flow):

        try:

            request = msg.value()

            # Sender-produced ID

            id = msg.properties()["id"]

            model = flow("model")
            temperature = flow("temperature")

            # Check if streaming is requested and supported
            streaming = getattr(request, 'streaming', False)

            if streaming and self.supports_streaming():

                # Streaming mode
                with __class__.text_completion_metric.labels(
                        id=self.id,
                        flow=f"{flow.name}-{consumer.name}",
                ).time():

                    async for chunk in self.generate_content_stream(
                        request.system, request.prompt, model, temperature
                    ):
                        await flow("response").send(
                            TextCompletionResponse(
                                error=None,
                                response=chunk.text,
                                in_token=chunk.in_token,
                                out_token=chunk.out_token,
                                model=chunk.model,
                                end_of_stream=chunk.is_final
                            ),
                            properties={"id": id}
                        )

            else:

                # Non-streaming mode (original behavior)
                with __class__.text_completion_metric.labels(
                        id=self.id,
                        flow=f"{flow.name}-{consumer.name}",
                ).time():

                    response = await self.generate_content(
                        request.system, request.prompt, model, temperature
                    )

                await flow("response").send(
                    TextCompletionResponse(
                        error=None,
                        response=response.text,
                        in_token=response.in_token,
                        out_token=response.out_token,
                        model=response.model,
                        end_of_stream=True
                    ),
                    properties={"id": id}
                )

            __class__.text_completion_model_metric.labels(
                processor = self.id,
                flow = flow.name
            ).info({
                "model": str(model) if model is not None else "",
                "temperature": str(temperature) if temperature is not None else "",
            })

        except TooManyRequests as e:
            raise e

        except Exception as e:

            # Apart from rate limits, treat all exceptions as unrecoverable

            logger.error(f"LLM service exception: {e}", exc_info=True)

            logger.debug("Sending error response...")

            await flow.producer["response"].send(
                TextCompletionResponse(
                    error=Error(
                        type = "llm-error",
                        message = str(e),
                    ),
                    response=None,
                    in_token=None,
                    out_token=None,
                    model=None,
                    end_of_stream=True
                ),
                properties={"id": id}
            )

    def supports_streaming(self):
        """
        Override in subclass to indicate streaming support.
        Returns False by default.
        """
        return False

    async def generate_content_stream(self, system, prompt, model=None, temperature=None):
        """
        Override in subclass to implement streaming.
        Should yield LlmChunk objects.
        The final chunk should have is_final=True.
        """
        raise NotImplementedError("Streaming not implemented for this provider")

    @staticmethod
    def add_args(parser):

        parser.add_argument(
            '-c', '--concurrency',
            type=int,
            default=default_concurrency,
            help=f'Concurrent processing threads (default: {default_concurrency})'
        )

        FlowProcessor.add_args(parser)

