
"""
Simple LLM service, performs text prompt completion using Cohere.
Input is prompt, output is response.
"""

import cohere
from prometheus_client import Histogram
import os

from .... schema import TextCompletionRequest, TextCompletionResponse, Error
from .... schema import text_completion_request_queue
from .... schema import text_completion_response_queue
from .... log_level import LogLevel
from .... base import ConsumerProducer
from .... exceptions import TooManyRequests

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = text_completion_request_queue
default_output_queue = text_completion_response_queue
default_subscriber = module
default_model = 'c4ai-aya-23-8b'
default_temperature = 0.0
default_api_key = os.getenv("COHERE_KEY")

class Processor(ConsumerProducer):

    def __init__(self, **params):
    
        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)
        model = params.get("model", default_model)
        api_key = params.get("api_key", default_api_key)
        temperature = params.get("temperature", default_temperature)

        if api_key is None:
            raise RuntimeError("Cohere API key not specified")

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "output_queue": output_queue,
                "subscriber": subscriber,
                "input_schema": TextCompletionRequest,
                "output_schema": TextCompletionResponse,
                "model": model,
                "temperature": temperature,
            }
        )

        if not hasattr(__class__, "text_completion_metric"):
            __class__.text_completion_metric = Histogram(
                'text_completion_duration',
                'Text completion duration (seconds)',
                buckets=[
                    0.25, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0,
                    8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0,
                    17.0, 18.0, 19.0, 20.0, 21.0, 22.0, 23.0, 24.0, 25.0,
                    30.0, 35.0, 40.0, 45.0, 50.0, 60.0, 80.0, 100.0,
                    120.0
                ]
            )

        self.model = model
        self.temperature = temperature
        self.cohere = cohere.Client(api_key=api_key)

        print("Initialised", flush=True)

    async def handle(self, msg):

        v = msg.value()

        # Sender-produced ID

        id = msg.properties()["id"]

        print(f"Handling prompt {id}...", flush=True)

        system = v.system
        prompt = v.prompt

        try:

            with __class__.text_completion_metric.time():

                output = self.cohere.chat( 
                    model=self.model,
                    message=prompt,
                    preamble = system,
                    temperature=self.temperature,
                    chat_history=[],
                    prompt_truncation='auto',
                    connectors=[]
                )

            resp = output.text
            inputtokens = int(output.meta.billed_units.input_tokens)
            outputtokens = int(output.meta.billed_units.output_tokens)

            print(resp, flush=True)
            print(f"Input Tokens: {inputtokens}", flush=True)
            print(f"Output Tokens: {outputtokens}", flush=True)

            print("Send response...", flush=True)
            r = TextCompletionResponse(response=resp, error=None, in_token=inputtokens, out_token=outputtokens, model=self.model)
            self.await send(r, properties={"id": id})

            print("Done.", flush=True)

        # FIXME: Wrong exception, don't know what this LLM throws
        # for a rate limit
        except cohere.TooManyRequestsError:

            # Leave rate limit retries to the base handler
            raise TooManyRequests()

        except Exception as e:

            # Apart from rate limits, treat all exceptions as unrecoverable

            print(f"Exception: {e}")

            print("Send error response...", flush=True)

            r = TextCompletionResponse(
                error=Error(
                    type = "llm-error",
                    message = str(e),
                ),
                response=None,
                in_token=None,
                out_token=None,
                model=None,
            )

            await self.producer.send(r, properties={"id": id})

            self.consumer.acknowledge(msg)

    @staticmethod
    def add_args(parser):

        ConsumerProducer.add_args(
            parser, default_input_queue, default_subscriber,
            default_output_queue,
        )

        parser.add_argument(
            '-m', '--model',
            default="c4ai-aya-23-8b",
            help=f'Cohere model (default: c4ai-aya-23-8b)'
        )

        parser.add_argument(
            '-k', '--api-key',
            default=default_api_key,
            help=f'Cohere API key'
        )

        parser.add_argument(
            '-t', '--temperature',
            type=float,
            default=default_temperature,
            help=f'LLM temperature parameter (default: {default_temperature})'
        )

def run():

    Processor.launch(module, __doc__)

    
