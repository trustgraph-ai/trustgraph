
from pulsar.schema import Record, Bytes, String, Boolean, Array, Map, Integer

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
class FlowRequest(Record):

    operation = String() # list-classes, get-class, put-class, delete-class
                         # list-flows, get-flow, start-flow, stop-flow

    # get_class, put_class, delete_class, start_flow
    class_name = String()

    # put_class
    class_definition = String()

    # start_flow
    description = String()

    # get_flow, start_flow, stop_flow
    flow_id = String()

    # start_flow - optional parameters for flow customization
    parameters = Map(String())

class FlowResponse(Record):

    # list_classes
    class_names = Array(String())

    # list_flows
    flow_ids = Array(String())

    # get_class
    class_definition = String()

    # get_flow
    flow = String()

    # get_flow
    description = String()

    # get_flow - parameters used when flow was started
    parameters = Map(String())

    # Everything
    error = Error()

flow_request_queue = topic(
    'flow', kind='non-persistent', namespace='request'
)
flow_response_queue = topic(
    'flow', kind='non-persistent', namespace='response'
)

############################################################################

