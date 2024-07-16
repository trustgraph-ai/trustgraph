
"""
Simple LLM service, performs text prompt completion using the Azure
serverless endpoint service.  Input is prompt, output is response.
"""

import pulsar
from pulsar.schema import JsonSchema
import tempfile
import base64
import os
import argparse
from langchain_community.llms import Ollama
import requests
import time
import json

from ... schema import TextCompletionRequest, TextCompletionResponse
from ... log_level import LogLevel

default_pulsar_host = os.getenv("PULSAR_HOST", 'pulsar://pulsar:6650')
default_input_queue = 'llm-complete-text'
default_output_queue = 'llm-complete-text-response'
default_subscriber = 'llm-azure-text'

class Processor:

    def __init__(
            self,
            pulsar_host=default_pulsar_host,
            input_queue=default_input_queue,
            output_queue=default_output_queue,
            subscriber=default_subscriber,
            log_level=LogLevel.INFO,
            endpoint=None,
            token=None,
    ):

        self.client = None

        self.client = pulsar.Client(
            pulsar_host,
            logger=pulsar.ConsoleLogger(log_level.to_pulsar())
        )

        self.consumer = self.client.subscribe(
            input_queue, subscriber,
            schema=JsonSchema(TextCompletionRequest),
        )

        self.producer = self.client.create_producer(
            topic=output_queue,
            schema=JsonSchema(TextCompletionResponse),
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

    def run(self):

        while True:

            msg = self.consumer.receive()

            try:

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

                # Acknowledge successful processing of the message
                self.consumer.acknowledge(msg)

            except Exception as e:

                print("Exception:", e, flush=True)

                # Message failed to be processed
                self.consumer.negative_acknowledge(msg)

    def __del__(self):
        self.client.close()

def run():

    parser = argparse.ArgumentParser(
        prog='llm-ollama-text',
        description=__doc__,
    )

    parser.add_argument(
        '-p', '--pulsar-host',
        default=default_pulsar_host,
        help=f'Pulsar host (default: {default_pulsar_host})',
    )

    parser.add_argument(
        '-i', '--input-queue',
        default=default_input_queue,
        help=f'Input queue (default: {default_input_queue})'
    )

    parser.add_argument(
        '-s', '--subscriber',
        default=default_subscriber,
        help=f'Queue subscriber name (default: {default_subscriber})'
    )

    parser.add_argument(
        '-o', '--output-queue',
        default=default_output_queue,
        help=f'Output queue (default: {default_output_queue})'
    )

    parser.add_argument(
        '-l', '--log-level',
        type=LogLevel,
        default=LogLevel.INFO,
        choices=list(LogLevel),
        help=f'Output queue (default: info)'
    )

    parser.add_argument(
        '-e', '--endpoint',
        help=f'LLM model endpoint'
    )

    parser.add_argument(
        '-k', '--token',
        help=f'LLM model token'
    )

    args = parser.parse_args()

    while True:

        try:

            p = Processor(
                pulsar_host=args.pulsar_host,
                input_queue=args.input_queue,
                output_queue=args.output_queue,
                subscriber=args.subscriber,
                log_level=args.log_level,
                endpoint=args.endpoint,
                token=args.token,
            )

            p.run()

        except Exception as e:

            print("Exception:", e, flush=True)
            print("Will retry...", flush=True)

        time.sleep(10)


