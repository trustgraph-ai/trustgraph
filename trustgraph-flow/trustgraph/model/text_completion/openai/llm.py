
"""
Simple LLM service, performs text prompt completion using OpenAI.
Input is prompt, output is response.
"""

from openai import OpenAI, RateLimitError, InternalServerError
import os
import logging

from .... exceptions import TooManyRequests, LlmError
from .... base import LlmService, LlmResult, LlmChunk
from . variants import get_variant, DEFAULT_VARIANT, VARIANTS

# Module logger
logger = logging.getLogger(__name__)

default_ident = "text-completion"

default_model = 'gpt-3.5-turbo'
default_temperature = 0.0
default_max_output = 4096
default_api_key = os.getenv("OPENAI_TOKEN")
default_base_url = os.getenv("OPENAI_BASE_URL")
default_thinking = "off"

if default_base_url is None or default_base_url == "":
    default_base_url = "https://api.openai.com/v1"

class Processor(LlmService):

    def __init__(self, **params):

        model = params.get("model", default_model)
        api_key = params.get("api_key", default_api_key)
        base_url = params.get("url", default_base_url)
        temperature = params.get("temperature", default_temperature)
        max_output = params.get("max_output", default_max_output)
        thinking = params.get("thinking", default_thinking)
        variant_name = params.get("variant", DEFAULT_VARIANT)

        if not api_key:
            api_key = "not-set"

        self.variant = get_variant(variant_name)
        self.thinking = thinking

        super(Processor, self).__init__(
            **params | {
                "model": model,
                "temperature": temperature,
                "max_output": max_output,
                "base_url": base_url,
            }
        )

        self.default_model = model
        self.temperature = temperature
        self.max_output = max_output

        if base_url:
            self.openai = OpenAI(base_url=base_url, api_key=api_key)
        else:
            self.openai = OpenAI(api_key=api_key)

        logger.info(
            f"OpenAI LLM service initialized "
            f"(variant={self.variant.name}, thinking={self.thinking})"
        )

    def _build_kwargs(self, model_name, temperature):
        """Build API call kwargs using the active variant."""
        return self.variant.completion_kwargs(
            max_output=self.max_output,
            temperature=temperature,
            thinking=self.thinking,
        )

    def _extract_content(self, message):
        """Extract visible content from a response message."""
        if hasattr(self.variant, "extract_content"):
            return self.variant.extract_content(message)
        return message.content

    async def generate_content(self, system, prompt, model=None, temperature=None):

        model_name = model or self.default_model
        effective_temperature = temperature if temperature is not None else self.temperature

        logger.debug(f"Using model: {model_name}")
        logger.debug(f"Using temperature: {effective_temperature}")

        prompt = system + "\n\n" + prompt

        try:

            api_kwargs = self._build_kwargs(model_name, effective_temperature)

            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]

            resp = self.variant.create_completion(
                self.openai, model_name, messages, **api_kwargs,
            )

            inputtokens = resp.usage.prompt_tokens
            outputtokens = resp.usage.completion_tokens

            content = self._extract_content(resp.choices[0].message)
            thinking = self.variant.extract_thinking(resp.choices[0].message)

            logger.debug(f"LLM response: {content}")
            if thinking:
                logger.debug(f"LLM thinking: {thinking[:200]}...")
            logger.info(f"Input Tokens: {inputtokens}")
            logger.info(f"Output Tokens: {outputtokens}")

            resp = LlmResult(
                text = content,
                in_token = inputtokens,
                out_token = outputtokens,
                model = model_name
            )

            return resp

        except RateLimitError as e:
            try:
                body = getattr(e, 'body', {})
                if isinstance(body, dict):
                    code = body.get('error', {}).get('code')
                    if code in ('insufficient_quota', 'invalid_api_key', 'account_deactivated'):
                        raise RuntimeError(f"OpenAI unrecoverable error: {code} - {body['error'].get('message', '')}")
            except (ValueError, KeyError, TypeError, AttributeError):
                pass
            # Leave rate limit retries to the base handler
            raise TooManyRequests()

        except InternalServerError:
            # Treat 503 as a retryable LlmError
            raise LlmError()

        except Exception as e:

            # Apart from rate limits, treat all exceptions as unrecoverable

            logger.error(f"OpenAI LLM exception ({type(e).__name__}): {e}", exc_info=True)
            raise e

    def supports_streaming(self):
        """OpenAI supports streaming"""
        return True

    async def generate_content_stream(self, system, prompt, model=None, temperature=None):
        """
        Stream content generation from OpenAI.
        Yields LlmChunk objects with is_final=True on the last chunk.
        """
        model_name = model or self.default_model
        effective_temperature = temperature if temperature is not None else self.temperature

        logger.debug(f"Using model (streaming): {model_name}")
        logger.debug(f"Using temperature: {effective_temperature}")

        prompt = system + "\n\n" + prompt

        try:
            api_kwargs = self._build_kwargs(model_name, effective_temperature)

            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]

            total_input_tokens = 0
            total_output_tokens = 0

            async for chunk in self.variant.create_completion_stream(
                self.openai, model_name, messages, **api_kwargs,
            ):
                if chunk.choices and chunk.choices[0].delta.content:
                    yield LlmChunk(
                        text=chunk.choices[0].delta.content,
                        in_token=None,
                        out_token=None,
                        model=model_name,
                        is_final=False
                    )

                # Capture usage from final chunk
                if chunk.usage:
                    total_input_tokens = chunk.usage.prompt_tokens
                    total_output_tokens = chunk.usage.completion_tokens

            # Send final chunk with token counts
            yield LlmChunk(
                text="",
                in_token=total_input_tokens,
                out_token=total_output_tokens,
                model=model_name,
                is_final=True
            )

            logger.debug("Streaming complete")

        except RateLimitError as e:
            try:
                body = getattr(e, 'body', {})
                if isinstance(body, dict):
                    code = body.get('error', {}).get('code')
                    if code in ('insufficient_quota', 'invalid_api_key', 'account_deactivated'):
                        logger.warning(f"Hit unrecoverable rate limit error during streaming: {code}")
                        raise RuntimeError(f"OpenAI unrecoverable error: {code} - {body['error'].get('message', '')}")
            except (ValueError, KeyError, TypeError, AttributeError):
                pass
            logger.warning("Hit rate limit during streaming")
            raise TooManyRequests()

        except InternalServerError:
            logger.warning("Hit internal server error during streaming")
            raise LlmError()

        except Exception as e:
            logger.error(f"OpenAI streaming exception ({type(e).__name__}): {e}", exc_info=True)
            raise e

    @staticmethod
    def add_args(parser):

        LlmService.add_args(parser)

        parser.add_argument(
            '-m', '--model',
            default="gpt-3.5-turbo",
            help=f'LLM model (default: GPT-3.5-Turbo)'
        )

        parser.add_argument(
            '-k', '--api-key',
            default=default_api_key,
            help=f'OpenAI API key'
        )

        parser.add_argument(
            '-u', '--url',
            default=default_base_url,
            help=f'OpenAI service base URL'
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

        parser.add_argument(
            '--thinking',
            choices=["off", "low", "medium", "high"],
            default=default_thinking,
            help=f'Thinking/reasoning effort level (default: {default_thinking})'
        )

        parser.add_argument(
            '--variant',
            choices=sorted(VARIANTS.keys()),
            default=DEFAULT_VARIANT,
            help=f'API variant (default: {DEFAULT_VARIANT})'
        )

def run():

    Processor.launch(default_ident, __doc__)
