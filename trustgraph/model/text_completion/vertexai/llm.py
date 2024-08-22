
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
default_model = 'gemini-1.0-pro-001'
default_region = 'us-central1'
default_temperature = 0.0
default_max_output = 8192

class Processor(ConsumerProducer):

    def __init__(self, **params):

        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)
        region = params.get("region", default_region)
        model = params.get("model", default_model)
        private_key = params.get("private_key")
        temperature = params.get("temperature", default_temperature)
        max_output = params.get("max_output", default_max_output)

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
            "temperature": temperature,
            "top_p": 1.0,
            "top_k": 32,
            "candidate_count": 1,
            "max_output_tokens": max_output,
        }

        self.generation_config = GenerationConfig(
            temperature=temperature,
            top_p=1.0,
            top_k=10,
            candidate_count=1,
            max_output_tokens=max_output,
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

            r = TextCompletionResponse(
                error=None,
                response=resp,
            )

            self.producer.send(r, properties={"id": id})

            print("Done.", flush=True)

            # Acknowledge successful processing of the message
            self.consumer.acknowledge(msg)

        except google.api_core.exceptions.ResourceExhausted as e:

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
            default=default_model,
            help=f'LLM model (default: {default_model})'
        )
        # Also: text-bison-32k

        parser.add_argument(
            '-k', '--private-key',
            help=f'Google Cloud private JSON file'
        )

        parser.add_argument(
            '-r', '--region',
            default=default_region,
            help=f'Google Cloud region (default: {default_region})',
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

