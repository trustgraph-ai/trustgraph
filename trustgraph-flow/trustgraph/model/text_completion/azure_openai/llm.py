
"""
Simple LLM service, performs text prompt completion using the Azure
OpenAI endpoit service.  Input is prompt, output is response.
"""

import json
from prometheus_client import Histogram
from openai import AzureOpenAI, RateLimitError
import os
import logging

# Module logger
logger = logging.getLogger(__name__)

from .... exceptions import TooManyRequests
from .... base import LlmService, LlmResult

default_ident = "text-completion"

default_temperature = 0.0
default_max_output = 4192
default_api = "2024-12-01-preview"
default_endpoint = os.getenv("AZURE_ENDPOINT", None)
default_token = os.getenv("AZURE_TOKEN", None)
default_model = os.getenv("AZURE_MODEL", None)

class Processor(LlmService):

    def __init__(self, **params):

        temperature = params.get("temperature", default_temperature)
        max_output = params.get("max_output", default_max_output)

        api = params.get("api_version", default_api)
        endpoint = params.get("endpoint", default_endpoint)
        token = params.get("token", default_token)
        model = params.get("model", default_model)

        if endpoint is None:
            raise RuntimeError("Azure endpoint not specified")

        if token is None:
            raise RuntimeError("Azure token not specified")

        super(Processor, self).__init__(
            **params | {
                "temperature": temperature,
                "max_output": max_output,
                "model": model,
                "api": api,
            }
        )

        self.temperature = temperature
        self.max_output = max_output
        self.model = model

        self.openai = AzureOpenAI(
            api_key=token,  
            api_version=api,
            azure_endpoint = endpoint,
        )

    async def generate_content(self, system, prompt):

        prompt = system + "\n\n" + prompt

        try:

            resp = self.openai.chat.completions.create(
                model=self.model,
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
            )

            inputtokens = resp.usage.prompt_tokens
            outputtokens = resp.usage.completion_tokens
            logger.debug(f"LLM response: {resp.choices[0].message.content}")
            logger.info(f"Input Tokens: {inputtokens}")
            logger.info(f"Output Tokens: {outputtokens}")
            logger.debug("Sending response...")

            r = LlmResult(
                text = resp.choices[0].message.content,
                in_token = inputtokens,
                out_token = outputtokens,
                model = self.model
            )

            return r

        except RateLimitError:

            logger.warning("Rate limit exceeded")

            # Leave rate limit retries to the base handler
            raise TooManyRequests()

        except Exception as e:

            # Apart from rate limits, treat all exceptions as unrecoverable
            logger.error(f"Azure OpenAI LLM exception ({type(e).__name__}): {e}", exc_info=True)
            raise e

        logger.debug("Azure OpenAI LLM processing complete")

    @staticmethod
    def add_args(parser):

        LlmService.add_args(parser)

        parser.add_argument(
            '-e', '--endpoint',
            default=default_endpoint,
            help=f'LLM model endpoint'
        )

        parser.add_argument(
            '-a', '--api-version',
            default=default_api,
            help=f'API version (default: {default_api})'
        )

        parser.add_argument(
            '-k', '--token',
            default=default_token,
            help=f'LLM model token'
        )

        parser.add_argument(
            '-m', '--model',
            default=default_model,
            help=f'LLM model'
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
