
from .. schema import FlowRequest, FlowResponse, ConfigKey, ConfigValue
from .. schema import flow_request_queue
from .. schema import flow_response_queue

from . endpoint import ServiceEndpoint
from . requestor import ServiceRequestor

class FlowRequestor(ServiceRequestor):
    def __init__(self, pulsar_client, timeout, auth):

        super(FlowRequestor, self).__init__(
            pulsar_client=pulsar_client,
            request_queue=flow_request_queue,
            response_queue=flow_response_queue,
            request_schema=FlowRequest,
            response_schema=FlowResponse,
            timeout=timeout,
        )

    def to_request(self, body):

        return FlowRequest(
            operation = body.get("operation", None),
            class_name = body.get("class-name", None),
            class_definition = body.get("class-definition", None),
            description = body.get("description", None),
            flow_id = body.get("flow-id", None),
        )

    def from_response(self, message):

        response = { }

        if message.class_names is not None:
            response["class-names"] = message.class_names

        if message.flow_ids is not None:
            response["flow-ids"] = message.flow_ids

        if message.class_definition is not None:
            response["class-definition"] = message.class_definition

        if message.flow is not None:
            response["flow"] = message.flow

        if message.description is not None:
            response["description"] = message.description

        return response, True

