
"""
Simple LLM service, performs text prompt completion using GoogleAIStudio.
Input is prompt, output is response.
"""

#
# Using this SDK:
#   https://googleapis.github.io/python-genai/genai.html#module-genai.client
#
# Seems to have simpler dependencies on the 'VertexAI' service, which
# TrustGraph implements in the trustgraph-vertexai package.
#

from google import genai
from google.genai import types
from google.genai.types import HarmCategory, HarmBlockThreshold
from google.genai.errors import ClientError
from google.api_core.exceptions import ResourceExhausted
import os
import logging

# Module logger
logger = logging.getLogger(__name__)

from .... exceptions import TooManyRequests
from .... base import LlmService, LlmResult, LlmChunk

default_ident = "text-completion"

default_model = 'gemini-2.0-flash-001'
default_temperature = 0.0
default_max_output = 8192
default_api_key = os.getenv("GOOGLE_AI_STUDIO_KEY")

class Processor(LlmService):

    def __init__(self, **params):
    
        model = params.get("model", default_model)
        api_key = params.get("api_key", default_api_key)
        temperature = params.get("temperature", default_temperature)
        max_output = params.get("max_output", default_max_output)

        if api_key is None:
            raise RuntimeError("Google AI Studio API key not specified")

        super(Processor, self).__init__(
            **params | {
                "model": model,
                "temperature": temperature,
                "max_output": max_output,
            }
        )

        self.client = genai.Client(api_key=api_key)
        self.default_model = model
        self.temperature = temperature
        self.max_output = max_output

        # Cache for generation configs per model
        self.generation_configs = {}

        block_level = HarmBlockThreshold.BLOCK_ONLY_HIGH

        self.safety_settings = [
            types.SafetySetting(
                category = HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold = block_level,
            ),
            types.SafetySetting(
                category = HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold = block_level,
            ),
            types.SafetySetting(
                category = HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold = block_level,
            ),
            types.SafetySetting(
                category = HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold = block_level,
            ),
            # There is a documentation conflict on whether or not
            # CIVIC_INTEGRITY is a valid category
            # HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY: block_level,
        ]

        logger.info("GoogleAIStudio LLM service initialized")

    def _get_or_create_config(self, model_name, temperature=None):
        """Get or create generation config with dynamic temperature"""
        # Use provided temperature or fall back to default
        effective_temperature = temperature if temperature is not None else self.temperature

        # Create cache key that includes temperature to avoid conflicts
        cache_key = f"{model_name}:{effective_temperature}"

        if cache_key not in self.generation_configs:
            logger.info(f"Creating generation config for '{model_name}' with temperature {effective_temperature}")
            self.generation_configs[cache_key] = types.GenerateContentConfig(
                temperature = effective_temperature,
                top_p = 1,
                top_k = 40,
                max_output_tokens = self.max_output,
                response_mime_type = "text/plain",
                safety_settings = self.safety_settings,
            )

        return self.generation_configs[cache_key]

    async def generate_content(self, system, prompt, model=None, temperature=None):

        # Use provided model or fall back to default
        model_name = model or self.default_model
        # Use provided temperature or fall back to default
        effective_temperature = temperature if temperature is not None else self.temperature

        logger.debug(f"Using model: {model_name}")
        logger.debug(f"Using temperature: {effective_temperature}")

        generation_config = self._get_or_create_config(model_name, effective_temperature)
        # Set system instruction per request (can't be cached)
        generation_config.system_instruction = system

        try:

            response = self.client.models.generate_content(
                model=model_name,
                config=generation_config,
                contents=prompt,
            )

            resp = response.text
            inputtokens = int(response.usage_metadata.prompt_token_count)
            outputtokens = int(response.usage_metadata.candidates_token_count)
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

        except ResourceExhausted as e:

            logger.warning("Rate limit exceeded")

            # Leave rate limit retries to the default handler
            raise TooManyRequests()

        except ClientError as e:
            # google-genai SDK throws ClientError for 4xx errors
            if e.code == 429:
                logger.warning(f"Rate limit exceeded (ClientError 429): {e}")
                raise TooManyRequests()
            # Other client errors are unrecoverable
            logger.error(f"GoogleAIStudio ClientError: {e}", exc_info=True)
            raise e

        except Exception as e:

            # Apart from rate limits, treat all exceptions as unrecoverable

            logger.error(f"GoogleAIStudio LLM exception ({type(e).__name__}): {e}", exc_info=True)
            raise e

    def supports_streaming(self):
        """Google AI Studio supports streaming"""
        return True

    async def generate_content_stream(self, system, prompt, model=None, temperature=None):
        """Stream content generation from Google AI Studio"""
        model_name = model or self.default_model
        effective_temperature = temperature if temperature is not None else self.temperature

        logger.debug(f"Using model (streaming): {model_name}")
        logger.debug(f"Using temperature: {effective_temperature}")

        generation_config = self._get_or_create_config(model_name, effective_temperature)
        generation_config.system_instruction = system

        try:
            response = self.client.models.generate_content_stream(
                model=model_name,
                config=generation_config,
                contents=prompt,
            )

            total_input_tokens = 0
            total_output_tokens = 0

            for chunk in response:
                if hasattr(chunk, 'text') and chunk.text:
                    yield LlmChunk(
                        text=chunk.text,
                        in_token=None,
                        out_token=None,
                        model=model_name,
                        is_final=False
                    )

                # Accumulate token counts if available
                if hasattr(chunk, 'usage_metadata'):
                    if hasattr(chunk.usage_metadata, 'prompt_token_count'):
                        total_input_tokens = int(chunk.usage_metadata.prompt_token_count)
                    if hasattr(chunk.usage_metadata, 'candidates_token_count'):
                        total_output_tokens = int(chunk.usage_metadata.candidates_token_count)

            # Send final chunk with token counts
            yield LlmChunk(
                text="",
                in_token=total_input_tokens,
                out_token=total_output_tokens,
                model=model_name,
                is_final=True
            )

            logger.debug("Streaming complete")

        except ResourceExhausted:
            logger.warning("Rate limit exceeded during streaming")
            raise TooManyRequests()

        except ClientError as e:
            # google-genai SDK throws ClientError for 4xx errors
            if e.code == 429:
                logger.warning(f"Rate limit exceeded during streaming (ClientError 429): {e}")
                raise TooManyRequests()
            # Other client errors are unrecoverable
            logger.error(f"GoogleAIStudio streaming ClientError: {e}", exc_info=True)
            raise e

        except Exception as e:
            logger.error(f"GoogleAIStudio streaming exception ({type(e).__name__}): {e}", exc_info=True)
            raise e

    @staticmethod
    def add_args(parser):

        LlmService.add_args(parser)

        parser.add_argument(
            '-m', '--model',
            default=default_model,
            help=f'LLM model (default: {default_model})'
        )

        parser.add_argument(
            '-k', '--api-key',
            default=default_api_key,
            help=f'GoogleAIStudio API key'
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

