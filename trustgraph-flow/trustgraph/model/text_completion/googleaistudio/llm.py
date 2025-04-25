
"""
Simple LLM service, performs text prompt completion using GoogleAIStudio.
Input is prompt, output is response.
"""

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.api_core.exceptions import ResourceExhausted
from prometheus_client import Histogram
import os

from .... exceptions import TooManyRequests
from .... base import LlmService, LlmResult

default_ident = "text-completion"

default_model = 'gemini-1.5-flash-002'
default_temperature = 0.0
default_max_output = 8192
default_api_key = os.getenv("GOOGLE_AI_STUDIO_KEY")

class Processor(LlmService):

    def __init__(self, **params):
    
        model = params.get("model", default_model)
        api_key = params.get("api_key", default_api_key)
        temperature = params.get("temperature", default_temperature)
        max_output = params.get("max_output", default_max_output)

        if api_key is None:
            raise RuntimeError("Google AI Studio API key not specified")

        super(Processor, self).__init__(
            **params | {
                "model": model,
                "temperature": temperature,
                "max_output": max_output,
            }
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
            # There is a documentation conflict on whether or not
            # CIVIC_INTEGRITY is a valid category
            # HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY: block_level,
        }

        self.llm = genai.GenerativeModel(
            model_name=model,
            generation_config=self.generation_config,
            safety_settings=self.safety_settings,
            system_instruction="You are a helpful AI assistant.",
        )

        print("Initialised", flush=True)

    async def generate_content(self, system, prompt):

        # FIXME: There's a system prompt above.  Maybe if system changes,
        # then reset self.llm?  It shouldn't do, because system prompt
        # is set system wide?

        # Or... could keep different LLM structures for different system
        # prompts?

        prompt = system + "\n\n" + prompt

        try:

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

            resp = LlmResult(
                text = resp,
                in_token = inputtokens,
                out_token = outputtokens,
                model = self.model
            )

            return resp

        except ResourceExhausted as e:

            print("Hit rate limit:", e, flush=True)

            # Leave rate limit retries to the default handler
            raise TooManyRequests()

        except Exception as e:

            # Apart from rate limits, treat all exceptions as unrecoverable

            print(type(e), flush=True)
            print(f"Exception: {e}", flush=True)
            raise e

    @staticmethod
    def add_args(parser):

        LlmService.add_args(parser)

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
    
    Processor.launch(default_ident, __doc__)
