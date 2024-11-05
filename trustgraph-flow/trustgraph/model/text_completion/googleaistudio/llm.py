
"""
Simple LLM service, performs text prompt completion using GoogleAIStudio.
Input is prompt, output is response.
"""

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.api_core.exceptions import ResourceExhausted
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
default_model = 'gemini-1.5-flash-002'
default_temperature = 0.0
default_max_output = 8192
default_api_key = os.getenv("GOOGLE_AI_STUDIO_KEY")

class Processor(ConsumerProducer):

    def __init__(self, **params):
    
        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)
        model = params.get("model", default_model)
        api_key = params.get("api_key", default_api_key)
        temperature = params.get("temperature", default_temperature)
        max_output = params.get("max_output", default_max_output)

        if api_key is None:
            raise RuntimeError("Google AI Studio API key not specified")

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

        genai.configure(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_output = max_output

        self.generation_config = {
            "temperature": temperature,
            "top_p": 1,
            "top_k": 40,
            "max_output_tokens": max_output,
            "response_mime_type": "text/plain",
        }

        block_level = HarmBlockThreshold.BLOCK_ONLY_HIGH

        self.safety_settings={
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: block_level,
            HarmCategory.HARM_CATEGORY_HARASSMENT: block_level,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: block_level,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: block_level,
            # There is a documentation conflict on whether or not CIVIC_INTEGRITY is a valid category
            # HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY: block_level,
        }

        self.llm = genai.GenerativeModel(
            model_name=model,
            generation_config=self.generation_config,
            safety_settings=self.safety_settings,
            system_instruction="You are a helpful AI assistant.",
        )

        print("Initialised", flush=True)

    def handle(self, msg):

        v = msg.value()

        # Sender-produced ID

        id = msg.properties()["id"]

        print(f"Handling prompt {id}...", flush=True)

        # FIXME: There's a system prompt above.  Maybe if system changes,
        # then reset self.llm?  It shouldn't do, because system prompt
        # is set system wide?

        # Or... could keep different LLM structures for different system
        # prompts?

        prompt = v.system + "\n\n" + v.prompt

        try:

            # FIXME: Rate limits?

            with __class__.text_completion_metric.time():

                chat_session = self.llm.start_chat(
                    history=[
                    ]
                )
                response = chat_session.send_message(prompt)

            resp = response.text
            inputtokens = int(response.usage_metadata.prompt_token_count)
            outputtokens = int(response.usage_metadata.candidates_token_count)
            print(resp, flush=True)
            print(f"Input Tokens: {inputtokens}", flush=True)
            print(f"Output Tokens: {outputtokens}", flush=True)

            print("Send response...", flush=True)
            r = TextCompletionResponse(response=resp, error=None, in_token=inputtokens, out_token=outputtokens, model=self.model)
            self.send(r, properties={"id": id})

            print("Done.", flush=True)

        # FIXME: Wrong exception, don't know what this LLM throws
        # for a rate limit
        except ResourceExhausted as e:

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

        parser.add_argument(
            '-k', '--api-key',
            default=default_api_key,
            help=f'GoogleAIStudio API key'
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

    
