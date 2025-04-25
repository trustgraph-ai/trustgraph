
"""
Simple LLM service, performs text prompt completion using Mistral.
Input is prompt, output is response.
"""

from mistralai import Mistral
import os

from .... exceptions import TooManyRequests
from .... base import LlmService, LlmResult

default_ident = "text-completion"

default_model = 'ministral-8b-latest'
default_temperature = 0.0
default_max_output = 4096
default_api_key = os.getenv("MISTRAL_TOKEN")

class Processor(LlmService):

    def __init__(self, **params):
    
        model = params.get("model", default_model)
        api_key = params.get("api_key", default_api_key)
        temperature = params.get("temperature", default_temperature)
        max_output = params.get("max_output", default_max_output)

        if api_key is None:
            raise RuntimeError("Mistral API key not specified")

        super(Processor, self).__init__(
            **params | {
                "model": model,
                "temperature": temperature,
                "max_output": max_output,
            }
        )

        self.model = model
        self.temperature = temperature
        self.max_output = max_output
        self.mistral = Mistral(api_key=api_key)

        print("Initialised", flush=True)

    async def generate_content(self, system, prompt):

        prompt = system + "\n\n" + prompt

        try:

            resp = self.mistral.chat.complete(
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
                frequency_penalty=0,
                presence_penalty=0,
                response_format={
                    "type": "text"
                }
            )
            
            inputtokens = resp.usage.prompt_tokens
            outputtokens = resp.usage.completion_tokens
            print(resp.choices[0].message.content, flush=True)
            print(f"Input Tokens: {inputtokens}", flush=True)
            print(f"Output Tokens: {outputtokens}", flush=True)

            resp = LlmResult(
                text = resp.choices[0].message.content,
                in_token = inputtokens,
                out_token = outputtokens,
                model = self.model
            )

        # FIXME: Wrong exception.  The MistralAI library has retry logic
        # so retry-able errors are retried transparently.  It means we
        # don't get rate limit events.

        # We could choose to turn off retry and handle all that here
        # or subclass BackoffStrategy to keep the retry logic, but
        # get the events out.

#        except Mistral.RateLimitError:

#            # Leave rate limit retries to the base handler
#            raise TooManyRequests()

        except Exception as e:

            # Apart from rate limits, treat all exceptions as unrecoverable

            print(f"Exception: {e}")
            raise e

    @staticmethod
    def add_args(parser):

        LlmService.add_args(parser)

        parser.add_argument(
            '-m', '--model',
            default=default_model,
            help=f'LLM model (default: ministral-8b-latest)'
        )

        parser.add_argument(
            '-k', '--api-key',
            default=default_api_key,
            help=f'Mistral API Key'
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
