
import logging

from trustgraph.schema import ConfigResponse
from trustgraph.schema import ConfigValue, Error

from ... tables.config import ConfigTableStore

# Module logger
logger = logging.getLogger(__name__)

class Configuration:

    def __init__(self, push, host, username, password, keyspace):

        # External function to respond to update
        self.push = push

        self.table_store = ConfigTableStore(
            host, username, password, keyspace
        )

    async def inc_version(self):
        await self.table_store.inc_version()

    async def get_version(self):
        return await self.table_store.get_version()

    async def handle_get(self, v):

        workspace = v.workspace

        values = [
            ConfigValue(
                type = k.type,
                key = k.key,
                value = await self.table_store.get_value(
                    workspace, k.type, k.key
                )
            )
            for k in v.keys
        ]

        return ConfigResponse(
            version = await self.get_version(),
            values = values,
        )

    async def handle_list(self, v):

        return ConfigResponse(
            version = await self.get_version(),
            directory = await self.table_store.get_keys(
                v.workspace, v.type
            ),
        )

    async def handle_getvalues(self, v):

        vals = await self.table_store.get_values(v.workspace, v.type)

        values = map(
            lambda x: ConfigValue(
                type = v.type, key = x[0], value = x[1]
            ),
            vals
        )

        return ConfigResponse(
            version = await self.get_version(),
            values = list(values),
        )

    async def handle_getvalues_all_ws(self, v):
        """Fetch all values of a given type across all workspaces.
        Used by shared processors to load type-scoped config at
        startup without enumerating workspaces separately."""

        vals = await self.table_store.get_values_all_ws(v.type)

        values = [
            ConfigValue(
                workspace = row[0],
                type = v.type,
                key = row[1],
                value = row[2],
            )
            for row in vals
        ]

        return ConfigResponse(
            version = await self.get_version(),
            values = values,
        )

    async def handle_delete(self, v):

        workspace = v.workspace
        types = list(set(k.type for k in v.keys))

        for k in v.keys:
            await self.table_store.delete_key(workspace, k.type, k.key)

        await self.inc_version()

        await self.push(changes={t: [workspace] for t in types})

        return ConfigResponse(
        )

    async def handle_put(self, v):

        workspace = v.workspace
        types = list(set(k.type for k in v.values))

        for k in v.values:
            await self.table_store.put_config(
                workspace, k.type, k.key, k.value
            )

        await self.inc_version()

        await self.push(changes={t: [workspace] for t in types})

        return ConfigResponse(
        )

    async def get_config(self, workspace):

        table = await self.table_store.get_all_for_workspace(workspace)

        config = {}

        for row in table:
            if row[0] not in config:
                config[row[0]] = {}
            config[row[0]][row[1]] = row[2]

        return config

    async def handle_config(self, v):

        config = await self.get_config(v.workspace)

        return ConfigResponse(
            version = await self.get_version(),
            config = config,
        )

    async def handle(self, msg):

        logger.debug(
            f"Handling config message: {msg.operation} "
            f"workspace={msg.workspace}"
        )

        # getvalues-all-ws spans all workspaces, so no workspace
        # required; everything else is workspace-scoped.
        if msg.operation != "getvalues-all-ws" and not msg.workspace:
            return ConfigResponse(
                error=Error(
                    type = "bad-request",
                    message = "Workspace is required"
                )
            )

        if msg.operation == "get":

            resp = await self.handle_get(msg)

        elif msg.operation == "list":

            resp = await self.handle_list(msg)

        elif msg.operation == "getvalues":

            resp = await self.handle_getvalues(msg)

        elif msg.operation == "getvalues-all-ws":

            resp = await self.handle_getvalues_all_ws(msg)

        elif msg.operation == "delete":

            resp = await self.handle_delete(msg)

        elif msg.operation == "put":

            resp = await self.handle_put(msg)

        elif msg.operation == "config":

            resp = await self.handle_config(msg)

        else:

            resp = ConfigResponse(
                error=Error(
                    type = "bad-operation",
                    message = "Bad operation"
                )
            )

        return resp
