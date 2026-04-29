"""
DefaultFlowStart initialiser — starts a named flow in a workspace
using a specified blueprint.

Separated from WorkspaceInit so deployments that want a workspace
without an auto-started flow can simply omit this initialiser.

Parameters
----------
workspace : str (default "default")
    Workspace in which to start the flow.
flow_id : str (default "default")
    Identifier for the started flow.
blueprint : str (required)
    Blueprint name (must already exist in the workspace's config,
    typically via TemplateSeed -> WorkspaceInit).
description : str (default "Default")
    Human-readable description passed to flow-svc.
parameters : dict (optional)
    Optional parameter overrides passed to start-flow.
"""

from trustgraph.schema import FlowRequest

from .. base import Initialiser


class DefaultFlowStart(Initialiser):

    def __init__(
            self,
            workspace="default",
            flow_id="default",
            blueprint=None,
            description="Default",
            parameters=None,
            **kwargs,
    ):
        super().__init__(**kwargs)
        if not blueprint:
            raise ValueError(
                "DefaultFlowStart requires 'blueprint'"
            )
        self.workspace = workspace
        self.flow_id = flow_id
        self.blueprint = blueprint
        self.description = description
        self.parameters = dict(parameters) if parameters else {}

    async def run(self, ctx, old_flag, new_flag):

        # Check whether the flow already exists.  Belt-and-braces
        # beyond the flag gate: if an operator stops and restarts the
        # bootstrapper after the flow is already running, we don't
        # want to blindly try to start it again.
        list_resp = await ctx.flow.request(
            FlowRequest(
                operation="list-flows",
                workspace=self.workspace,
            ),
            timeout=10,
        )
        if list_resp.error:
            raise RuntimeError(
                f"list-flows failed: "
                f"{list_resp.error.type}: {list_resp.error.message}"
            )

        if self.flow_id in (list_resp.flow_ids or []):
            ctx.logger.info(
                f"Flow {self.flow_id!r} already running in workspace "
                f"{self.workspace!r}; nothing to do"
            )
            return

        ctx.logger.info(
            f"Starting flow {self.flow_id!r} "
            f"(blueprint={self.blueprint!r}) "
            f"in workspace {self.workspace!r}"
        )

        resp = await ctx.flow.request(
            FlowRequest(
                operation="start-flow",
                workspace=self.workspace,
                flow_id=self.flow_id,
                blueprint_name=self.blueprint,
                description=self.description,
                parameters=self.parameters,
            ),
            timeout=30,
        )
        if resp.error:
            raise RuntimeError(
                f"start-flow failed: "
                f"{resp.error.type}: {resp.error.message}"
            )

        ctx.logger.info(
            f"Flow {self.flow_id!r} started"
        )
