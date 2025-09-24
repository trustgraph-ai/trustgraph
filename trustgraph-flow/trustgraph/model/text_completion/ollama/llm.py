
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
default_ollama = os.getenv("OLLAMA_HOST", 'http://localhost:11434')

class Processor(LlmService):

    def __init__(self, **params):

        model = params.get("model", default_model)
        ollama = params.get("ollama", default_ollama)

        super(Processor, self).__init__(
            **params | {
                "model": model,
                "ollama": ollama,
            }
        )

        self.default_model = model
        self.llm = Client(host=ollama)

    async def generate_content(self, system, prompt, model=None):

        # Use provided model or fall back to default
        model_name = model or self.default_model

        logger.debug(f"Using model: {model_name}")

        prompt = system + "\n\n" + prompt

        try:

            response = self.llm.generate(model_name, prompt)

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

def run():

    Processor.launch(default_ident, __doc__)
