
from trustgraph.schema import FlowResponse, Error
import json
import logging

# Module logger
logger = logging.getLogger(__name__)

class FlowConfig:
    def __init__(self, config):

        self.config = config

    async def handle_list_classes(self, msg):

        names = list(await self.config.get("flow-classes").keys())

        return FlowResponse(
            error = None,
            class_names = names,
        )
    
    async def handle_get_class(self, msg):

        return FlowResponse(
            error = None,
            class_definition = await self.config.get(
                "flow-classes"
            ).get(msg.class_name),
        )
    
    async def handle_put_class(self, msg):

        await self.config.get("flow-classes").put(
            msg.class_name, msg.class_definition
        )

        await self.config.inc_version()

        await self.config.push()

        return FlowResponse(
            error = None,
        )
    
    async def handle_delete_class(self, msg):

        logger.debug(f"Flow config message: {msg}")

        await self.config.get("flow-classes").delete(msg.class_name)

        await self.config.inc_version()

        await self.config.push()

        return FlowResponse(
            error = None,
        )
    
    async def handle_list_flows(self, msg):

        names = list(await self.config.get("flows").keys())

        return FlowResponse(
            error = None,
            flow_ids = names,
        )
    
    async def handle_get_flow(self, msg):

        flow = await self.config.get("flows").get(msg.flow_id)

        return FlowResponse(
            error = None,
            flow = flow,
        )
    
    async def handle_start_flow(self, msg):

        if msg.class_name is None:
            raise RuntimeError("No class name")

        if msg.flow_id is None:
            raise RuntimeError("No flow ID")

        if msg.flow_id in await self.config.get("flows").values():
            raise RuntimeError("Flow already exists")

        if msg.description is None:
            raise RuntimeError("No description")

        if msg.class_name not in await self.config.get("flow-classes").values():
            raise RuntimeError("Class does not exist")

        def repl_template(tmp):
            return tmp.replace(
                "{class}", msg.class_name
            ).replace(
                "{id}", msg.flow_id
            )

        cls = json.loads(
            await self.config.get("flow-classes").get(msg.class_name)
        )

        for kind in ("class", "flow"):

            for k, v in cls[kind].items():

                processor, variant = k.split(":", 1)

                variant = repl_template(variant)

                v = {
                    repl_template(k2): repl_template(v2)
                    for k2, v2 in v.items()
                }

                flac = await self.config.get("flows-active").values()
                if processor in flac:
                    target = json.loads(flac[processor])
                else:
                    target = {}

                if variant not in target:
                    target[variant] = v

                await self.config.get("flows-active").put(
                    processor, json.dumps(target)
                )

        def repl_interface(i):
            if isinstance(i, str):
                return repl_template(i)
            else:
                return {
                    k: repl_template(v)
                    for k, v in i.items()
                }

        if "interfaces" in cls:
            interfaces = {
                k: repl_interface(v)
                for k, v in cls["interfaces"].items()
            }
        else:
            interfaces = {}

        await self.config.get("flows").put(
            msg.flow_id,
            json.dumps({
                "description": msg.description,
                "class-name": msg.class_name,
                "interfaces": interfaces,
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

        if msg.flow_id not in await self.config.get("flows").keys():
            raise RuntimeError("Flow ID invalid")

        flow = json.loads(await self.config.get("flows").get(msg.flow_id))

        if "class-name" not in flow:
            raise RuntimeError("Internal error: flow has no flow class")

        class_name = flow["class-name"]

        cls = json.loads(await self.config.get("flow-classes").get(class_name))

        def repl_template(tmp):
            return tmp.replace(
                "{class}", class_name
            ).replace(
                "{id}", msg.flow_id
            )

        for kind in ("flow",):

            for k, v in cls[kind].items():

                processor, variant = k.split(":", 1)

                variant = repl_template(variant)

                flac = await self.config.get("flows-active").values()

                if processor in flac:
                    target = json.loads(flac[processor])
                else:
                    target = {}

                if variant in target:
                    del target[variant]

                await self.config.get("flows-active").put(
                    processor, json.dumps(target)
                )

        if msg.flow_id in await self.config.get("flows").values():
            await self.config.get("flows").delete(msg.flow_id)

        await self.config.inc_version()

        await self.config.push()

        return FlowResponse(
            error = None,
        )
    
    async def handle(self, msg):

        logger.debug(f"Handling flow message: {msg.operation}")

        if msg.operation == "list-classes":
            resp = await self.handle_list_classes(msg)
        elif msg.operation == "get-class":
            resp = await self.handle_get_class(msg)
        elif msg.operation == "put-class":
            resp = await self.handle_put_class(msg)
        elif msg.operation == "delete-class":
            resp = await self.handle_delete_class(msg)
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
                value=None,
                directory=None,
                values=None,
                error=Error(
                    type = "bad-operation",
                    message = "Bad operation"
                )
            )

        return resp

