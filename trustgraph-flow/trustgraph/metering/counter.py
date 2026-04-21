"""
Simple token counter for each LLM response.
"""

from prometheus_client import Counter
import json
import logging

from .. schema import TextCompletionResponse, Error
from .. base import FlowProcessor, ConsumerSpec

# Module logger
logger = logging.getLogger(__name__)

default_ident = "metering"

class Processor(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id", default_ident)

        if not hasattr(__class__, "token_metric"):
            __class__.token_metric = Counter(
                'tokens',
                'Token count',
                ['model', 'direction']
            )

        if not hasattr(__class__, "cost_metric"):
            __class__.cost_metric = Counter(
                'cost',
                'Cost in USD',
                ['model', 'direction']
            )

        super(Processor, self).__init__(
            **params | {
                "id": id,
            }
        )

        self.register_config_handler(self.on_cost_config, types=["token-cost"])

        self.register_specification(
            ConsumerSpec(
                name = "input",
                schema = TextCompletionResponse,
                handler = self.on_message,
            )
        )

        # Per-workspace price tables
        self.prices = {}

        self.config_key = "token-cost"

    async def on_cost_config(self, workspace, config, version):

        logger.info(
            f"Loading metering configuration version {version} "
            f"for workspace {workspace}"
        )

        if self.config_key not in config:
            logger.warning(
                f"No key {self.config_key} in config for {workspace}"
            )
            self.prices[workspace] = {}
            return

        prices = config[self.config_key]

        self.prices[workspace] = {
            k: json.loads(v)
            for k, v in prices.items()
        }

    def get_prices(self, workspace, modelname):

        ws_prices = self.prices.get(workspace, {})
        if modelname in ws_prices:
            model = ws_prices[modelname]
            return model["input_price"], model["output_price"]
        return None, None  # Return None if model is not found

    async def on_message(self, msg, consumer, flow):

        v = msg.value()

        workspace = flow.workspace

        modelname = v.model or "unknown"
        num_in = v.in_token or 0
        num_out = v.out_token or 0

        # Increment token metrics with model and direction labels
        __class__.token_metric.labels(model=modelname, direction="input").inc(num_in)
        __class__.token_metric.labels(model=modelname, direction="output").inc(num_out)

        model_input_price, model_output_price = self.get_prices(
            workspace, modelname
        )

        if model_input_price == None:
            cost_per_call = f"Model Not Found in Price list"
        else:
            cost_in = num_in * model_input_price
            cost_out = num_out * model_output_price
            cost_per_call = round(cost_in + cost_out, 6)

            # Increment cost metrics with model and direction labels
            __class__.cost_metric.labels(model=modelname, direction="input").inc(cost_in)
            __class__.cost_metric.labels(model=modelname, direction="output").inc(cost_out)

        logger.debug(
            f"Model: {modelname}, in={num_in}, out={num_out}, "
            f"cost=${cost_per_call}"
        )

    @staticmethod
    def add_args(parser):

        FlowProcessor.add_args(parser)

def run():

    Processor.launch(default_ident, __doc__)
