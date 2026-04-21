
from trustgraph.schema import FlowResponse, Error
import asyncio
import json
import logging

# Module logger
logger = logging.getLogger(__name__)

# Topic deletion retry settings
DELETE_RETRIES = 5
DELETE_RETRY_DELAY = 2  # seconds


class FlowConfig:
    def __init__(self, config, pubsub):

        self.config = config
        self.pubsub = pubsub
        # Cache for parameter type definitions to avoid repeated lookups
        self.param_type_cache = {}

    async def resolve_parameters(self, flow_blueprint, user_params):
        """
        Resolve parameters by merging user-provided values with defaults.

        Args:
            flow_blueprint: The flow blueprint definition dict
            user_params: User-provided parameters dict (may be None or empty)

        Returns:
            Complete parameter dict with user values and defaults merged
            (all values as strings)
        """

        # If the flow blueprint has no parameters section, return user params as-is (stringified)

        if "parameters" not in flow_blueprint:
            if not user_params:
                return {}
            # Ensure all values are strings
            return {k: str(v) for k, v in user_params.items()}

        resolved = {}
        flow_params = flow_blueprint["parameters"]
        user_params = user_params if user_params else {}

        # First pass: resolve parameters with explicit values or defaults
        for param_name, param_meta in flow_params.items():
            # Check if user provided a value
            if param_name in user_params:
                # Store as string
                resolved[param_name] = str(user_params[param_name])
            else:
                # Look up the parameter type definition
                param_type = param_meta.get("type")
                if param_type:
                    # Check cache first
                    if param_type not in self.param_type_cache:
                        try:
                            # Fetch parameter type definition from config store
                            type_def = await self.config.get(
                                "parameter-type", param_type
                            )
                            if type_def:
                                self.param_type_cache[param_type] = json.loads(type_def)
                            else:
                                logger.warning(f"Parameter type '{param_type}' not found in config")
                                self.param_type_cache[param_type] = {}
                        except Exception as e:
                            logger.error(f"Error fetching parameter type '{param_type}': {e}")
                            self.param_type_cache[param_type] = {}

                    # Apply default from type definition (as string)
                    type_def = self.param_type_cache[param_type]
                    if "default" in type_def:
                        default_value = type_def["default"]
                        # Convert to string based on type
                        if isinstance(default_value, bool):
                            resolved[param_name] = "true" if default_value else "false"
                        else:
                            resolved[param_name] = str(default_value)
                    elif type_def.get("required", False):
                        # Required parameter with no default and no user value
                        raise RuntimeError(f"Required parameter '{param_name}' not provided and has no default")

        # Second pass: handle controlled-by relationships
        for param_name, param_meta in flow_params.items():
            if param_name not in resolved and "controlled-by" in param_meta:
                controller = param_meta["controlled-by"]
                if controller in resolved:
                    # Inherit value from controlling parameter (already a string)
                    resolved[param_name] = resolved[controller]
                else:
                    # Controller has no value, try to get default from type definition
                    param_type = param_meta.get("type")
                    if param_type and param_type in self.param_type_cache:
                        type_def = self.param_type_cache[param_type]
                        if "default" in type_def:
                            default_value = type_def["default"]
                            # Convert to string based on type
                            if isinstance(default_value, bool):
                                resolved[param_name] = "true" if default_value else "false"
                            else:
                                resolved[param_name] = str(default_value)

        # Include any extra parameters from user that weren't in flow blueprint definition
        # This allows for forward compatibility (ensure they're strings)
        for key, value in user_params.items():
            if key not in resolved:
                resolved[key] = str(value)

        return resolved

    async def handle_list_blueprints(self, msg):

        names = list(await self.config.keys("flow-blueprint"))

        return FlowResponse(
            error = None,
            blueprint_names = names,
        )

    async def handle_get_blueprint(self, msg):

        return FlowResponse(
            error = None,
            blueprint_definition = await self.config.get(
                "flow-blueprint", msg.blueprint_name
            ),
        )

    async def handle_put_blueprint(self, msg):

        await self.config.put(
            "flow-blueprint",
            msg.blueprint_name, msg.blueprint_definition
        )

        return FlowResponse(
            error = None,
        )

    async def handle_delete_blueprint(self, msg):

        logger.debug(f"Flow config message: {msg}")

        await self.config.delete("flow-blueprint", msg.blueprint_name)

        return FlowResponse(
            error = None,
        )

    async def handle_list_flows(self, msg):

        names = list(await self.config.keys("flow"))

        return FlowResponse(
            error = None,
            flow_ids = names,
        )

    async def handle_get_flow(self, msg):

        flow_data = await self.config.get("flow", msg.flow_id)
        flow = json.loads(flow_data)

        return FlowResponse(
            error = None,
            flow = flow_data,
            description = flow.get("description", ""),
            parameters = flow.get("parameters", {}),
        )

    async def handle_start_flow(self, msg):

        if msg.blueprint_name is None:
            raise RuntimeError("No blueprint name")

        if msg.flow_id is None:
            raise RuntimeError("No flow ID")

        if msg.flow_id in await self.config.keys("flow"):
            raise RuntimeError("Flow already exists")

        if msg.description is None:
            raise RuntimeError("No description")

        if msg.blueprint_name not in await self.config.keys("flow-blueprint"):
            raise RuntimeError("Blueprint does not exist")

        cls = json.loads(
            await self.config.get("flow-blueprint", msg.blueprint_name)
        )

        # Resolve parameters by merging user-provided values with defaults
        user_params = msg.parameters if msg.parameters else {}
        parameters = await self.resolve_parameters(cls, user_params)

        # Log the resolved parameters for debugging
        logger.debug(f"User provided parameters: {user_params}")
        logger.debug(f"Resolved parameters (with defaults): {parameters}")

        # Apply parameter substitution to template replacement function
        def repl_template_with_params(tmp):

            result = tmp.replace(
                "{blueprint}", msg.blueprint_name
            ).replace(
                "{id}", msg.flow_id
            )
            # Apply parameter substitutions
            for param_name, param_value in parameters.items():
                result = result.replace(f"{{{param_name}}}", str(param_value))

            return result

        # Pre-create topic exchanges so the data path is wired
        # before processors receive their config and start connecting.
        topics = self._collect_flow_topics(cls, repl_template_with_params)
        for topic in topics:
            await self.pubsub.create_topic(topic)

        # Build all processor config updates, then write in a single batch.
        updates = []

        for kind in ("blueprint", "flow"):

            for k, v in cls[kind].items():

                processor, variant = k.split(":", 1)

                variant = repl_template_with_params(variant)

                topics = {
                    repl_template_with_params(k2): repl_template_with_params(v2)
                    for k2, v2 in v.get("topics", {}).items()
                }

                params = {
                    repl_template_with_params(k2): repl_template_with_params(v2)
                    for k2, v2 in v.get("parameters", {}).items()
                }

                entry = {
                    "topics": topics,
                    "parameters": params,
                }

                updates.append((
                    f"processor:{processor}",
                    variant,
                    json.dumps(entry),
                ))

        await self.config.put_many(updates)

        def repl_interface(i):
            return {
                k: repl_template_with_params(v)
                for k, v in i.items()
            }

        if "interfaces" in cls:
            interfaces = {
                k: repl_interface(v)
                for k, v in cls["interfaces"].items()
            }
        else:
            interfaces = {}

        await self.config.put(
            "flow", msg.flow_id,
            json.dumps({
                "description": msg.description,
                "blueprint-name": msg.blueprint_name,
                "interfaces": interfaces,
                "parameters": parameters,
            })
        )

        return FlowResponse(
            error = None,
        )

    async def ensure_existing_flow_topics(self):
        """Ensure topics exist for all already-running flows.

        Called on startup to handle flows that were started before this
        version of the flow service was deployed, or before a restart.
        """
        flow_ids = await self.config.keys("flow")

        for flow_id in flow_ids:
            try:
                flow_data = await self.config.get("flow", flow_id)
                if flow_data is None:
                    continue

                flow = json.loads(flow_data)

                blueprint_name = flow.get("blueprint-name")
                if blueprint_name is None:
                    continue

                # Skip flows that are mid-shutdown
                if flow.get("status") == "stopping":
                    continue

                parameters = flow.get("parameters", {})

                blueprint_data = await self.config.get(
                    "flow-blueprint", blueprint_name
                )
                if blueprint_data is None:
                    logger.warning(
                        f"Blueprint '{blueprint_name}' not found for "
                        f"flow '{flow_id}', skipping topic creation"
                    )
                    continue

                cls = json.loads(blueprint_data)

                def repl_template(tmp):
                    result = tmp.replace(
                        "{blueprint}", blueprint_name
                    ).replace(
                        "{id}", flow_id
                    )
                    for param_name, param_value in parameters.items():
                        result = result.replace(
                            f"{{{param_name}}}", str(param_value)
                        )
                    return result

                topics = self._collect_flow_topics(cls, repl_template)
                for topic in topics:
                    await self.pubsub.ensure_topic(topic)

                logger.info(
                    f"Ensured topics for existing flow '{flow_id}'"
                )

            except Exception as e:
                logger.error(
                    f"Failed to ensure topics for flow '{flow_id}': {e}"
                )

    def _collect_flow_topics(self, cls, repl_template):
        """Collect unique topic identifiers from the blueprint.

        Iterates the blueprint's "flow" section and returns a
        deduplicated set of resolved topic strings.  The flow service
        manages topic lifecycle (create/delete exchanges), not
        individual consumer queues.
        """
        topics = set()

        for k, v in cls["flow"].items():
            for spec_name, topic_template in v.get("topics", {}).items():
                topic = repl_template(topic_template)
                topics.add(topic)

        return topics

    @staticmethod
    def _topic_is_flow_owned(raw_template):
        """Is a topic template owned by the flow system?

        A topic is flow-owned if its template contains at least one
        variable substitution (``{id}``, ``{blueprint}``,
        ``{workspace}``, ``{param}``, etc.).  Pure literal templates
        name topics that are created and owned by something else (a
        global service, e.g. ``request:tg:librarian``) and must never
        be touched by the flow service.
        """
        return '{' in raw_template

    def _collect_owned_topics(self, cls, repl_template):
        """Resolved set of flow-owned topics for a single flow.

        Only includes topics whose raw template was parameterised
        (contains ``{...}``).  Literal templates are skipped — they
        refer to global topics the flow service does not own.
        """
        topics = set()

        for k, v in cls["flow"].items():
            for spec_name, topic_template in v.get("topics", {}).items():
                if not self._topic_is_flow_owned(topic_template):
                    continue
                topics.add(repl_template(topic_template))

        return topics

    async def _live_owned_topic_closure(self, exclude_flow_id=None):
        """Union of flow-owned topics referenced by all live flows.

        Walks every flow record currently registered in the config
        service (except ``exclude_flow_id``, typically the flow being
        torn down), resolves its blueprint + parameter templates, and
        collects the set of flow-owned topics those templates produce.

        Used to drive closure-based topic cleanup on flow stop: a
        topic may only be deleted if no remaining live flow would
        still template to it.  This handles all three scoping cases
        transparently — ``{id}`` topics have no other references once
        their flow is excluded; ``{blueprint}`` topics stay alive
        while another flow of the same blueprint exists; ``{workspace}``
        (when introduced) stays alive while any flow in the workspace
        exists.
        """

        live = set()

        flow_ids = await self.config.keys("flow")

        for fid in flow_ids:

            if fid == exclude_flow_id:
                continue

            try:
                frec_raw = await self.config.get("flow", fid)
                if frec_raw is None:
                    continue
                frec = json.loads(frec_raw)
            except Exception as e:
                logger.warning(
                    f"Closure sweep: skipping flow {fid}: {e}"
                )
                continue

            # Flows mid-shutdown don't keep their topics alive.
            if frec.get("status") == "stopping":
                continue

            bp_name = frec.get("blueprint-name")
            if bp_name is None:
                continue

            try:
                bp_raw = await self.config.get("flow-blueprint", bp_name)
                if bp_raw is None:
                    continue
                bp = json.loads(bp_raw)
            except Exception as e:
                logger.warning(
                    f"Closure sweep: skipping flow {fid} "
                    f"(blueprint {bp_name}): {e}"
                )
                continue

            parameters = frec.get("parameters", {})

            def repl(tmp, bp_name=bp_name, fid=fid, parameters=parameters):
                result = tmp.replace(
                    "{blueprint}", bp_name
                ).replace(
                    "{id}", fid
                )
                for pname, pvalue in parameters.items():
                    result = result.replace(
                        f"{{{pname}}}", str(pvalue)
                    )
                return result

            live.update(self._collect_owned_topics(bp, repl))

        return live

    async def _delete_topics(self, topics):
        """Delete topics with retries. Best-effort — logs failures but
        does not raise."""
        for attempt in range(DELETE_RETRIES):
            remaining = []

            for topic in topics:
                try:
                    await self.pubsub.delete_topic(topic)
                except Exception as e:
                    logger.warning(
                        f"Topic delete failed (attempt {attempt + 1}/"
                        f"{DELETE_RETRIES}): {topic}: {e}"
                    )
                    remaining.append(topic)

            if not remaining:
                return

            topics = remaining

            if attempt < DELETE_RETRIES - 1:
                await asyncio.sleep(DELETE_RETRY_DELAY)

        for topic in topics:
            logger.error(
                f"Failed to delete topic after {DELETE_RETRIES} "
                f"attempts: {topic}"
            )

    async def handle_stop_flow(self, msg):

        if msg.flow_id is None:
            raise RuntimeError("No flow ID")

        if msg.flow_id not in await self.config.keys("flow"):
            raise RuntimeError("Flow ID invalid")

        flow = json.loads(await self.config.get("flow", msg.flow_id))

        if "blueprint-name" not in flow:
            raise RuntimeError("Internal error: flow has no flow blueprint")

        blueprint_name = flow["blueprint-name"]
        parameters = flow.get("parameters", {})

        cls = json.loads(
            await self.config.get("flow-blueprint", blueprint_name)
        )

        def repl_template(tmp):
            result = tmp.replace(
                "{blueprint}", blueprint_name
            ).replace(
                "{id}", msg.flow_id
            )
            # Apply parameter substitutions
            for param_name, param_value in parameters.items():
                result = result.replace(f"{{{param_name}}}", str(param_value))
            return result

        # Collect this flow's owned topics before any config changes.
        # Global (literal-template) topics are never touched — they are
        # managed by whichever service owns them, not by flow-svc.
        this_flow_owned = self._collect_owned_topics(cls, repl_template)

        # Phase 1: Set status to "stopping" and remove processor config.
        # The config push tells processors to shut down their consumers.
        flow["status"] = "stopping"
        await self.config.put(
            "flow", msg.flow_id, json.dumps(flow)
        )

        # Delete all processor config entries for this flow.
        deletes = []

        for k, v in cls["flow"].items():

            processor, variant = k.split(":", 1)
            variant = repl_template(variant)

            deletes.append((f"processor:{processor}", variant))

        await self.config.delete_many(deletes)

        # Phase 2: Closure-based sweep. Only delete topics that no
        # other live flow still references via its blueprint templates.
        # This preserves {blueprint}-scoped topics while another flow
        # of the same blueprint is still running, and {workspace}-scoped
        # topics while any flow in that workspace remains.
        live_owned = await self._live_owned_topic_closure(
            exclude_flow_id=msg.flow_id,
        )

        to_delete = this_flow_owned - live_owned

        if to_delete:
            await self._delete_topics(to_delete)

        kept = this_flow_owned - to_delete
        if kept:
            logger.info(
                f"Flow {msg.flow_id}: keeping {len(kept)} topics "
                f"still referenced by other live flows"
            )

        # Phase 3: Remove the flow record.
        if msg.flow_id in await self.config.keys("flow"):
            await self.config.delete("flow", msg.flow_id)

        return FlowResponse(
            error = None,
        )

    async def handle(self, msg):

        logger.debug(f"Handling flow message: {msg.operation}")

        if msg.operation == "list-blueprints":
            resp = await self.handle_list_blueprints(msg)
        elif msg.operation == "get-blueprint":
            resp = await self.handle_get_blueprint(msg)
        elif msg.operation == "put-blueprint":
            resp = await self.handle_put_blueprint(msg)
        elif msg.operation == "delete-blueprint":
            resp = await self.handle_delete_blueprint(msg)
        elif msg.operation == "list-flows":
            resp = await self.handle_list_flows(msg)
        elif msg.operation == "get-flow":
            resp = await self.handle_get_flow(msg)
        elif msg.operation == "start-flow":
            resp = await self.handle_start_flow(msg)
        elif msg.operation == "stop-flow":
            resp = await self.handle_stop_flow(msg)
        else:

            resp = FlowResponse(
                error=Error(
                    type = "bad-operation",
                    message = "Bad operation"
                )
            )

        return resp
