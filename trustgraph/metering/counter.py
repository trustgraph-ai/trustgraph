"""
Simple token counter for each LLM response.
"""

from prometheus_client import Histogram, Info
from . pricelist import price_list

from .. schema import TextCompletionResponse, Error
from .. schema import text_completion_response_queue
from .. log_level import LogLevel
from .. base import Consumer

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = text_completion_response_queue
default_subscriber = module


class Processor(Consumer):

    def __init__(self, **params):

        input_queue = params.get("input_queue", default_input_queue)
        subscriber = params.get("subscriber", default_subscriber)

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "subscriber": subscriber,
                "input_schema": TextCompletionResponse,
            }
        )

    def get_prices(self, prices, modelname):
        for model in prices["price_list"]:
            if model["model_name"] == modelname:
                return model["input_price"], model["output_price"]
        return None, None  # Return None if model is not found

    def handle(self, msg):

        v = msg.value()
        modelname = v.model

        # Sender-produced ID
        id = msg.properties()["id"]

        print(f"Handling response {id}...", flush=True)

        num_in = v.in_token
        num_out = v.out_token

        model_input_price, model_output_price = self.get_prices(price_list, modelname)
        cost_in = num_in * model_input_price
        cost_out = num_out * model_output_price
        cost_per_call = cost_in + cost_out

        print(f"Input Tokens: {num_in}", flush=True)
        print(f"Output Tokens: {num_out}", flush=True)
        print(f"Cost for call: ${cost_per_call:.6f}", flush=True)

    @staticmethod
    def add_args(parser):

        Consumer.add_args(
            parser, default_input_queue, default_subscriber,
        )

def run():

    Processor.start(module, __doc__)