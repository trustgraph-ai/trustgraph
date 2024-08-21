
"""
Simple LLM service, performs text prompt completion using the Azure
serverless endpoint service.  Input is prompt, output is response.
"""

import requests
import json

from .... schema import TextCompletionRequest, TextCompletionResponse
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
default_max = 4192

class Processor(ConsumerProducer):

    def __init__(self, **params):

        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)
        endpoint = params.get("endpoint")
        token = params.get("token")
        temperature = params.get("temperature", default_temperature)
        max_tokens = params.get("max_output", default_max)

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "output_queue": output_queue,
                "subscriber": subscriber,
                "input_schema": TextCompletionRequest,
                "output_schema": TextCompletionResponse,
            }
        )

        self.endpoint = endpoint
        self.token = token

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
            "max_tokens": max_tokens,
            "temperature": temperature,
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

        result = resp.json()

        message_content = result['choices'][0]['message']['content']

        return message_content

    def handle(self, msg):

        v = msg.value()

        # Sender-produced ID

        id = msg.properties()["id"]

        print(f"Handling prompt {id}...", flush=True)

        prompt = self.build_prompt(
            "You are a helpful chatbot",
            v.prompt
        )

        response = self.call_llm(prompt)

        print("Send response...", flush=True)
        r = TextCompletionResponse(response=response)
        self.producer.send(r, properties={"id": id})

        print("Done.", flush=True)

    @staticmethod
    def add_args(parser):

        ConsumerProducer.add_args(
            parser, default_input_queue, default_subscriber,
            default_output_queue,
        )

        parser.add_argument(
            '-e', '--endpoint',
            help=f'LLM model endpoint'
        )

        parser.add_argument(
            '-k', '--token',
            help=f'LLM model token'
        )

        parser.add_argument(
            '-t', '--temperature',
            default=f"temp=0.0",
            help=f'LLM temperature parameter'
        )

        parser.add_argument(
            '-l', '--max-output',
            default=f"max_tokens=4192",
            help=f'LLM max output tokens'
        )

def run():
    
    Processor.start(module, __doc__)
