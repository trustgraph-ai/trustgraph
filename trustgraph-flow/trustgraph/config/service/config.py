
from trustgraph.schema import ConfigResponse
from trustgraph.schema import ConfigValue, Error

class ConfigurationItems(dict):
    pass

class Configuration(dict):

    # FIXME: The state is held internally. This only works if there's
    # one config service.  Should be more than one, and use a
    # back-end state store.

    def __init__(self):

        # Version counter
        self.version = 0

    def __getitem__(self, key):
        if key not in self:
            self[key] = ConfigurationItems()
        return dict.__getitem__(self, key)

    async def handle_get(self, v):

        for k in v.keys:
            if k.type not in self or k.key not in self[k.type]:
                return ConfigResponse(
                    version = None,
                    values = None,
                    directory = None,
                    config = None,
                    error = Error(
                        type = "key-error",
                        message = f"Key error"
                    )
                )

        values = [
            ConfigValue(
                type = k.type,
                key = k.key,
                value = self[k.type][k.key]
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
    
    async def handle_list(self, v):

        if v.type not in self:

            return ConfigResponse(
                version = None,
                values = None,
                directory = None,
                config = None,
                error = Error(
                    type = "key-error",
                    message = "No such type",
                ),
            )

        return ConfigResponse(
            version = self.version,
            values = None,
            directory = list(self[v.type].keys()),
            config = None,
            error = None,
        )

    async def handle_getvalues(self, v):

        if v.type not in self:

            return ConfigResponse(
                version = None,
                values = None,
                directory = None,
                config = None,
                error = Error(
                    type = "key-error",
                    message = f"Key error"
                )
            )

        values = [
            ConfigValue(
                type = v.type,
                key = k,
                value = self[v.type][k],
            )
            for k in self[v.type]
        ]

        return ConfigResponse(
            version = self.version,
            values = values,
            directory = None,
            config = None,
            error = None,
        )

    async def handle_delete(self, v):

        for k in v.keys:
            if k.type not in self or k.key not in self[k.type]:
                return ConfigResponse(
                    version = None,
                    values = None,
                    directory = None,
                    config = None,
                    error = Error(
                        type = "key-error",
                        message = f"Key error"
                    )
                )

        for k in v.keys:
            del self[k.type][k.key]

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

    async def handle_put(self, v):

        for k in v.values:
            self[k.type][k.key] = k.value

        self.version += 1

        await self.push()

        return ConfigResponse(
            version = None,
            value = None,
            directory = None,
            values = None,
            error = None,
        )

    async def handle_config(self, v):

        return ConfigResponse(
            version = self.version,
            value = None,
            directory = None,
            values = None,
            config = self,
            error = None,
        )

    async def handle(self, msg):

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
