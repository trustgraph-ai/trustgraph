
import logging

from trustgraph.schema import ConfigResponse
from trustgraph.schema import ConfigValue, WorkspaceChanges, Error

from ... tables.config import ConfigTableStore

# Module logger
logger = logging.getLogger(__name__)

WORKSPACES_NAMESPACE = "__workspaces__"
WORKSPACE_TYPE = "workspace"
TEMPLATE_WORKSPACE = "__template__"

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

    async def handle_get(self, v, workspace):

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

    async def handle_list(self, v, workspace):

        return ConfigResponse(
            version = await self.get_version(),
            directory = await self.table_store.get_keys(
                workspace, v.type
            ),
        )

    async def handle_getvalues(self, v, workspace):

        vals = await self.table_store.get_values(workspace, v.type)

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

    async def handle_delete(self, v, workspace):

        types = list(set(k.type for k in v.keys))

        for k in v.keys:
            await self.table_store.delete_key(workspace, k.type, k.key)

        await self.inc_version()

        workspace_changes = None
        if workspace == WORKSPACES_NAMESPACE and WORKSPACE_TYPE in types:
            deleted = [k.key for k in v.keys if k.type == WORKSPACE_TYPE]
            if deleted:
                workspace_changes = WorkspaceChanges(deleted=deleted)

        await self.push(
            changes={t: [workspace] for t in types},
            workspace_changes=workspace_changes,
        )

        return ConfigResponse(
        )

    async def handle_put(self, v, workspace):

        types = list(set(k.type for k in v.values))

        for k in v.values:
            await self.table_store.put_config(
                workspace, k.type, k.key, k.value
            )

        await self.inc_version()

        workspace_changes = None
        if workspace == WORKSPACES_NAMESPACE and WORKSPACE_TYPE in types:
            created = [k.key for k in v.values if k.type == WORKSPACE_TYPE]
            if created:
                workspace_changes = WorkspaceChanges(created=created)

        await self.push(
            changes={t: [workspace] for t in types},
            workspace_changes=workspace_changes,
        )

        return ConfigResponse(
        )

    async def provision_from_template(self, workspace):
        """Copy all config from __template__ into a new workspace,
        skipping keys that already exist (upsert-missing)."""

        template = await self.get_config(TEMPLATE_WORKSPACE)

        if not template:
            logger.info(
                f"No template config to provision for {workspace}"
            )
            return 0

        existing_types = await self.get_config(workspace)

        written = 0
        for type_name, entries in template.items():
            existing_keys = set(existing_types.get(type_name, {}).keys())
            for key, value in entries.items():
                if key not in existing_keys:
                    await self.table_store.put_config(
                        workspace, type_name, key, value
                    )
                    written += 1

        if written > 0:
            await self.inc_version()

        return written

    async def get_config(self, workspace):

        table = await self.table_store.get_all_for_workspace(workspace)

        config = {}

        for row in table:
            if row[0] not in config:
                config[row[0]] = {}
            config[row[0]][row[1]] = row[2]

        return config

    async def handle_config(self, v, workspace):

        config = await self.get_config(workspace)

        return ConfigResponse(
            version = await self.get_version(),
            config = config,
        )

    async def handle_workspace(self, msg, workspace):
        """Handle workspace-scoped config operations.
        Workspace is provided by queue infrastructure."""

        logger.debug(
            f"Handling workspace config message: {msg.operation} "
            f"workspace={workspace}"
        )

        if msg.operation == "get":
            resp = await self.handle_get(msg, workspace)

        elif msg.operation == "list":
            resp = await self.handle_list(msg, workspace)

        elif msg.operation == "getvalues":
            resp = await self.handle_getvalues(msg, workspace)

        elif msg.operation == "delete":
            resp = await self.handle_delete(msg, workspace)

        elif msg.operation == "put":
            resp = await self.handle_put(msg, workspace)

        elif msg.operation == "config":
            resp = await self.handle_config(msg, workspace)

        else:
            resp = ConfigResponse(
                error=Error(
                    type = "bad-operation",
                    message = "Bad operation"
                )
            )

        return resp

    async def handle_system(self, msg):
        """Handle system-level config operations.
        Workspace, when needed, comes from message body."""

        logger.debug(
            f"Handling system config message: {msg.operation} "
            f"workspace={msg.workspace}"
        )

        if msg.operation == "getvalues-all-ws":
            resp = await self.handle_getvalues_all_ws(msg)

        elif msg.operation in ("get", "list", "getvalues", "delete",
                               "put", "config"):

            if not msg.workspace:
                return ConfigResponse(
                    error=Error(
                        type = "bad-request",
                        message = "Workspace is required"
                    )
                )

            handler = {
                "get": self.handle_get,
                "list": self.handle_list,
                "getvalues": self.handle_getvalues,
                "delete": self.handle_delete,
                "put": self.handle_put,
                "config": self.handle_config,
            }[msg.operation]

            resp = await handler(msg, msg.workspace)

        else:
            resp = ConfigResponse(
                error=Error(
                    type = "bad-operation",
                    message = "Bad operation"
                )
            )

        return resp
