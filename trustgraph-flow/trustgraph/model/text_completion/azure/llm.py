
"""
Simple LLM service, performs text prompt completion using the Azure
serverless endpoint service.  Input is prompt, output is response.
"""

import requests
import json
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
default_temperature = 0.0
default_max_output = 4192
default_model = "AzureAI"
default_endpoint = os.getenv("AZURE_ENDPOINT")
default_token = os.getenv("AZURE_TOKEN")

class Processor(ConsumerProducer):

    def __init__(self, **params):

        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)
        endpoint = params.get("endpoint", default_endpoint)
        token = params.get("token", default_token)
        temperature = params.get("temperature", default_temperature)
        max_output = params.get("max_output", default_max_output)
        model = default_model

        if endpoint is None:
            raise RuntimeError("Azure endpoint not specified")

        if token is None:
            raise RuntimeError("Azure token not specified")

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "output_queue": output_queue,
                "subscriber": subscriber,
                "input_schema": TextCompletionRequest,
                "output_schema": TextCompletionResponse,
                "temperature": temperature,
                "max_output": max_output,
                "model": model,
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

        self.endpoint = endpoint
        self.token = token
        self.temperature = temperature
        self.max_output = max_output
        self.model = model

    def build_prompt(self, system, content):

        data =  {
            "messages": [
                {
                    "role": "system", "content": system
                },
                {
                    "role": "user", "content": content
                }
            ],
            "max_tokens": self.max_output,
            "temperature": self.temperature,
            "top_p": 1
        }

        body = json.dumps(data)

        return body

    def call_llm(self, body):

        url = self.endpoint

        # Replace this with the primary/secondary key, AMLToken, or
        # Microsoft Entra ID token for the endpoint
        api_key = self.token

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }

        resp = requests.post(url, data=body, headers=headers)

        if resp.status_code == 429:
            raise TooManyRequests()

        if resp.status_code != 200:
            raise RuntimeError("LLM failure")

        result = resp.json()

        return result

    def handle(self, msg):

        v = msg.value()

        # Sender-produced ID

        id = msg.properties()["id"]

        print(f"Handling prompt {id}...", flush=True)

        try:

            prompt = self.build_prompt(
                v.system,
                v.prompt
            )

            with __class__.text_completion_metric.time():
                response = self.call_llm(prompt)

            resp = response['choices'][0]['message']['content']
            inputtokens = response['usage']['prompt_tokens']
            outputtokens = response['usage']['completion_tokens']

            print(resp, flush=True)
            print(f"Input Tokens: {inputtokens}", flush=True)
            print(f"Output Tokens: {outputtokens}", flush=True)

            print("Send response...", flush=True)

            r = TextCompletionResponse(response=resp, error=None, in_token=inputtokens, out_token=outputtokens, model=self.model)
            self.producer.send(r, properties={"id": id})

        except TooManyRequests:

            print("Send rate limit response...", flush=True)

            r = TextCompletionResponse(
                error=Error(
                    type = "rate-limit",
                    message = str(e),
                ),
                response=None,
                in_token=None,
                out_token=None,
                model=None,
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
                in_token=None,
                out_token=None,
                model=None,
            )

            self.producer.send(r, properties={"id": id})

            self.consumer.acknowledge(msg)

        print("Done.", flush=True)

    @staticmethod
    def add_args(parser):

        ConsumerProducer.add_args(
            parser, default_input_queue, default_subscriber,
            default_output_queue,
        )

        parser.add_argument(
            '-e', '--endpoint',
            default=default_endpoint,
            help=f'LLM model endpoint'
        )

        parser.add_argument(
            '-k', '--token',
            default=default_token,
            help=f'LLM model token'
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
    
    Processor.start(module, __doc__)
