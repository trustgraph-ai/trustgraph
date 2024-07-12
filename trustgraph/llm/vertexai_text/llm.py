
"""
Simple LLM service, performs text prompt completion using VertexAI on
Google Cloud.   Input is prompt, output is response.
"""

import pulsar
from pulsar.schema import JsonSchema
import tempfile
import base64
import os
import argparse
import vertexai
import time

from google.oauth2 import service_account
import google

from vertexai.preview.generative_models import (
    Content,
    FunctionDeclaration,
    GenerativeModel,
    GenerationConfig,
    HarmCategory,
    HarmBlockThreshold,
    Part,
    Tool,
)

from ... schema import TextCompletionRequest, TextCompletionResponse
from ... log_level import LogLevel

class Processor:

    def __init__(
            self,
            pulsar_host,
            input_queue,
            output_queue,
            subscriber,
            log_level,
            credentials,
            region,
            model,
    ):

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

        self.parameters = {
            "temperature": 0.2,
            "top_p": 1.0,
            "top_k": 32,
            "candidate_count": 1,
            "max_output_tokens": 8192,
        }

        self.generation_config = GenerationConfig(
            temperature=0.2,
            top_p=1.0,
            top_k=10,
            candidate_count=1,
            max_output_tokens=8191,
        )

        # Block none doesn't seem to work
        block_level = HarmBlockThreshold.BLOCK_ONLY_HIGH
        #     block_level = HarmBlockThreshold.BLOCK_NONE

        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: block_level,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: block_level,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: block_level,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: block_level,
        }

        print("Initialise VertexAI...", flush=True)

        if credentials:
            vertexai.init(
                location=region,
                credentials=credentials,
                project=credentials.project_id,
            )
        else:
            vertexai.init(
                location=region
            )

        print(f"Initialise model {model}", flush=True)
        self.llm = GenerativeModel(model)

        print("Initialisation complete", flush=True)

    def run(self):

        while True:

            msg = self.consumer.receive()

            try:

                v = msg.value()

	        # Sender-produced ID

                id = msg.properties()["id"]

                print(f"Handling prompt {id}...", flush=True)

                prompt = v.prompt

                resp = self.llm.generate_content(
                    prompt, generation_config=self.generation_config,
                    safety_settings=self.safety_settings
                )

                resp = resp.text

                resp = resp.replace("```json", "")
                resp = resp.replace("```", "")

                print("Send response...", flush=True)
                r = TextCompletionResponse(response=resp)
                self.producer.send(r, properties={"id": id})

                print("Done.", flush=True)

                # Acknowledge successful processing of the message
                self.consumer.acknowledge(msg)

            except google.api_core.exceptions.ResourceExhausted:

                print("429, resource busy, sleeping", flush=True)
                time.sleep(15)
                self.consumer.negative_acknowledge(msg)

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

    default_pulsar_host = os.getenv("PULSAR_HOST", 'pulsar://pulsar:6650')
    default_input_queue = 'llm-complete-text'
    default_output_queue = 'llm-complete-text-response'
    default_subscriber = 'llm-vertexai-text'

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
        '-m', '--model',
        default="gemini-1.0-pro-001",
        help=f'LLM model (default: gemini-1.0-pro-001)'
    )
    # Also: text-bison-32k

    parser.add_argument(
        '-k', '--private-key',
        help=f'Google Cloud private JSON file'
    )

    parser.add_argument(
        '-r', '--region',
        default='us-west1',
        help=f'Google Cloud region (default: us-west1)',
    )

    args = parser.parse_args()

    if args.private_key:
        credentials = service_account.Credentials.from_service_account_file(
            args.private_key
        )
    else:
        credentials = None

    while True:

        try:
        
            p = Processor(
                pulsar_host=args.pulsar_host,
                input_queue=args.input_queue,
                output_queue=args.output_queue,
                subscriber=args.subscriber,
                log_level=args.log_level,
                credentials=credentials,
                region=args.region,
                model=args.model,
            )

            p.run()

        except Exception as e:

            print("Exception:", e, flush=True)
            print("Will retry...", flush=True)

        time.sleep(10)

