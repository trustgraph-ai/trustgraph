
"""
Simple LLM service, performs text prompt completion using OpenAI.
Input is prompt, output is response.
"""

from openai import OpenAI, RateLimitError
from prometheus_client import Histogram
import os

from .... schema import TextCompletionRequest, TextCompletionResponse, Error
from .... schema import text_completion_request_queue
from .... schema import text_completion_response_queue
from .... log_level import LogLevel
from .... base import ConsumerProducer
from .... exceptions import TooManyRequests

module = "text-completion"

default_input_queue = text_completion_request_queue
default_output_queue = text_completion_response_queue
default_subscriber = module
default_model = 'gpt-3.5-turbo'
default_temperature = 0.0
default_max_output = 4096
default_api_key = os.getenv("OPENAI_TOKEN")
default_base_url = os.getenv("OPENAI_BASE_URL", None)

class Processor(ConsumerProducer):

    def __init__(self, **params):
    
        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)
        model = params.get("model", default_model)
        api_key = params.get("api_key", default_api_key)
        base_url = params.get("base_url", default_base_url)
        temperature = params.get("temperature", default_temperature)
        max_output = params.get("max_output", default_max_output)

        if api_key is None:
            raise RuntimeError("OpenAI API key not specified")

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
                "base_url": base_url,
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
        self.max_output = max_output
        self.openai = OpenAI(base_url=base_url, api_key=api_key)

        print("Initialised", flush=True)

    async def handle(self, msg):

        v = msg.value()

        # Sender-produced ID

        id = msg.properties()["id"]

        print(f"Handling prompt {id}...", flush=True)

        prompt = v.system + "\n\n" + v.prompt

        try:

            with __class__.text_completion_metric.time():

                resp = self.openai.chat.completions.create(
                    model=self.model,
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
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_output,
                    top_p=1,
                    frequency_penalty=0,
                    presence_penalty=0,
                    response_format={
                        "type": "text"
                    }
                )
            
            inputtokens = resp.usage.prompt_tokens
            outputtokens = resp.usage.completion_tokens
            print(resp.choices[0].message.content, flush=True)
            print(f"Input Tokens: {inputtokens}", flush=True)
            print(f"Output Tokens: {outputtokens}", flush=True)

            print("Send response...", flush=True)
            r = TextCompletionResponse(
                response=resp.choices[0].message.content,
                error=None,
                in_token=inputtokens,
                out_token=outputtokens,
                model=self.model
            )
            await self.send(r, properties={"id": id})

            print("Done.", flush=True)

        # FIXME: Wrong exception, don't know what this LLM throws
        # for a rate limit
        except RateLimitError:

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

            await self.send(r, properties={"id": id})

            self.consumer.acknowledge(msg)

    @staticmethod
    def add_args(parser):

        ConsumerProducer.add_args(
            parser, default_input_queue, default_subscriber,
            default_output_queue,
        )

        parser.add_argument(
            '-m', '--model',
            default="gpt-3.5-turbo",
            help=f'LLM model (default: GPT-3.5-Turbo)'
        )

        parser.add_argument(
            '-k', '--api-key',
            default=default_api_key,
            help=f'OpenAI API key'
        )

        parser.add_argument(
            '-u', '--url',
            default=default_base_url,
            help=f'OpenAI service base URL'
        )

        parser.add_argument(
            '-t', '--temperature',
            type=float,
            default=default_temperature,
            help=f'LLM temperature parameter (default: {default_temperature})'
        )

        parser.add_argument(
            '-x', '--max-output',
            type=int,
            default=default_max_output,
            help=f'LLM max output tokens (default: {default_max_output})'
        )

def run():

    Processor.launch(module, __doc__)

    
