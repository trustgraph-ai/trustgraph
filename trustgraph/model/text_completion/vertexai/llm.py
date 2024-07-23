
"""
Simple LLM service, performs text prompt completion using VertexAI on
Google Cloud.   Input is prompt, output is response.
"""

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

from .... schema import TextCompletionRequest, TextCompletionResponse
from .... schema import text_completion_request_queue
from .... schema import text_completion_response_queue
from .... log_level import LogLevel
from .... base import ConsumerProducer

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = text_completion_request_queue
default_output_queue = text_completion_response_queue
default_subscriber = module

class Processor(ConsumerProducer):

    def __init__(self, **params):

        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)
        region = params.get("region", "us-west1")
        model = params.get("model", "gemini-1.0-pro-001")
        private_key = params.get("private_key")

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "output_queue": output_queue,
                "subscriber": subscriber,
                "input_schema": TextCompletionRequest,
                "output_schema": TextCompletionResponse,
            }
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

        if private_key:
            credentials = service_account.Credentials.from_service_account_file(private_key)
        else:
            credentials = None

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

    def handle(self, msg):

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

        # Let other exceptions fall through

    @staticmethod
    def add_args(parser):

        ConsumerProducer.add_args(
            parser, default_input_queue, default_subscriber,
            default_output_queue,
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

def run():

    Processor.start(module, __doc__)

