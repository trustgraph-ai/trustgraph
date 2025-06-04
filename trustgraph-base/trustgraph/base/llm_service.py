
"""
LLM text completion base class
"""

import time
from prometheus_client import Histogram

from .. schema import TextCompletionRequest, TextCompletionResponse, Error
from .. exceptions import TooManyRequests
from .. base import FlowProcessor, ConsumerSpec, ProducerSpec

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

class LlmService(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")
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

    async def on_request(self, msg, consumer, flow):

        try:

            request = msg.value()

            # Sender-produced ID

            id = msg.properties()["id"]

            with __class__.text_completion_metric.labels(
                    id=self.id,
                    flow=f"{flow.name}-{consumer.name}",
            ).time():

                response = await self.generate_content(
                    request.system, request.prompt
                )

            await flow("response").send(
                TextCompletionResponse(
                    error=None,
                    response=response.text,
                    in_token=response.in_token,
                    out_token=response.out_token,
                    model=response.model
                ),
                properties={"id": id}
            )

        except TooManyRequests as e:
            raise e

        except Exception as e:

            # Apart from rate limits, treat all exceptions as unrecoverable

            print(f"Exception: {e}")

            print("Send error response...", flush=True)

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
                ),
                properties={"id": id}
            )

    @staticmethod
    def add_args(parser):

        parser.add_argument(
            '-c', '--concurrency',
            type=int,
            default=default_concurrency,
            help=f'Concurrent processing threads (default: {default_concurrency})'
        )

        FlowProcessor.add_args(parser)

