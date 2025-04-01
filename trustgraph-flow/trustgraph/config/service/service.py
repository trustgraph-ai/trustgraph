
"""
Config service.  Fetchs an extract from the Wikipedia page
using the API.
"""

from pulsar.schema import JsonSchema

from trustgraph.schema import ConfigRequest, ConfigResponse, ConfigPush
from trustgraph.schema import ConfigValue, Error
from trustgraph.schema import config_request_queue, config_response_queue
from trustgraph.schema import config_push_queue
from trustgraph.log_level import LogLevel
from trustgraph.base import ConsumerProducer

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = config_request_queue
default_output_queue = config_response_queue
default_push_queue = config_push_queue
default_subscriber = module

# This behaves just like a dict, should be easier to add persistent storage
# later

class ConfigurationItems(dict):
    pass

class Configuration(dict):

    def __getitem__(self, key):
        if key not in self:
            self[key] = ConfigurationItems()
        return dict.__getitem__(self, key)
        
class Processor(ConsumerProducer):

    def __init__(self, **params):

        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        push_queue = params.get("push_queue", default_push_queue)
        subscriber = params.get("subscriber", default_subscriber)

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
        self.config = Configuration()

        # Version counter
        self.version = 0

    async def start(self):
        await self.push()
        
    async def handle_get(self, v, id):

        for k in v.keys:
            if k.type not in self.config or k.key not in self.config[k.type]:
                return ConfigResponse(
                    version = None,
                    values = None,
                    directory = None,
                    config = None,
                    error = Error(
                        code = "key-error",
                        message = f"Key error"
                    )
                )

        values = [
            ConfigValue(
                type = k.type,
                key = k.key,
                value = self.config[k.type][k.key]
            )
            for k in v.keys
        ]

        return ConfigResponse(
            version = self.version,
            values = values,
            directory = None,
            config = None,
            error = None,
        )

    async def handle_list(self, v, id):

        if v.type not in self.config:

            return ConfigResponse(
                version = None,
                values = None,
                directory = None,
                config = None,
                error = Error(
                    code="key-error",
                    message="No such type",
                ),
            )

        return ConfigResponse(
            version = self.version,
            values = None,
            directory = list(self.config[v.type].keys()),
            config = None,
            error = None,
        )

    async def handle_getvalues(self, v, id):

        if v.type not in self.config:

            return ConfigResponse(
                version = None,
                values = None,
                directory = None,
                config = None,
                error = Error(
                    code = "key-error",
                    message = f"Key error"
                )
            )

        values = [
            ConfigValue(
                type = v.type,
                key = k,
                value = self.config[v.type][k],
            )
            for k in self.config[v.type]
        ]

        return ConfigResponse(
            version = self.version,
            values = values,
            directory = None,
            config = None,
            error = None,
        )

    async def handle_delete(self, v, id):

        for k in v.keys:
            if k.type not in self.config or k.key not in self.config[k.type]:
                return ConfigResponse(
                    version = None,
                    values = None,
                    directory = None,
                    config = None,
                    error = Error(
                        code = "key-error",
                        message = f"Key error"
                    )
                )

        for k in v.keys:
            del self.config[k.type][k.key]

        self.version += 1

        await self.push()

        return ConfigResponse(
            version = None,
            value = None,
            directory = None,
            values = None,
            config = None,
            error = None,
        )

    async def handle_put(self, v, id):

        for k in v.values:
            self.config[k.type][k.key] = k.value

        self.version += 1

        await self.push()

        return ConfigResponse(
            version = None,
            value = None,
            directory = None,
            values = None,
            error = None,
        )

    async def handle_config(self, v, id):

        return ConfigResponse(
            version = self.version,
            value = None,
            directory = None,
            values = None,
            config = self.config,
            error = None,
        )

    async def push(self):

        resp = ConfigPush(
            version = self.version,
            value = None,
            directory = None,
            values = None,
            config = self.config,
            error = None,
        )
        self.push_prod.send(resp)
        print("Pushed.")
        
    async def handle(self, msg):

        v = msg.value()

        # Sender-produced ID
        id = msg.properties()["id"]

        print(f"Handling {id}...", flush=True)

        try:

            if v.operation == "get":

                resp = await self.handle_get(v, id)

            elif v.operation == "list":

                resp = await self.handle_list(v, id)

            elif v.operation == "getvalues":

                resp = await self.handle_getvalues(v, id)

            elif v.operation == "delete":

                resp = await self.handle_delete(v, id)

            elif v.operation == "put":

                resp = await self.handle_put(v, id)

            elif v.operation == "config":

                resp = await self.handle_config(v, id)

            else:

                resp = ConfigResponse(
                    value=None,
                    directory=None,
                    values=None,
                    error=Error(
                        code="bad-operation",
                        message="Bad operation"
                    )
                )

            await self.send(resp, properties={"id": id})

            self.consumer.acknowledge(msg)

        except Exception as e:
                
            resp = ConfigResponse(
                error=Error(
                    type = "unexpected-error",
                    message = str(e),
                ),
                text=None,
            )
            await self.send(resp, properties={"id": id})
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

