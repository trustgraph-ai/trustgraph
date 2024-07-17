
"""
Simple LLM service, performs text prompt completion using the Azure
serverless endpoint service.  Input is prompt, output is response.
"""

import requests
import json

from ... schema import TextCompletionRequest, TextCompletionResponse
from ... log_level import LogLevel
from ... base import ConsumerProducer

default_input_queue = 'llm-complete-text'
default_output_queue = 'llm-complete-text-response'
default_subscriber = 'llm-azure-text'

class Processor(ConsumerProducer):

    def __init__(
            self,
            pulsar_host=None,
            input_queue=default_input_queue,
            output_queue=default_output_queue,
            subscriber=default_subscriber,
            log_level=LogLevel.INFO,
            endpoint=None,
            token=None,
    ):

        super(Processor, self).__init__(
            pulsar_host=pulsar_host,
            log_level=log_level,
            input_queue=input_queue,
            output_queue=output_queue,
            subscriber=subscriber,
            input_schema=TextCompletionRequest,
            output_schema=TextCompletionResponse,
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
            "max_tokens": 4192,
            "temperature": 0.2,
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

def run():
    
    Processor.start("llm-azure-text", __doc__)
