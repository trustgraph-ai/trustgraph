"""
Simple LLM service, performs text prompt completion using VertexAI on
Google Cloud.   Input is prompt, output is response.
Supports both Google's Gemini models and Anthropic's Claude models.
"""

#
# Uses the google-genai SDK for Gemini models on Vertex AI:
#   https://googleapis.github.io/python-genai/genai.html#module-genai.client
#

from google.oauth2 import service_account
import google.auth
import logging

from google import genai
from google.genai import types
from google.genai.types import HarmCategory, HarmBlockThreshold
from google.api_core.exceptions import ResourceExhausted

# Added for Anthropic model support
from anthropic import AnthropicVertex, RateLimitError

from .... exceptions import TooManyRequests
from .... base import LlmService, LlmResult, LlmChunk

# Module logger
logger = logging.getLogger(__name__)

default_ident = "text-completion"

default_model = 'gemini-1.5-flash-001'
default_region = 'us-central1'
default_temperature = 0.0
default_max_output = 8192
default_private_key = "private.json"

class Processor(LlmService):

    def __init__(self, **params):

        region = params.get("region", default_region)
        model = params.get("model", default_model)
        private_key = params.get("private_key", default_private_key)
        temperature = params.get("temperature", default_temperature)
        max_output = params.get("max_output", default_max_output)

        if private_key is None:
            logger.warning("Private key file not specified, using Application Default Credentials")

        super(Processor, self).__init__(**params)

        # Store default model and configuration parameters
        self.default_model = model
        self.region = region
        self.temperature = temperature
        self.max_output = max_output
        self.private_key = private_key

        # Anthropic client (handles Claude models)
        self.anthropic_client = None

        # Shared parameters for Anthropic models
        self.api_params = {
            "temperature": temperature,
            "top_p": 1.0,
            "top_k": 32,
            "max_output_tokens": max_output,
        }

        logger.info("Initializing VertexAI...")

        # Unified credential and project ID loading
        if private_key:
            scopes = ["https://www.googleapis.com/auth/cloud-platform"]
            credentials = service_account.Credentials.from_service_account_file(
                private_key,
                scopes=scopes
            )
            project_id = credentials.project_id
        else:
            credentials, project_id = google.auth.default()

        if not project_id:
            raise RuntimeError(
                "Could not determine Google Cloud project ID. "
                "Ensure it's set in your environment or service account."
            )

        # Store credentials and project info for later use
        self.credentials = credentials
        self.project_id = project_id

        # Initialize Google GenAI client for Gemini models
        self.client = genai.Client(
            vertexai=True,
            project=project_id,
            location=region,
            credentials=credentials
        )

        # Pre-initialize Anthropic client if needed (single client handles all Claude models)
        if 'claude' in self.default_model.lower():
            self._get_anthropic_client()

        # Safety settings for Gemini models
        block_level = HarmBlockThreshold.BLOCK_ONLY_HIGH
        self.safety_settings = [
            types.SafetySetting(
                category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=block_level,
            ),
            types.SafetySetting(
                category=HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=block_level,
            ),
            types.SafetySetting(
                category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=block_level,
            ),
            types.SafetySetting(
                category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=block_level,
            ),
        ]

        # Cache for generation configs
        self.generation_configs = {}

        logger.info("VertexAI initialization complete")

    def _get_anthropic_client(self):
        """Get or create the Anthropic client (single client for all Claude models)"""
        if self.anthropic_client is None:
            logger.info(f"Initializing AnthropicVertex client")
            anthropic_kwargs = {'region': self.region, 'project_id': self.project_id}
            if self.credentials and self.private_key:  # Pass credentials only if from a file
                anthropic_kwargs['credentials'] = self.credentials
                logger.debug(f"Using service account credentials for Anthropic models")
            else:
                logger.debug(f"Using Application Default Credentials for Anthropic models")

            self.anthropic_client = AnthropicVertex(**anthropic_kwargs)

        return self.anthropic_client

    def _get_or_create_config(self, model_name, temperature=None):
        """Get or create generation config with dynamic temperature"""
        # Use provided temperature or fall back to default
        effective_temperature = temperature if temperature is not None else self.temperature

        # Create cache key that includes temperature to avoid conflicts
        cache_key = f"{model_name}:{effective_temperature}"

        if cache_key not in self.generation_configs:
            logger.info(f"Creating generation config for '{model_name}' with temperature {effective_temperature}")
            self.generation_configs[cache_key] = types.GenerateContentConfig(
                temperature=effective_temperature,
                top_p=1.0,
                top_k=40,
                max_output_tokens=self.max_output,
                response_mime_type="text/plain",
                safety_settings=self.safety_settings,
            )

        return self.generation_configs[cache_key]

    async def generate_content(self, system, prompt, model=None, temperature=None):

        # Use provided model or fall back to default
        model_name = model or self.default_model
        # Use provided temperature or fall back to default
        effective_temperature = temperature if temperature is not None else self.temperature

        logger.debug(f"Using model: {model_name}")
        logger.debug(f"Using temperature: {effective_temperature}")

        try:
            if 'claude' in model_name.lower():
                # Anthropic API uses a dedicated system prompt
                logger.debug(f"Sending request to Anthropic model '{model_name}'...")
                client = self._get_anthropic_client()

                response = client.messages.create(
                    model=model_name,
                    system=system,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=self.api_params['max_output_tokens'],
                    temperature=effective_temperature,
                    top_p=self.api_params['top_p'],
                    top_k=self.api_params['top_k'],
                )

                resp = LlmResult(
                    text=response.content[0].text,
                    in_token=response.usage.input_tokens,
                    out_token=response.usage.output_tokens,
                    model=model_name
                )
            else:
                # Gemini API using google-genai SDK
                logger.debug(f"Sending request to Gemini model '{model_name}'...")

                generation_config = self._get_or_create_config(model_name, effective_temperature)
                # Set system instruction per request (can't be cached)
                generation_config.system_instruction = system

                response = self.client.models.generate_content(
                    model=model_name,
                    config=generation_config,
                    contents=prompt,
                )

                resp = LlmResult(
                    text=response.text,
                    in_token=int(response.usage_metadata.prompt_token_count),
                    out_token=int(response.usage_metadata.candidates_token_count),
                    model=model_name
                )

            logger.info(f"Input Tokens: {resp.in_token}")
            logger.info(f"Output Tokens: {resp.out_token}")
            logger.debug("Send response...")

            return resp

        except (ResourceExhausted, RateLimitError) as e:
            logger.warning(f"Hit rate limit: {e}")
            # Leave rate limit retries to the base handler
            raise TooManyRequests()

        except Exception as e:
            # Apart from rate limits, treat all exceptions as unrecoverable
            logger.error(f"VertexAI LLM exception: {e}", exc_info=True)
            raise e

    def supports_streaming(self):
        """VertexAI supports streaming for both Gemini and Claude models"""
        return True

    async def generate_content_stream(self, system, prompt, model=None, temperature=None):
        """
        Stream content generation from VertexAI (Gemini or Claude).
        Yields LlmChunk objects with is_final=True on the last chunk.
        """
        # Use provided model or fall back to default
        model_name = model or self.default_model
        # Use provided temperature or fall back to default
        effective_temperature = temperature if temperature is not None else self.temperature

        logger.debug(f"Using model (streaming): {model_name}")
        logger.debug(f"Using temperature: {effective_temperature}")

        try:
            if 'claude' in model_name.lower():
                # Claude/Anthropic streaming
                logger.debug(f"Streaming request to Anthropic model '{model_name}'...")
                client = self._get_anthropic_client()

                total_in_tokens = 0
                total_out_tokens = 0

                with client.messages.stream(
                    model=model_name,
                    system=system,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=self.api_params['max_output_tokens'],
                    temperature=effective_temperature,
                    top_p=self.api_params['top_p'],
                    top_k=self.api_params['top_k'],
                ) as stream:
                    # Stream text chunks
                    for text in stream.text_stream:
                        yield LlmChunk(
                            text=text,
                            in_token=None,
                            out_token=None,
                            model=model_name,
                            is_final=False
                        )

                    # Get final message with token counts
                    final_message = stream.get_final_message()
                    total_in_tokens = final_message.usage.input_tokens
                    total_out_tokens = final_message.usage.output_tokens

                # Send final chunk with token counts
                yield LlmChunk(
                    text="",
                    in_token=total_in_tokens,
                    out_token=total_out_tokens,
                    model=model_name,
                    is_final=True
                )

                logger.info(f"Input Tokens: {total_in_tokens}")
                logger.info(f"Output Tokens: {total_out_tokens}")

            else:
                # Gemini streaming using google-genai SDK
                logger.debug(f"Streaming request to Gemini model '{model_name}'...")

                generation_config = self._get_or_create_config(model_name, effective_temperature)
                generation_config.system_instruction = system

                response = self.client.models.generate_content_stream(
                    model=model_name,
                    config=generation_config,
                    contents=prompt,
                )

                total_in_tokens = 0
                total_out_tokens = 0

                # Stream chunks
                for chunk in response:
                    if chunk.text:
                        yield LlmChunk(
                            text=chunk.text,
                            in_token=None,
                            out_token=None,
                            model=model_name,
                            is_final=False
                        )

                    # Accumulate token counts if available
                    if hasattr(chunk, 'usage_metadata') and chunk.usage_metadata:
                        if hasattr(chunk.usage_metadata, 'prompt_token_count'):
                            total_in_tokens = chunk.usage_metadata.prompt_token_count
                        if hasattr(chunk.usage_metadata, 'candidates_token_count'):
                            total_out_tokens = chunk.usage_metadata.candidates_token_count

                # Send final chunk with token counts
                yield LlmChunk(
                    text="",
                    in_token=total_in_tokens,
                    out_token=total_out_tokens,
                    model=model_name,
                    is_final=True
                )

                logger.info(f"Input Tokens: {total_in_tokens}")
                logger.info(f"Output Tokens: {total_out_tokens}")

        except (ResourceExhausted, RateLimitError) as e:
            logger.warning(f"Hit rate limit during streaming: {e}")
            raise TooManyRequests()

        except Exception as e:
            logger.error(f"VertexAI streaming exception: {e}", exc_info=True)
            raise e

    @staticmethod
    def add_args(parser):

        LlmService.add_args(parser)

        parser.add_argument(
            '-m', '--model',
            default=default_model,
            help=f'LLM model (e.g., gemini-1.5-flash-001, claude-3-sonnet@20240229) (default: {default_model})'
        )

        parser.add_argument(
            '-k', '--private-key',
            help=f'Google Cloud private JSON file (optional, uses ADC if not provided)'
        )

        parser.add_argument(
            '-r', '--region',
            default=default_region,
            help=f'Google Cloud region (default: {default_region})',
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
