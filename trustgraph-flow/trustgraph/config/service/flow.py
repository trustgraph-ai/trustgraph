
from trustgraph.schema import FlowResponse, Error

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

        return FlowResponse(
            error = None,
        )
    
    async def handle_delete_class(self, msg):

        del self.config["flow-classes"][msg.class_name]

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

        cls = self.config["flow-classes"][msg.class_name]

        print(cls)

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

    
