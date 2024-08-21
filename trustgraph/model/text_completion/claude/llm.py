
"""
Simple LLM service, performs text prompt completion using Claude.
Input is prompt, output is response.
"""

import anthropic

from .... schema import TextCompletionRequest, TextCompletionResponse
from .... schema import text_completion_request_queue
from .... schema import text_completion_response_queue
from .... log_level import LogLevel
from .... base import ConsumerProducer

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = text_completion_request_queue
default_output_queue = text_completion_response_queue
default_subscriber = module
default_model = 'claude-3-5-sonnet-20240620'
default_temperature = 0.0
default_max_output = 8192

class Processor(ConsumerProducer):

    def __init__(self, **params):
    
        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)
        model = params.get("model", default_model)
        api_key = params.get("api_key")
        temperature = params.get("temperature", default_temperature)
        max_output = params.get("max_output", default_max_output)

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "output_queue": output_queue,
                "subscriber": subscriber,
                "input_schema": TextCompletionRequest,
                "output_schema": TextCompletionResponse,
                "model": model,
                "temperature": temperature,
                "max_output": max_output,
            }
        )

        self.model = model
        self.claude = anthropic.Anthropic(api_key=api_key)
        self.temperature = temperature
        self.max_output = max_output

        print("Initialised", flush=True)

    def handle(self, msg):

        v = msg.value()

        # Sender-produced ID

        id = msg.properties()["id"]

        print(f"Handling prompt {id}...", flush=True)

        prompt = v.prompt

        # FIXME: Rate limits?
        response = message = self.claude.messages.create(
            model=self.model,
            max_tokens=self.max_output,
            temperature=self.temperature,
            system = "You are a helpful chatbot.",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )

        resp = response.content[0].text
        print(resp, flush=True)

        print("Send response...", flush=True)
        r = TextCompletionResponse(response=resp)
        self.send(r, properties={"id": id})

        print("Done.", flush=True)

    @staticmethod
    def add_args(parser):

        ConsumerProducer.add_args(
            parser, default_input_queue, default_subscriber,
            default_output_queue,
        )

        parser.add_argument(
            '-m', '--model',
            default="claude-3-5-sonnet-20240620",
            help=f'LLM model (default: claude-3-5-sonnet-20240620)'
        )

        parser.add_argument(
            '-k', '--api-key',
            help=f'Claude API key'
        )

        parser.add_argument(
            '-t', '--temperature',
            type=float,
            default=default_temperature,
            help=f'LLM temperature parameter (default: {default_temperature})'
        )

        parser.add_argument(
            '-l', '--max-output',
            type=int,
            default=default_max_output,
            help=f'LLM max output tokens (default: {default_max_output})'
        )

def run():

    Processor.start(module, __doc__)

    
