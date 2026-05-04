from __future__ import annotations

from argparse import ArgumentParser

import logging

from . async_processor import AsyncProcessor

logger = logging.getLogger(__name__)

WORKSPACES_NAMESPACE = "__workspaces__"
WORKSPACE_TYPE = "workspace"


class WorkspaceProcessor(AsyncProcessor):

    def __init__(self, **params):

        super(WorkspaceProcessor, self).__init__(**params)

        self.active_workspaces = set()

        self.register_workspace_handler(self._handle_workspace_changes)

    async def _discover_workspaces(self):
        client = self._create_config_client()
        try:
            await client.start()
            type_data, version = await self._fetch_type_all_workspaces(
                client, WORKSPACE_TYPE,
            )
            for ws in type_data:
                if ws == WORKSPACES_NAMESPACE:
                    for workspace_id in type_data[ws]:
                        if workspace_id not in self.active_workspaces:
                            self.active_workspaces.add(workspace_id)
                            await self.on_workspace_created(workspace_id)
        finally:
            await client.stop()

    async def _handle_workspace_changes(self, workspace_changes):
        for workspace_id in workspace_changes.created:
            if workspace_id not in self.active_workspaces:
                self.active_workspaces.add(workspace_id)
                logger.info(f"Workspace created: {workspace_id}")
                await self.on_workspace_created(workspace_id)

        for workspace_id in workspace_changes.deleted:
            if workspace_id in self.active_workspaces:
                logger.info(f"Workspace deleted: {workspace_id}")
                await self.on_workspace_deleted(workspace_id)
                self.active_workspaces.discard(workspace_id)

    async def on_workspace_created(self, workspace):
        pass

    async def on_workspace_deleted(self, workspace):
        pass

    async def start(self):
        await super(WorkspaceProcessor, self).start()
        await self._discover_workspaces()

    @staticmethod
    def add_args(parser: ArgumentParser) -> None:
        AsyncProcessor.add_args(parser)
