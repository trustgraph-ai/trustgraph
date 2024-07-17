
"""
Simple LLM service, performs text prompt completion using an Ollama service.
Input is prompt, output is response.
"""

import pulsar
from pulsar.schema import JsonSchema
import tempfile
import base64
import os
import argparse
from langchain_community.llms import Ollama
import time

from ... schema import TextCompletionRequest, TextCompletionResponse
from ... log_level import LogLevel
from ... base import ConsumerProducer

default_input_queue = 'llm-complete-text'
default_output_queue = 'llm-complete-text-response'
default_subscriber = 'llm-ollama-text'
default_model = 'gemma2'
default_ollama = 'http://localhost:11434'

class Processor(ConsumerProducer):

    def __init__(
            self,
            pulsar_host=None,
            input_queue=default_input_queue,
            output_queue=default_output_queue,
            subscriber=default_subscriber,
            log_level=LogLevel.INFO,
            model=default_model,
            ollama=default_ollama,
    ):

        super(Processor, self).__init__(
            pulsar_host=pulsar_host,
            log_level=log_level,
            input_queue=input_queue,
            output_queue=output_queue,
            subscriber=subscriber,
            request_schema=TextCompletionRequest,
            response_schema=TextCompletionResponse,
        )

        self.llm = Ollama(base_url=ollama, model=model)

    def handle(self, msg):

        v = msg.value()

        # Sender-produced ID
        id = msg.properties()["id"]

        print(f"Handling prompt {id}...", flush=True)

        prompt = v.prompt
        response = self.llm.invoke(prompt)

        print("Send response...", flush=True)

        r = TextCompletionResponse(response=response)

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
            default="gemma2",
            help=f'LLM model (default: gemma2)'
        )

        parser.add_argument(
            '-r', '--ollama',
            default=default_ollama,
            help=f'ollama (default: {default_ollama})'
        )

def run():

    Processor.start("llm-ollama-text", __doc__)

    
