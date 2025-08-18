
"""
Simple LLM service, performs text prompt completion using Cohere.
Input is prompt, output is response.
"""

import cohere
from prometheus_client import Histogram
import os
import logging

# Module logger
logger = logging.getLogger(__name__)

from .... exceptions import TooManyRequests
from .... base import LlmService, LlmResult

default_ident = "text-completion"

default_model = 'c4ai-aya-23-8b'
default_temperature = 0.0
default_api_key = os.getenv("COHERE_KEY")

class Processor(LlmService):

    def __init__(self, **params):
    
        model = params.get("model", default_model)
        api_key = params.get("api_key", default_api_key)
        temperature = params.get("temperature", default_temperature)

        if api_key is None:
            raise RuntimeError("Cohere API key not specified")

        super(Processor, self).__init__(
            **params | {
                "model": model,
                "temperature": temperature,
            }
        )

        self.model = model
        self.temperature = temperature
        self.cohere = cohere.Client(api_key=api_key)

        logger.info("Cohere LLM service initialized")

    async def generate_content(self, system, prompt):

        try:

            output = self.cohere.chat( 
                model=self.model,
                message=prompt,
                preamble = system,
                temperature=self.temperature,
                chat_history=[],
                prompt_truncation='auto',
                connectors=[]
            )

            resp = output.text
            inputtokens = int(output.meta.billed_units.input_tokens)
            outputtokens = int(output.meta.billed_units.output_tokens)

            logger.debug(f"LLM response: {resp}")
            logger.info(f"Input Tokens: {inputtokens}")
            logger.info(f"Output Tokens: {outputtokens}")

            resp = LlmResult(
                text = resp,
                in_token = inputtokens,
                out_token = outputtokens,
                model = self.model
            )

            return resp

        # FIXME: Wrong exception, don't know what this LLM throws
        # for a rate limit
        except cohere.TooManyRequestsError:

            # Leave rate limit retries to the base handler
            raise TooManyRequests()

        except Exception as e:

            # Apart from rate limits, treat all exceptions as unrecoverable

            logger.error(f"Cohere LLM exception ({type(e).__name__}): {e}", exc_info=True)
            raise e

    @staticmethod
    def add_args(parser):

        LlmService.add_args(parser)

        parser.add_argument(
            '-m', '--model',
            default="c4ai-aya-23-8b",
            help=f'Cohere model (default: c4ai-aya-23-8b)'
        )

        parser.add_argument(
            '-k', '--api-key',
            default=default_api_key,
            help=f'Cohere API key'
        )

        parser.add_argument(
            '-t', '--temperature',
            type=float,
            default=default_temperature,
            help=f'LLM temperature parameter (default: {default_temperature})'
        )

def run():
    
    Processor.launch(default_ident, __doc__)
