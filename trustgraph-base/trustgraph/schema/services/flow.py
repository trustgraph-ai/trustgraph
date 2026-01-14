
from dataclasses import dataclass, field

from ..core.topic import topic
from ..core.primitives import Error

############################################################################

# Flow service:
#   list_blueprints() -> (blueprintname[])
#   get_blueprint(blueprintname) -> (blueprint)
#   put_blueprint(blueprint) -> (blueprint)
#   delete_blueprint(blueprintname) -> ()
#
#   list_flows() -> (flowid[])
#   get_flow(flowid) -> (flow)
#   start_flow(flowid, blueprintname) -> ()
#   stop_flow(flowid) -> ()

# Prompt services, abstract the prompt generation
@dataclass
class FlowRequest:
    operation: str = ""  # list-blueprints, get-blueprint, put-blueprint, delete-blueprint
                         # list-flows, get-flow, start-flow, stop-flow

    # get_blueprint, put_blueprint, delete_blueprint, start_flow
    blueprint_name: str = ""

    # put_blueprint
    blueprint_definition: str = ""

    # start_flow
    description: str = ""

    # get_flow, start_flow, stop_flow
    flow_id: str = ""

    # start_flow - optional parameters for flow customization
    parameters: dict[str, str] = field(default_factory=dict)

@dataclass
class FlowResponse:
    # list_blueprints
    blueprint_names: list[str] = field(default_factory=list)

    # list_flows
    flow_ids: list[str] = field(default_factory=list)

    # get_blueprint
    blueprint_definition: str = ""

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

