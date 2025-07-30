
import logging

from trustgraph.schema import ConfigResponse
from trustgraph.schema import ConfigValue, Error

from ... tables.config import ConfigTableStore

# Module logger
logger = logging.getLogger(__name__)

class ConfigurationClass:
    
    async def keys(self):
        return await self.table_store.get_keys(self.type)
    
    async def values(self):
        vals = await self.table_store.get_values(self.type)
        return {
            v[0]: v[1]
            for v in vals
        }

    async def get(self, key):
        return await self.table_store.get_value(self.type, key)        

    async def put(self, key, value):
        return await self.table_store.put_config(self.type, key, value)

    async def delete(self, key):
        return await self.table_store.delete_key(self.type, key)

    async def has(self, key):
        val = await self.table_store.get_value(self.type, key)
        return val is not None

class Configuration:

    # FIXME: The state is held internally. This only works if there's
    # one config service.  Should be more than one, and use a
    # back-end state store.

    # FIXME: This has state now, but does it address all of the above?
    # REVIEW: Above

    # FIXME: Some version vs config race conditions

    def __init__(self, push, host, user, password, keyspace):

        # External function to respond to update
        self.push = push

        self.table_store = ConfigTableStore(
            host, user, password, keyspace
        )

    async def inc_version(self):
        await self.table_store.inc_version()

    async def get_version(self):
        return await self.table_store.get_version()

    def get(self, type):

        c = ConfigurationClass()
        c.table_store = self.table_store
        c.type = type

        return c

    async def handle_get(self, v):

        # for k in v.keys:
        #     if k.type not in self or k.key not in self[k.type]:
        #         return ConfigResponse(
        #             version = None,
        #             values = None,
        #             directory = None,
        #             config = None,
        #             error = Error(
        #                 type = "key-error",
        #                 message = f"Key error"
        #             )
        #         )

        values = [
            ConfigValue(
                type = k.type,
                key = k.key,
                value = await self.table_store.get_value(k.type, k.key)
            )
            for k in v.keys
        ]

        return ConfigResponse(
            version = await self.get_version(),
            values = values,
            directory = None,
            config = None,
            error = None,
        )
    
    async def handle_list(self, v):

        # if v.type not in self:

        #     return ConfigResponse(
        #         version = None,
        #         values = None,
        #         directory = None,
        #         config = None,
        #         error = Error(
        #             type = "key-error",
        #             message = "No such type",
        #         ),
        #     )

        return ConfigResponse(
            version = await self.get_version(),
            values = None,
            directory = await self.table_store.get_keys(v.type),
            config = None,
            error = None,
        )

    async def handle_getvalues(self, v):

        # if v.type not in self:

        #     return ConfigResponse(
        #         version = None,
        #         values = None,
        #         directory = None,
        #         config = None,
        #         error = Error(
        #             type = "key-error",
        #             message = f"Key error"
        #         )
        #     )

        vals = await self.table_store.get_values(v.type)

        values = map(
            lambda x: ConfigValue(
                type = v.type, key = x[0], value = x[1]
            ),
            vals
        )

        return ConfigResponse(
            version = await self.get_version(),
            values = list(values),
            directory = None,
            config = None,
            error = None,
        )

    async def handle_delete(self, v):

        # for k in v.keys:
        #     if k.type not in self or k.key not in self[k.type]:
        #         return ConfigResponse(
        #             version = None,
        #             values = None,
        #             directory = None,
        #             config = None,
        #             error = Error(
        #                 type = "key-error",
        #                 message = f"Key error"
        #             )
        #         )

        for k in v.keys:

            await self.table_store.delete_key(k.type, k.key)

        await self.inc_version()

        await self.push()

        return ConfigResponse(
            version = None,
            value = None,
            directory = None,
            values = None,
            config = None,
            error = None,
        )

    async def handle_put(self, v):

        for k in v.values:

            await self.table_store.put_config(k.type, k.key, k.value)

        await self.inc_version()

        await self.push()

        return ConfigResponse(
            version = None,
            value = None,
            directory = None,
            values = None,
            error = None,
        )

    async def get_config(self):

        table = await self.table_store.get_all()

        config = {}

        for row in table:
            if row[0] not in config:
                config[row[0]] = {}
            config[row[0]][row[1]] = row[2]

        return config

    async def handle_config(self, v):

        config = await self.get_config()

        return ConfigResponse(
            version = await self.get_version(),
            value = None,
            directory = None,
            values = None,
            config = config,
            error = None,
        )

    async def handle(self, msg):

        logger.debug(f"Handling config message: {msg.operation}")

        if msg.operation == "get":

            resp = await self.handle_get(msg)

        elif msg.operation == "list":

            resp = await self.handle_list(msg)

        elif msg.operation == "getvalues":

            resp = await self.handle_getvalues(msg)

        elif msg.operation == "delete":

            resp = await self.handle_delete(msg)

        elif msg.operation == "put":

            resp = await self.handle_put(msg)

        elif msg.operation == "config":

            resp = await self.handle_config(msg)

        else:

            resp = ConfigResponse(
                value=None,
                directory=None,
                values=None,
                error=Error(
                    type = "bad-operation",
                    message = "Bad operation"
                )
            )

        return resp
