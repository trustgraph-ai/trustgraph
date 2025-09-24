
"""
Simple LLM service, performs text prompt completion using OpenAI.
Input is prompt, output is response.
"""

from openai import OpenAI, RateLimitError
import os
import logging

from .... exceptions import TooManyRequests
from .... base import LlmService, LlmResult

# Module logger
logger = logging.getLogger(__name__)

default_ident = "text-completion"

default_model = 'gpt-3.5-turbo'
default_temperature = 0.0
default_max_output = 4096
default_api_key = os.getenv("OPENAI_TOKEN")
default_base_url = os.getenv("OPENAI_BASE_URL")

if default_base_url is None or default_base_url == "":
    default_base_url = "https://api.openai.com/v1"

class Processor(LlmService):

    def __init__(self, **params):
    
        model = params.get("model", default_model)
        api_key = params.get("api_key", default_api_key)
        base_url = params.get("url", default_base_url)
        temperature = params.get("temperature", default_temperature)
        max_output = params.get("max_output", default_max_output)

        if api_key is None:
            raise RuntimeError("OpenAI API key not specified")

        super(Processor, self).__init__(
            **params | {
                "model": model,
                "temperature": temperature,
                "max_output": max_output,
                "base_url": base_url,
            }
        )

        self.default_model = model
        self.temperature = temperature
        self.max_output = max_output

        if base_url:
            self.openai = OpenAI(base_url=base_url, api_key=api_key)
        else:
            self.openai = OpenAI(api_key=api_key)

        logger.info("OpenAI LLM service initialized")

    async def generate_content(self, system, prompt, model=None):

        # Use provided model or fall back to default
        model_name = model or self.default_model

        logger.debug(f"Using model: {model_name}")

        prompt = system + "\n\n" + prompt

        try:

            resp = self.openai.chat.completions.create(
                model=model_name,
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
                ],
                temperature=self.temperature,
                max_tokens=self.max_output,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
                response_format={
                    "type": "text"
                }
            )
            
            inputtokens = resp.usage.prompt_tokens
            outputtokens = resp.usage.completion_tokens
            logger.debug(f"LLM response: {resp.choices[0].message.content}")
            logger.info(f"Input Tokens: {inputtokens}")
            logger.info(f"Output Tokens: {outputtokens}")

            resp = LlmResult(
                text = resp.choices[0].message.content,
                in_token = inputtokens,
                out_token = outputtokens,
                model = model_name
            )

            return resp

        # FIXME: Wrong exception, don't know what this LLM throws
        # for a rate limit
        except RateLimitError:

            # Leave rate limit retries to the base handler
            raise TooManyRequests()

        except Exception as e:

            # Apart from rate limits, treat all exceptions as unrecoverable

            logger.error(f"OpenAI LLM exception ({type(e).__name__}): {e}", exc_info=True)
            raise e

    @staticmethod
    def add_args(parser):

        LlmService.add_args(parser)

        parser.add_argument(
            '-m', '--model',
            default="gpt-3.5-turbo",
            help=f'LLM model (default: GPT-3.5-Turbo)'
        )

        parser.add_argument(
            '-k', '--api-key',
            default=default_api_key,
            help=f'OpenAI API key'
        )

        parser.add_argument(
            '-u', '--url',
            default=default_base_url,
            help=f'OpenAI service base URL'
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
