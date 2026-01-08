
from dataclasses import dataclass, field

from ..core.topic import topic
from ..core.primitives import Error

############################################################################

# Flow service:
#   list_classes() -> (classname[])
#   get_class(classname) -> (class)
#   put_class(class) -> (class)
#   delete_class(classname) -> ()
#
#   list_flows() -> (flowid[])
#   get_flow(flowid) -> (flow)
#   start_flow(flowid, classname) -> ()
#   stop_flow(flowid) -> ()

# Prompt services, abstract the prompt generation
@dataclass
class FlowRequest:
    operation: str = ""  # list-classes, get-class, put-class, delete-class
                         # list-flows, get-flow, start-flow, stop-flow

    # get_class, put_class, delete_class, start_flow
    class_name: str = ""

    # put_class
    class_definition: str = ""

    # start_flow
    description: str = ""

    # get_flow, start_flow, stop_flow
    flow_id: str = ""

    # start_flow - optional parameters for flow customization
    parameters: dict[str, str] = field(default_factory=dict)

@dataclass
class FlowResponse:
    # list_classes
    class_names: list[str] = field(default_factory=list)

    # list_flows
    flow_ids: list[str] = field(default_factory=list)

    # get_class
    class_definition: str = ""

    # get_flow
    flow: str = ""

    # get_flow
    description: str = ""

    # get_flow - parameters used when flow was started
    parameters: dict[str, str] = field(default_factory=dict)

    # Everything
    error: Error | None = None

flow_request_queue = topic(
    'flow', qos='q0', namespace='request'
)
flow_response_queue = topic(
    'flow', qos='q0', namespace='response'
)

############################################################################

