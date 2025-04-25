
from pulsar.schema import Record, Bytes, String, Boolean, Array, Map, Integer

from . topic import topic
from . types import Error

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

    operation = String() # list_classes, get_class, put_class, delete_class
                         # list_flows, get_flow, start_flow, stop_flow

    # get_class, put_class, delete_class, start_flow
    class_name = String()

    # put_class
    class = String()

    # start_flow
    description = String()

    # get_flow, start_flow, stop_flow
    flow_id = String()

class FlowResponse(Record):

    # list_classes
    class_names = Array(String())

    # list_flows
    flow_ids = Array(String())

    # get_class
    class = String()

    # get_flow
    flow = String()

    # get_flow
    description = String()

    # Everything
    error = Error()

flow_request_queue = topic(
    'flow', kind='non-persistent', namespace='request'
)
flow_response_queue = topic(
    'flow', kind='non-persistent', namespace='response'
)

############################################################################

