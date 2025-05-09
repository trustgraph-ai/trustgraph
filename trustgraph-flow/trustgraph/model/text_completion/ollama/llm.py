
"""
Simple LLM service, performs text prompt completion using an Ollama service.
Input is prompt, output is response.
"""

from ollama import Client
import os

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

        self.model = model
        self.llm = Client(host=ollama)

    async def generate_content(self, system, prompt):

        prompt = system + "\n\n" + prompt

        try:

            response = self.llm.generate(self.model, prompt)

            response_text = response['response']
            print("Send response...", flush=True)
            print(response_text, flush=True)

            inputtokens = int(response['prompt_eval_count'])
            outputtokens = int(response['eval_count'])

            resp = LlmResult(
                text = response_text,
                in_token = inputtokens,
                out_token = outputtokens,
                model = self.model
            )

            return resp

        # SLM, presumably no rate limits

        except Exception as e:

            print(f"Exception: {e}")
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
