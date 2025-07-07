
"""
Tool invocation base class
"""

import json
from prometheus_client import Counter

from .. schema import ToolRequest, ToolResponse, Error
from .. exceptions import TooManyRequests
from .. base import FlowProcessor, ConsumerSpec, ProducerSpec

default_concurrency = 1

class ToolService(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")
        concurrency = params.get("concurrency", 1)

        super(ToolService, self).__init__(**params | {
            "id": id,
            "concurrency": concurrency,
        })

        self.register_specification(
            ConsumerSpec(
                name = "request",
                schema = ToolRequest,
                handler = self.on_request,
                concurrency = concurrency,
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "response",
                schema = ToolResponse
            )
        )

        if not hasattr(__class__, "tool_invocation_metric"):
            __class__.tool_invocation_metric = Counter(
                'tool_invocation_count', 'Tool invocation count',
                ["id", "flow", "name"],
            )

    async def on_request(self, msg, consumer, flow):

        try:

            request = msg.value()

            # Sender-produced ID

            id = msg.properties()["id"]

            response = await self.invoke_tool(
                request.name,
                json.loads(request.parameters) if request.parameters else {},
            )

            if isinstance(response, str):
                await flow("response").send(
                    ToolResponse(
                        error=None,
                        text=response,
                        object=None,
                    ),
                    properties={"id": id}
                )
            else:
                await flow("response").send(
                    ToolResponse(
                        error=None,
                        text=None,
                        object=json.dumps(response),
                    ),
                    properties={"id": id}
                )

            __class__.tool_invocation_metric.labels(
                id = self.id, flow = flow.name, name = request.name,
            ).inc()

        except TooManyRequests as e:
            raise e

        except Exception as e:

            # Apart from rate limits, treat all exceptions as unrecoverable

            print(f"Exception: {e}")

            print("Send error response...", flush=True)

            await flow.producer["response"].send(
                ToolResponse(
                    error=Error(
                        type = "tool-error",
                        message = str(e),
                    ),
                    text=None,
                    object=None,
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

