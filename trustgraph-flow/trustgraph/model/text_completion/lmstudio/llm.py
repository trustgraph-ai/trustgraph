
"""
Simple LLM service, performs text prompt completion using OpenAI.
Input is prompt, output is response.
"""

from openai import OpenAI
import os
import logging

# Module logger
logger = logging.getLogger(__name__)

from .... exceptions import TooManyRequests
from .... base import LlmService, LlmResult

default_ident = "text-completion"

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

        self.default_model = model
        self.url = url + "v1/"
        self.temperature = temperature
        self.max_output = max_output
        self.openai = OpenAI(
            base_url=self.url, 
            api_key = "sk-no-key-required",
        )

        logger.info("LMStudio LLM service initialized")

    async def generate_content(self, system, prompt, model=None, temperature=None):

        # Use provided model or fall back to default
        model_name = model or self.default_model
        # Use provided temperature or fall back to default
        effective_temperature = temperature if temperature is not None else self.temperature

        logger.debug(f"Using model: {model_name}")
        logger.debug(f"Using temperature: {effective_temperature}")

        prompt = system + "\n\n" + prompt

        try:

            logger.debug(f"Prompt: {prompt}")

            resp = self.openai.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=effective_temperature,
                max_tokens=self.max_output,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
                response_format={
                    "type": "text"
                }
            )

            logger.debug(f"Full response: {resp}")

            inputtokens = resp.usage.prompt_tokens
            outputtokens = resp.usage.completion_tokens

            logger.debug(f"LLM response: {resp.choices[0].message.content}")
            logger.info(f"Input Tokens: {inputtokens}")
            logger.info(f"Output Tokens: {outputtokens}")

            resp = LlmResult(
                text = resp.choices[0].message.content,
                in_token = inputtokens,
                out_token = outputtokens,
                model = model_name
            )

            return resp

            # SLM, presumably there aren't rate limits

        except Exception as e:

            logger.error(f"LMStudio LLM exception ({type(e).__name__}): {e}", exc_info=True)
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
