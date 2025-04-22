
from trustgraph.schema import FlowResponse, Error
import json

class FlowConfig:
    def __init__(self, config):

        self.config = config

    async def handle_list_classes(self, msg):

        names = list(self.config["flow-classes"].keys())

        return FlowResponse(
            error = None,
            class_names = names,
        )
    
    async def handle_get_class(self, msg):

        return FlowResponse(
            error = None,
            class_definition = self.config["flow-classes"][msg.class_name],
        )
    
    async def handle_put_class(self, msg):

        self.config["flow-classes"][msg.class_name] = msg.class_definition

        await self.config.push()

        return FlowResponse(
            error = None,
        )
    
    async def handle_delete_class(self, msg):

        del self.config["flow-classes"][msg.class_name]

        await self.config.push()

        return FlowResponse(
            error = None,
        )
    
    async def handle_list_flows(self, msg):

        names = list(self.config["flows"].keys())

        return FlowResponse(
            error = None,
            flow_ids = names,
        )
    
    async def handle_get_flow(self, msg):

        flow = self.config["flows"][msg.flow_id]

        return FlowResponse(
            error = None,
            flow = flow,
        )
    
    async def handle_start_flow(self, msg):

        def repl_template(tmp):
            print("REPL")
            return tmp.replace(
                "{class}", msg.class_name
            ).replace(
                "{id}", msg.flow_id
            )

        cls = json.loads(self.config["flow-classes"][msg.class_name])

        plumb = {}

        for kind in ("class", "flow"):

            for k, v in cls[kind].items():

                processor, variant = k.split(":", 1)

                variant = repl_template(variant)

                print(">>", processor, variant)

                print(">>>", v)

                v = {
                    repl_template(k2): repl_template(v2)
                    for k2, v2 in v.items()
                }

                print("<<<", v)

                if processor in self.config["flows-active"]:
                    target = json.loads(self.config["flows-active"][processor])
                else:
                    target = {}

                if variant not in target:
                    target[variant] = v

                self.config["flows-active"][processor] = json.dumps(target)

        print(cls)

        self.config["flows"][msg.flow_id] = {
            "description": cls["description"],
            "class-name": msg.class_name,
        }

        await self.config.push()

        return FlowResponse(
            error = None,
        )
    
    async def handle_stop_flow(self, msg):

        flow = self.config["flows"][msg.flow_id]

        return FlowResponse(
            error = None,
        )
    
    async def handle(self, msg):

        print("Handle message ", msg.operation)

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

    
