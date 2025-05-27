
"""
Simple LLM service, performs text prompt completion using HuggingFace TGI
Input is prompt, output is response.
"""

import os
import aiohttp

from .... exceptions import TooManyRequests
from .... base import LlmService, LlmResult

default_ident = "text-completion"

default_temperature = 0.0
default_max_output = 2048
default_base_url = os.getenv("TGI_BASE_URL")

if default_base_url == "" or default_base_url is None:
    default_base_url = "http://tgi-service:8899/v1"

class Processor(LlmService):

    def __init__(self, **params):
    
        base_url = params.get("url", default_base_url)
        temperature = params.get("temperature", default_temperature)
        max_output = params.get("max_output", default_max_output)

        super(Processor, self).__init__(
            **params | {
                "temperature": temperature,
                "max_output": max_output,
                "url": base_url,
            }
        )

        self.base_url = base_url
        self.temperature = temperature
        self.max_output = max_output

        self.session = aiohttp.ClientSession()

        print("Using TGI service at", base_url)

        print("Initialised", flush=True)

    async def generate_content(self, system, prompt):

        headers = {
            "Content-Type": "application/json",
        }

        request = {
            "model": "tgi",
            "messages": [
                {
                    "role": "system",
                    "content": system,
                },
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "max_tokens": self.max_output,
            "temperature": self.temperature,
        }            

        try:

            url = f"{self.base_url}/chat/completions"

            async with self.session.post(
                    url,
                    headers=headers,
                    json=request,
            ) as response:

                print("GOT A SRESPONSE")

                if response.status != 200:
                    raise RuntimeError("Bad status: " + str(response.status))

                print("GOT A GOOD STATUS")

                resp = await response.json()

                print("RESPONSE>", resp)
            
            inputtokens = resp["usage"]["prompt_tokens"]
            outputtokens = resp["usage"]["completion_tokens"]
            ans = resp["choices"][0]["message"]["content"]
            print(f"Input Tokens: {inputtokens}", flush=True)
            print(f"Output Tokens: {outputtokens}", flush=True)
            print(ans, flush=True)

            resp = LlmResult(
                text = ans,
                in_token = inputtokens,
                out_token = outputtokens,
                model = "tgi",
            )

            return resp

        # FIXME: Assuming TGI won't produce rate limits?

        except Exception as e:

            # Apart from rate limits, treat all exceptions as unrecoverable

            print(f"Exception: {type(e)} {e}")
            raise e

    @staticmethod
    def add_args(parser):

        LlmService.add_args(parser)

        parser.add_argument(
            '-u', '--url',
            default=default_base_url,
            help=f'TGI service base URL (default: {default_base_url})'
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
