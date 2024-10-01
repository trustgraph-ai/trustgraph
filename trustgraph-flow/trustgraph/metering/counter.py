"""
Simple token counter for each LLM response.
"""

from prometheus_client import Counter
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

        if not hasattr(__class__, "input_token_metric"):
            __class__.input_token_metric = Counter(
                'input_tokens', 'Input token count'
            )

        if not hasattr(__class__, "output_token_metric"):
            __class__.output_token_metric = Counter(
                'output_tokens', 'Output token count'
            )

        if not hasattr(__class__, "input_cost_metric"):
            __class__.input_cost_metric = Counter(
                'input_cost', 'Input cost'
            )

        if not hasattr(__class__, "output_cost_metric"):
            __class__.output_cost_metric = Counter(
                'output_cost', 'Output cost'
            )

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

        __class__.input_token_metric.inc(num_in)
        __class__.output_token_metric.inc(num_out)

        model_input_price, model_output_price = self.get_prices(price_list, modelname)

        if model_input_price == None:
            cost_per_call = f"Model Not Found in Price list"
        else:
            cost_in = num_in * model_input_price
            cost_out = num_out * model_output_price
            cost_per_call = round(cost_in + cost_out, 6)

            __class__.input_cost_metric.inc(cost_in)
            __class__.output_cost_metric.inc(cost_out)

        print(f"Input Tokens: {num_in}", flush=True)
        print(f"Output Tokens: {num_out}", flush=True)
        print(f"Cost for call: ${cost_per_call}", flush=True)

    @staticmethod
    def add_args(parser):

        Consumer.add_args(
            parser, default_input_queue, default_subscriber,
        )

def run():

    Processor.start(module, __doc__)
