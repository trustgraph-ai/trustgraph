
"""
Simple LLM service, performs text prompt completion using the Azure
serverless endpoint service.  Input is prompt, output is response.
"""

import requests
import json
from prometheus_client import Histogram
import os
import logging

from .... exceptions import TooManyRequests
from .... base import LlmService, LlmResult

# Module logger
logger = logging.getLogger(__name__)

default_ident = "text-completion"

default_temperature = 0.0
default_max_output = 4192
default_model = "AzureAI"
default_endpoint = os.getenv("AZURE_ENDPOINT")
default_token = os.getenv("AZURE_TOKEN")

class Processor(LlmService):

    def __init__(self, **params):

        endpoint = params.get("endpoint", default_endpoint)
        token = params.get("token", default_token)
        temperature = params.get("temperature", default_temperature)
        max_output = params.get("max_output", default_max_output)
        model = default_model

        if endpoint is None:
            raise RuntimeError("Azure endpoint not specified")

        if token is None:
            raise RuntimeError("Azure token not specified")

        super(Processor, self).__init__(
            **params | {
                "endpoint": endpoint,
                "temperature": temperature,
                "max_output": max_output,
                "model": model,
            }
        )

        self.endpoint = endpoint
        self.token = token
        self.temperature = temperature
        self.max_output = max_output
        self.model = model

    def build_prompt(self, system, content):

        data =  {
            "messages": [
                {
                    "role": "system", "content": system
                },
                {
                    "role": "user", "content": content
                }
            ],
            "max_tokens": self.max_output,
            "temperature": self.temperature,
            "top_p": 1
        }

        body = json.dumps(data)

        return body

    def call_llm(self, body):

        url = self.endpoint

        # Replace this with the primary/secondary key, AMLToken, or
        # Microsoft Entra ID token for the endpoint
        api_key = self.token

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }

        resp = requests.post(url, data=body, headers=headers)

        if resp.status_code == 429:
            raise TooManyRequests()

        if resp.status_code != 200:
            raise RuntimeError("LLM failure")

        result = resp.json()

        return result

    async def generate_content(self, system, prompt):

        try:

            prompt = self.build_prompt(
                system,
                prompt
            )

            response = self.call_llm(prompt)

            resp = response['choices'][0]['message']['content']
            inputtokens = response['usage']['prompt_tokens']
            outputtokens = response['usage']['completion_tokens']

            logger.debug(f"LLM response: {resp}")
            logger.info(f"Input Tokens: {inputtokens}")
            logger.info(f"Output Tokens: {outputtokens}")

            logger.debug("Sending response...")

            resp = LlmResult(
                text = resp,
                in_token = inputtokens,
                out_token = outputtokens,
                model = self.model
            )

            return resp

        except TooManyRequests:

            logger.warning("Rate limit exceeded")

            # Leave rate limit retries to the base handler
            raise TooManyRequests()

        except Exception as e:

            # Apart from rate limits, treat all exceptions as unrecoverable

            logger.error(f"Azure LLM exception ({type(e).__name__}): {e}", exc_info=True)
            raise e

        logger.debug("Azure LLM processing complete")

    @staticmethod
    def add_args(parser):

        LlmService.add_args(parser)

        parser.add_argument(
            '-e', '--endpoint',
            default=default_endpoint,
            help=f'LLM model endpoint'
        )

        parser.add_argument(
            '-k', '--token',
            default=default_token,
            help=f'LLM model token'
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
