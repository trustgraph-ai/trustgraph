
"""
Simple LLM service, performs text prompt completion using OpenAI.
Input is prompt, output is response.
"""

from openai import OpenAI
import os

from .... exceptions import TooManyRequests
from .... base import LlmService, LlmResult

default_ident = "text-completion"

default_subscriber = module
default_model = 'gemma3:9b'
default_url = os.getenv("LMSTUDIO_URL", "http://localhost:1234/")
default_temperature = 0.0
default_max_output = 4096

class Processor(LlmService):

    def __init__(self, **params):
    
        model = params.get("model", default_model)
        url = params.get("url", default_url)
        temperature = params.get("temperature", default_temperature)
        max_output = params.get("max_output", default_max_output)

        super(Processor, self).__init__(
            **params | {
                "model": model,
                "temperature": temperature,
                "max_output": max_output,
                "url" : url,
            }
        )

        self.model = model
        self.url = url + "v1/"
        self.temperature = temperature
        self.max_output = max_output
        self.openai = OpenAI(
            base_url=self.url, 
            api_key = "sk-no-key-required",
        )

        print("Initialised", flush=True)

    async def generate_content(self, system, prompt):

        prompt = system + "\n\n" + prompt

        try:

            print(prompt)

            resp = self.openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ]
                #temperature=self.temperature,
                #max_tokens=self.max_output,
                #top_p=1,
                #frequency_penalty=0,
                #presence_penalty=0,
                #response_format={
                #    "type": "text"
                #}
            )

            print(resp)

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

            return resp

            # SLM, presumably there aren't rate limits

        except Exception as e:

            print(f"Exception: {e}")
            raise e

    @staticmethod
    def add_args(parser):

        LlmService.add_args(parser)

        parser.add_argument(
            '-m', '--model',
            default=default_model,
            help=f'LLM model (default: gemma3:9b)'
        )

        parser.add_argument(
            '-u', '--url',
            default=default_url,
            help=f'LMStudio URL (default: {default_url})'
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
