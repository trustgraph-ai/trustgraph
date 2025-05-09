"""
Simple token counter for each LLM response.
"""

from prometheus_client import Counter
import json

from .. schema import TextCompletionResponse, Error
from .. base import FlowProcessor, ConsumerSpec

default_ident = "metering"

class Processor(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id", default_ident)

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

        super(Processor, self).__init__(
            **params | {
                "id": id,
            }
        )

        self.register_config_handler(self.on_cost_config)

        self.register_specification(
            ConsumerSpec(
                name = "input",
                schema = TextCompletionResponse,
                handler = self.on_message,
            )
        )

        self.prices = {}

        self.config_key = "token-costs"

    # Load token costs from the config service
    async def on_cost_config(self, config, version):

        print("Loading configuration version", version)

        if self.config_key not in config:
            print(f"No key {self.config_key} in config", flush=True)
            return

        config = config[self.config_key]

        self.prices = {
            k: json.loads(v)
            for k, v in config.items()
        }

    def get_prices(self, modelname):

        if modelname in self.prices:
            model = self.prices[modelname]
            return model["input_price"], model["output_price"]
        return None, None  # Return None if model is not found

    async def on_message(self, msg, consumer, flow):

        v = msg.value()

        modelname = v.model
        num_in = v.in_token
        num_out = v.out_token

        __class__.input_token_metric.inc(num_in)
        __class__.output_token_metric.inc(num_out)

        model_input_price, model_output_price = self.get_prices(modelname)

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

        FlowProcessor.add_args(parser)

def run():

    Processor.launch(default_ident, __doc__)
