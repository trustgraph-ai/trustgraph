
"""
Simple LLM service, performs text prompt completion using Claude.
Input is prompt, output is response.
"""

import anthropic
from prometheus_client import Histogram
import os

from .... exceptions import TooManyRequests
from .... base import LlmService, LlmResult

default_ident = "text-completion"

default_model = 'claude-3-5-sonnet-20240620'
default_temperature = 0.0
default_max_output = 8192
default_api_key = os.getenv("CLAUDE_KEY")

class Processor(LlmService):

    def __init__(self, **params):
    
        model = params.get("model", default_model)
        api_key = params.get("api_key", default_api_key)
        temperature = params.get("temperature", default_temperature)
        max_output = params.get("max_output", default_max_output)

        if api_key is None:
            raise RuntimeError("Claude API key not specified")

        super(Processor, self).__init__(
            **params | {
                "model": model,
                "temperature": temperature,
                "max_output": max_output,
            }
        )

        self.model = model
        self.claude = anthropic.Anthropic(api_key=api_key)
        self.temperature = temperature
        self.max_output = max_output

        print("Initialised", flush=True)

    async def generate_content(self, system, prompt):

        try:

            response = message = self.claude.messages.create(
                model=self.model,
                max_tokens=self.max_output,
                temperature=self.temperature,
                system = system,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )

            resp = response.content[0].text
            inputtokens = response.usage.input_tokens
            outputtokens = response.usage.output_tokens
            print(resp, flush=True)
            print(f"Input Tokens: {inputtokens}", flush=True)
            print(f"Output Tokens: {outputtokens}", flush=True)

            resp = LlmResult(
                text = resp,
                in_token = inputtokens,
                out_token = outputtokens,
                model = self.model
            )

        except anthropic.RateLimitError:

            # Leave rate limit retries to the base handler
            raise TooManyRequests()

        except Exception as e:

            # Apart from rate limits, treat all exceptions as unrecoverable

            print(f"Exception: {e}")
            raise e

    @staticmethod
    def add_args(parser):

        LlmService.add_args(parser)

        parser.add_argument(
            '-m', '--model',
            default="claude-3-5-sonnet-20240620",
            help=f'LLM model (default: claude-3-5-sonnet-20240620)'
        )

        parser.add_argument(
            '-k', '--api-key',
            default=default_api_key,
            help=f'Claude API key'
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
