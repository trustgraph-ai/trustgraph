
"""
Simple LLM service, performs text prompt completion using Claude.
Input is prompt, output is response.
"""

import anthropic
import os
import logging

from .... exceptions import TooManyRequests
from .... base import LlmService, LlmResult

# Module logger
logger = logging.getLogger(__name__)

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

        self.default_model = model
        self.claude = anthropic.Anthropic(api_key=api_key)
        self.temperature = temperature
        self.max_output = max_output

        logger.info("Claude LLM service initialized")

    async def generate_content(self, system, prompt, model=None):

        # Use provided model or fall back to default
        model_name = model or self.default_model

        logger.debug(f"Using model: {model_name}")

        try:

            response = message = self.claude.messages.create(
                model=model_name,
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
            logger.debug(f"LLM response: {resp}")
            logger.info(f"Input Tokens: {inputtokens}")
            logger.info(f"Output Tokens: {outputtokens}")

            resp = LlmResult(
                text = resp,
                in_token = inputtokens,
                out_token = outputtokens,
                model = model_name
            )

            return resp

        except anthropic.RateLimitError:

            # Leave rate limit retries to the base handler
            raise TooManyRequests()

        except Exception as e:

            # Apart from rate limits, treat all exceptions as unrecoverable

            logger.error(f"Claude LLM exception ({type(e).__name__}): {e}", exc_info=True)
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
