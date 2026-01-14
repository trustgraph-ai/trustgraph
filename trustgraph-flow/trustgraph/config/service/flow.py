
from trustgraph.schema import FlowResponse, Error
import json
import logging

# Module logger
logger = logging.getLogger(__name__)

class FlowConfig:
    def __init__(self, config):

        self.config = config
        # Cache for parameter type definitions to avoid repeated lookups
        self.param_type_cache = {}

    async def resolve_parameters(self, flow_blueprint, user_params):
        """
        Resolve parameters by merging user-provided values with defaults.

        Args:
            flow_blueprint: The flow blueprint definition dict
            user_params: User-provided parameters dict (may be None or empty)

        Returns:
            Complete parameter dict with user values and defaults merged (all values as strings)
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
                            type_def = await self.config.get("parameter-type").get(param_type)
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

        names = list(await self.config.get("flow-blueprint").keys())

        return FlowResponse(
            error = None,
            blueprint_names = names,
        )
    
    async def handle_get_blueprint(self, msg):

        return FlowResponse(
            error = None,
            blueprint_definition = await self.config.get(
                "flow-blueprint"
            ).get(msg.blueprint_name),
        )
    
    async def handle_put_blueprint(self, msg):

        await self.config.get("flow-blueprint").put(
            msg.blueprint_name, msg.blueprint_definition
        )

        await self.config.inc_version()

        await self.config.push()

        return FlowResponse(
            error = None,
        )
    
    async def handle_delete_blueprint(self, msg):

        logger.debug(f"Flow config message: {msg}")

        await self.config.get("flow-blueprint").delete(msg.blueprint_name)

        await self.config.inc_version()

        await self.config.push()

        return FlowResponse(
            error = None,
        )
    
    async def handle_list_flows(self, msg):

        names = list(await self.config.get("flow").keys())

        return FlowResponse(
            error = None,
            flow_ids = names,
        )
    
    async def handle_get_flow(self, msg):

        flow_data = await self.config.get("flow").get(msg.flow_id)
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

        if msg.flow_id in await self.config.get("flow").keys():
            raise RuntimeError("Flow already exists")

        if msg.description is None:
            raise RuntimeError("No description")

        if msg.blueprint_name not in await self.config.get("flow-blueprint").keys():
            raise RuntimeError("Blueprint does not exist")

        cls = json.loads(
            await self.config.get("flow-blueprint").get(msg.blueprint_name)
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

        for kind in ("blueprint", "flow"):

            for k, v in cls[kind].items():

                processor, variant = k.split(":", 1)

                variant = repl_template_with_params(variant)

                v = {
                    repl_template_with_params(k2): repl_template_with_params(v2)
                    for k2, v2 in v.items()
                }

                flac = await self.config.get("active-flow").get(processor)
                if flac is not None:
                    target = json.loads(flac)
                else:
                    target = {}

                # The condition if variant not in target: means it only adds
                # the configuration if the variant doesn't already exist.
                # If "everything" already exists in the target with old
                # values, they won't update.

                if variant not in target:
                    target[variant] = v

                await self.config.get("active-flow").put(
                    processor, json.dumps(target)
                )

        def repl_interface(i):
            if isinstance(i, str):
                return repl_template_with_params(i)
            else:
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

        await self.config.get("flow").put(
            msg.flow_id,
            json.dumps({
                "description": msg.description,
                "blueprint-name": msg.blueprint_name,
                "interfaces": interfaces,
                "parameters": parameters,
            })
        )

        await self.config.inc_version()

        await self.config.push()

        return FlowResponse(
            error = None,
        )
    
    async def handle_stop_flow(self, msg):

        if msg.flow_id is None:
            raise RuntimeError("No flow ID")

        if msg.flow_id not in await self.config.get("flow").keys():
            raise RuntimeError("Flow ID invalid")

        flow = json.loads(await self.config.get("flow").get(msg.flow_id))

        if "blueprint-name" not in flow:
            raise RuntimeError("Internal error: flow has no flow blueprint")

        blueprint_name = flow["blueprint-name"]
        parameters = flow.get("parameters", {})

        cls = json.loads(await self.config.get("flow-blueprint").get(blueprint_name))

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

        for kind in ("flow",):

            for k, v in cls[kind].items():

                processor, variant = k.split(":", 1)

                variant = repl_template(variant)

                flac = await self.config.get("active-flow").get(processor)

                if flac is not None:
                    target = json.loads(flac)
                else:
                    target = {}

                if variant in target:
                    del target[variant]

                await self.config.get("active-flow").put(
                    processor, json.dumps(target)
                )

        if msg.flow_id in await self.config.get("flow").keys():
            await self.config.get("flow").delete(msg.flow_id)

        await self.config.inc_version()

        await self.config.push()

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

