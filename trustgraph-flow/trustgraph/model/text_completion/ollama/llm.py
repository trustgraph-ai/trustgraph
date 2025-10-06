
"""
Simple LLM service, performs text prompt completion using an Ollama service.
Input is prompt, output is response.
"""

from ollama import Client
import os
import logging

# Module logger
logger = logging.getLogger(__name__)

from .... exceptions import TooManyRequests
from .... base import LlmService, LlmResult

default_ident = "text-completion"

default_model = 'gemma2:9b'
default_temperature = 0.0
default_ollama = os.getenv("OLLAMA_HOST", 'http://localhost:11434')

class Processor(LlmService):

    def __init__(self, **params):

        model = params.get("model", default_model)
        temperature = params.get("temperature", default_temperature)
        ollama = params.get("ollama", default_ollama)

        super(Processor, self).__init__(
            **params | {
                "model": model,
                "temperature": temperature,
                "ollama": ollama,
            }
        )

        self.default_model = model
        self.temperature = temperature
        self.llm = Client(host=ollama)

    async def generate_content(self, system, prompt, model=None, temperature=None):

        # Use provided model or fall back to default
        model_name = model or self.default_model
        # Use provided temperature or fall back to default
        effective_temperature = temperature if temperature is not None else self.temperature

        logger.debug(f"Using model: {model_name}")
        logger.debug(f"Using temperature: {effective_temperature}")

        prompt = system + "\n\n" + prompt

        try:

            response = self.llm.generate(model_name, prompt, options={'temperature': effective_temperature})

            response_text = response['response']
            logger.debug("Sending response...")
            logger.debug(f"LLM response: {response_text}")

            inputtokens = int(response['prompt_eval_count'])
            outputtokens = int(response['eval_count'])

            resp = LlmResult(
                text = response_text,
                in_token = inputtokens,
                out_token = outputtokens,
                model = model_name
            )

            return resp

        # SLM, presumably no rate limits

        except Exception as e:

            logger.error(f"Ollama LLM exception ({type(e).__name__}): {e}", exc_info=True)
            raise e

    @staticmethod
    def add_args(parser):

        LlmService.add_args(parser)

        parser.add_argument(
            '-m', '--model',
            default="gemma2",
            help=f'LLM model (default: {default_model})'
        )

        parser.add_argument(
            '-r', '--ollama',
            default=default_ollama,
            help=f'ollama (default: {default_ollama})'
        )

        parser.add_argument(
            '-t', '--temperature',
            type=float,
            default=default_temperature,
            help=f'LLM temperature parameter (default: {default_temperature})'
        )

def run():

    Processor.launch(default_ident, __doc__)
