
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
from .... base import LlmService, LlmResult, LlmChunk

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

        self.default_model = model
        self.temperature = temperature
        self.cohere = cohere.Client(api_key=api_key)

        logger.info("Cohere LLM service initialized")

    async def generate_content(self, system, prompt, model=None, temperature=None):

        # Use provided model or fall back to default
        model_name = model or self.default_model
        # Use provided temperature or fall back to default
        effective_temperature = temperature if temperature is not None else self.temperature

        logger.debug(f"Using model: {model_name}")
        logger.debug(f"Using temperature: {effective_temperature}")

        try:

            output = self.cohere.chat(
                model=model_name,
                message=prompt,
                preamble = system,
                temperature=effective_temperature,
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
                model = model_name
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

    def supports_streaming(self):
        """Cohere supports streaming"""
        return True

    async def generate_content_stream(self, system, prompt, model=None, temperature=None):
        """Stream content generation from Cohere"""
        model_name = model or self.default_model
        effective_temperature = temperature if temperature is not None else self.temperature

        logger.debug(f"Using model (streaming): {model_name}")
        logger.debug(f"Using temperature: {effective_temperature}")

        try:
            stream = self.cohere.chat_stream(
                model=model_name,
                message=prompt,
                preamble=system,
                temperature=effective_temperature,
                chat_history=[],
                prompt_truncation='auto',
                connectors=[]
            )

            total_input_tokens = 0
            total_output_tokens = 0

            for event in stream:
                if event.event_type == "text-generation":
                    if hasattr(event, 'text') and event.text:
                        yield LlmChunk(
                            text=event.text,
                            in_token=None,
                            out_token=None,
                            model=model_name,
                            is_final=False
                        )
                elif event.event_type == "stream-end":
                    # Extract token counts from final event
                    if hasattr(event, 'response') and hasattr(event.response, 'meta'):
                        if hasattr(event.response.meta, 'billed_units'):
                            total_input_tokens = int(event.response.meta.billed_units.input_tokens)
                            total_output_tokens = int(event.response.meta.billed_units.output_tokens)

            # Send final chunk with token counts
            yield LlmChunk(
                text="",
                in_token=total_input_tokens,
                out_token=total_output_tokens,
                model=model_name,
                is_final=True
            )

            logger.debug("Streaming complete")

        except cohere.TooManyRequestsError:
            logger.warning("Rate limit exceeded during streaming")
            raise TooManyRequests()

        except Exception as e:
            logger.error(f"Cohere streaming exception ({type(e).__name__}): {e}", exc_info=True)
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
