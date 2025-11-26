
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
from .... base import LlmService, LlmResult, LlmChunk

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
        self.default_model = model

        self.openai = AzureOpenAI(
            api_key=token,  
            api_version=api,
            azure_endpoint = endpoint,
        )

    async def generate_content(self, system, prompt, model=None, temperature=None):

        # Use provided model or fall back to default
        model_name = model or self.default_model
        # Use provided temperature or fall back to default
        effective_temperature = temperature if temperature is not None else self.temperature

        logger.debug(f"Using model: {model_name}")
        logger.debug(f"Using temperature: {effective_temperature}")

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
                temperature=effective_temperature,
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
                model = model_name
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

    def supports_streaming(self):
        """Azure OpenAI supports streaming"""
        return True

    async def generate_content_stream(self, system, prompt, model=None, temperature=None):
        """
        Stream content generation from Azure OpenAI.
        Yields LlmChunk objects with is_final=True on the last chunk.
        """
        # Use provided model or fall back to default
        model_name = model or self.default_model
        # Use provided temperature or fall back to default
        effective_temperature = temperature if temperature is not None else self.temperature

        logger.debug(f"Using model (streaming): {model_name}")
        logger.debug(f"Using temperature: {effective_temperature}")

        prompt = system + "\n\n" + prompt

        try:
            response = self.openai.chat.completions.create(
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
                temperature=effective_temperature,
                max_tokens=self.max_output,
                top_p=1,
                stream=True  # Enable streaming
            )

            # Stream chunks
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield LlmChunk(
                        text=chunk.choices[0].delta.content,
                        in_token=None,
                        out_token=None,
                        model=model_name,
                        is_final=False
                    )

            # Send final chunk
            yield LlmChunk(
                text="",
                in_token=None,
                out_token=None,
                model=model_name,
                is_final=True
            )

            logger.debug("Streaming complete")

        except RateLimitError:
            logger.warning("Rate limit exceeded during streaming")
            raise TooManyRequests()

        except Exception as e:
            logger.error(f"Azure OpenAI streaming exception ({type(e).__name__}): {e}", exc_info=True)
            raise e

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
