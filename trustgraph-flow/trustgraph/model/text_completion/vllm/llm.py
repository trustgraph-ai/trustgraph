
"""
Simple LLM service, performs text prompt completion using vLLM
Input is prompt, output is response.
"""

import os
import aiohttp
import logging

# Module logger
logger = logging.getLogger(__name__)

from .... exceptions import TooManyRequests
from .... base import LlmService, LlmResult, LlmChunk

default_ident = "text-completion"

default_temperature = 0.0
default_max_output = 2048
default_base_url = os.getenv("VLLM_BASE_URL")
default_model = "TheBloke/Mistral-7B-v0.1-AWQ"

if default_base_url == "" or default_base_url is None:
    default_base_url = "http://vllm-service:8899/v1"

class Processor(LlmService):

    def __init__(self, **params):
    
        base_url = params.get("url", default_base_url)
        temperature = params.get("temperature", default_temperature)
        max_output = params.get("max_output", default_max_output)
        model = params.get("model", default_model)

        super(Processor, self).__init__(
            **params | {
                "temperature": temperature,
                "max_output": max_output,
                "url": base_url,
                "model": model,
            }
        )

        self.base_url = base_url
        self.temperature = temperature
        self.max_output = max_output
        self.default_model = model

        self.session = aiohttp.ClientSession()

        logger.info(f"Using vLLM service at {base_url}")
        logger.info("vLLM LLM service initialized")

    async def generate_content(self, system, prompt, model=None, temperature=None):

        # Use provided model or fall back to default
        model_name = model or self.default_model
        # Use provided temperature or fall back to default
        effective_temperature = temperature if temperature is not None else self.temperature

        logger.debug(f"Using model: {model_name}")
        logger.debug(f"Using temperature: {effective_temperature}")

        headers = {
            "Content-Type": "application/json",
        }

        request = {
            "model": model_name,
            "prompt": system + "\n\n" + prompt,
            "max_tokens": self.max_output,
            "temperature": effective_temperature,
        }            

        try:

            url = f"{self.base_url.rstrip('/')}/completions"

            async with self.session.post(
                    url,
                    headers=headers,
                    json=request,
            ) as response:

                if response.status != 200:
                    raise RuntimeError("Bad status: " + str(response.status))

                resp = await response.json()
            
            inputtokens = resp["usage"]["prompt_tokens"]
            outputtokens = resp["usage"]["completion_tokens"]
            ans = resp["choices"][0]["text"]
            logger.info(f"Input Tokens: {inputtokens}")
            logger.info(f"Output Tokens: {outputtokens}")
            logger.debug(f"LLM response: {ans}")

            resp = LlmResult(
                text = ans,
                in_token = inputtokens,
                out_token = outputtokens,
                model = model_name,
            )

            return resp

        # FIXME: Assuming vLLM won't produce rate limits?

        except Exception as e:

            # Apart from rate limits, treat all exceptions as unrecoverable

            logger.error(f"vLLM LLM exception ({type(e).__name__}): {e}", exc_info=True)
            raise e

    def supports_streaming(self):
        """vLLM supports streaming"""
        return True

    async def generate_content_stream(self, system, prompt, model=None, temperature=None):
        """Stream content generation from vLLM"""
        model_name = model or self.default_model
        effective_temperature = temperature if temperature is not None else self.temperature

        logger.debug(f"Using model (streaming): {model_name}")
        logger.debug(f"Using temperature: {effective_temperature}")

        headers = {
            "Content-Type": "application/json",
        }

        request = {
            "model": model_name,
            "prompt": system + "\n\n" + prompt,
            "max_tokens": self.max_output,
            "temperature": effective_temperature,
            "stream": True,
            "stream_options": {"include_usage": True},
        }

        try:
            url = f"{self.base_url.rstrip('/')}/completions"

            total_input_tokens = 0
            total_output_tokens = 0

            async with self.session.post(
                    url,
                    headers=headers,
                    json=request,
            ) as response:

                if response.status != 200:
                    raise RuntimeError("Bad status: " + str(response.status))

                # Parse SSE stream
                async for line in response.content:
                    line = line.decode('utf-8').strip()

                    if not line:
                        continue

                    if line.startswith('data: '):
                        data = line[6:]  # Remove 'data: ' prefix

                        if data == '[DONE]':
                            break

                        try:
                            import json
                            chunk_data = json.loads(data)

                            # Extract text from chunk
                            if 'choices' in chunk_data and len(chunk_data['choices']) > 0:
                                choice = chunk_data['choices'][0]
                                if 'text' in choice and choice['text']:
                                    yield LlmChunk(
                                        text=choice['text'],
                                        in_token=None,
                                        out_token=None,
                                        model=model_name,
                                        is_final=False
                                    )

                            # Capture usage from final chunk
                            if 'usage' in chunk_data and chunk_data['usage']:
                                total_input_tokens = chunk_data['usage'].get('prompt_tokens', 0)
                                total_output_tokens = chunk_data['usage'].get('completion_tokens', 0)

                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse chunk: {data}")
                            continue

                # Send final chunk with token counts
                yield LlmChunk(
                    text="",
                    in_token=total_input_tokens,
                    out_token=total_output_tokens,
                    model=model_name,
                    is_final=True
                )

                logger.debug("Streaming complete")

        except Exception as e:
            logger.error(f"vLLM streaming exception ({type(e).__name__}): {e}", exc_info=True)
            raise e

    @staticmethod
    def add_args(parser):

        LlmService.add_args(parser)

        parser.add_argument(
            '-u', '--url',
            default=default_base_url,
            help=f'vLLM service base URL (default: {default_base_url})'
        )

        parser.add_argument(
            '-m', '--model',
            default=default_model,
            help=f'LLM model (default: {default_model})'
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
