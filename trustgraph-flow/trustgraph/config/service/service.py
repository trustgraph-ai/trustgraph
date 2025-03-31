
"""
Config service.  Fetchs an extract from the Wikipedia page
using the API.
"""

from trustgraph.schema import ConfigItem, ConfigItems, ConfigUpdate
from trustgraph.schema import ConfigRequest, ConfigResponse, ConfigPush
from trustgraph.schema import config_request_queue, config_response_queue
from trustgraph.schema import config_push_queue
from trustgraph.log_level import LogLevel
from trustgraph.base import ConsumerProducer
import requests

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = config_request_queue
default_output_queue = config_response_queue
default_push_queue = config_push_queue
default_subscriber = module

class Processor(ConsumerProducer):

    def __init__(self, **params):

        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        push_queue = params.get("push_queue", default_push_queue)
        subscriber = params.get("subscriber", default_subscriber)
        url = params.get("url", default_url)

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "output_queue": output_queue,
                "push_queue": output_queue,
                "subscriber": subscriber,
                "input_schema": ConfigRequest,
                "output_schema": ConfigResponse,
                "push_schema": ConfigPush,
            }
        )

        self.push_prod = self.client.create_producer(
            topic=push_queue,
            schema=JsonSchema(ConfigPush),
        )

        # FIXME: The state is held internally. This only works if there's
        # one config service.  Should be more than one, and use a
        # back-end state store.
        self.config = {}

    async def handle_get(self, v):

        if v.type in self.config:

            if v.key in self.config[v.type]:

                resp = ConfigResponse(
                    value = self.config[v.type][v.key],
                    directory = None,
                    values = None,
                    error = None,
                )
                await self.send(r, properties={"id": id})

            else:

                resp = ConfigResponse(
                    value=None,
                    directory=None,
                    values=None,
                    error=Error(
                        code="no-such-key",
                        message="No such key"
                    )
                )
                await self.send(r, properties={"id": id})

        else:

            resp = ConfigResponse(
                value=None,
                directory=None,
                values=None,
                error=Error(
                    code="no-such-type",
                    message="No such type"
                )
            )
            await self.send(r, properties={"id": id})

    async def handle_list(self, v):

        if v.type in self.config:

            resp = ConfigResponse(
                value = None,
                directory = list(self.config[v.type].keys())
                values = None,
                error = None,
            )
            await self.send(r, properties={"id": id})

        else:

            resp = ConfigResponse(
                value=None,
                directory=None,
                values=None,
                error=Error(
                    code="no-such-type",
                    message="No such type"
                )
            )
            await self.send(r, properties={"id": id})

    async def handle_getall(self, v):

        if v.type in self.config:

            resp = ConfigResponse(
                value = None,
                directory = None,
                values = self.config[v.type]
                error = None,
            )
            await self.send(r, properties={"id": id})

        else:

            resp = ConfigResponse(
                value=None,
                directory=None,
                values=None,
                error=Error(
                    code="no-such-type",
                    message="No such type"
                )
            )
            await self.send(r, properties={"id": id})

    async def handle_delete(self, v):

        if v.type in self.config:
            if v.key in self.config[v.type]:

                resp = ConfigResponse(
                    value = None,
                    directory = None,
                    values = None,
                    error = None,
                )
                await self.send(r, properties={"id": id})
                return

        resp = ConfigResponse(
            value=None,
            directory=None,
            values=None,
            error=Error(
                code="no-such-object",
                message="No such object"
            )
        )
        await self.send(r, properties={"id": id})

    async def handle_put(self, v):

        if v.type not in self.config:
            self.config[v.type] = {}

        self.config[v.type][v.key] = v.value

        resp = ConfigResponse(
            value = None,
            directory = None,
            values = None,
            error = None,
        )
        await self.send(r, properties={"id": id})

    async def handle(self, msg):

        v = msg.value()

        # Sender-produced ID
        id = msg.properties()["id"]

        print(f"Handling {id}...", flush=True)

        try:

            if v.operation == "get":

                self.handle_get(v, id)

            elif v.operation == "list":

                self.handle_list(v, id)

            elif v.operation == "getall":

                self.handle_getall(v, id)

            elif v.operation == "delete":

                self.handle_delete(v, id)

            elif v.operation == "put":

                self.handle_put(v, id)

            else:

                r = ConfigResponse(
                    value=None,
                    directory=None,
                    values=None,
                    error=Error(
                        code="bad-operation",
                        message="Bad operation"
                    )
                )
                await self.send(r, properties={"id": id})
                self.consumer.acknowledge(msg)

            self.consumer.acknowledge(msg)

        except Exception as e:
                
            r = LookupResponse(
                error=Error(
                    type = "unexpected-error",
                    message = str(e),
                ),
                text=None,
            )
            await self.send(r, properties={"id": id})
            self.consumer.acknowledge(msg)

    @staticmethod
    def add_args(parser):

        ConsumerProducer.add_args(
            parser, default_input_queue, default_subscriber,
            default_output_queue,
        )

        parser.add_argument(
            '-q', '--push-queue',
            default=default_push_queue,
            help=f'Config push queue (default: {default_push_queue})'
        )

def run():

    Processor.launch(module, __doc__)

