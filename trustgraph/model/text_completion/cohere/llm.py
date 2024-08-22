
"""
Simple LLM service, performs text prompt completion using Cohere.
Input is prompt, output is response.
"""

import cohere

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

class Processor(ConsumerProducer):

    def __init__(self, **params):
    
        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)
        model = params.get("model", default_model)
        api_key = params.get("api_key")
        temperature = params.get("temperature", default_temperature)

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

        self.model = model
        self.temperature = temperature
        self.cohere = cohere.Client(api_key=api_key)

        print("Initialised", flush=True)

    def handle(self, msg):

        v = msg.value()

        # Sender-produced ID

        id = msg.properties()["id"]

        print(f"Handling prompt {id}...", flush=True)

        prompt = v.prompt

        try:

            output = self.cohere.chat( 
                model=self.model,
                message=prompt,
                preamble = "You are a helpful AI-assistant.",
                temperature=self.temperature,
                chat_history=[],
                prompt_truncation='auto',
                connectors=[]
            )

            resp = output.text
            print(resp, flush=True)

            resp = resp.replace("```json", "")
            resp = resp.replace("```", "")

            print("Send response...", flush=True)
            r = TextCompletionResponse(response=resp)
            self.send(r, properties={"id": id})

            print("Done.", flush=True)

        # FIXME: Wrong exception, don't know what this LLM throws
        # for a rate limit
        except TooManyRequests:

            print("Send rate limit response...", flush=True)

            r = TextCompletionResponse(
                error=Error(
                    type = "rate-limit",
                    message = str(e),
                ),
                response=None,
            )

            self.producer.send(r, properties={"id": id})

            self.consumer.acknowledge(msg)

        except Exception as e:

            print(f"Exception: {e}")

            print("Send error response...", flush=True)

            r = TextCompletionResponse(
                error=Error(
                    type = "llm-error",
                    message = str(e),
                ),
                response=None,
            )

            self.producer.send(r, properties={"id": id})

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
            help=f'Cohere API key'
        )

        parser.add_argument(
            '-t', '--temperature',
            type=float,
            default=default_temperature,
            help=f'LLM temperature parameter (default: {default_temperature})'
        )

def run():

    Processor.start(module, __doc__)

    
