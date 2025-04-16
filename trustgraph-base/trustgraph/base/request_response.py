
import json
from pulsar.schema import JsonSchema

from .. schema import Error
from .. schema import config_request_queue, config_response_queue
from .. schema import config_push_queue
from .. log_level import LogLevel
from .. base import AsyncProcessor, Consumer, Producer

from .. base import ProcessorMetrics, ConsumerMetrics, ProducerMetrics
from . flow_processor import FlowProcessor

class RequestResponseService(FlowProcessor):

    def __init__(self, **params):

        super(RequestResponseService, self).__init__(**params)

        # These can be overriden by a derived class
        self.consumer_spec = [
            ("request", params.get("request_schema"), self.on_request)
        ]
        self.producer_spec = [
            ("response", params.get("response_schema"))
        ]

        print("Service initialised.")

    @staticmethod
    def add_args(parser, default_subscriber):

        FlowProcessor.add_args(parser)

def run():

    Processor.launch(module, __doc__)

