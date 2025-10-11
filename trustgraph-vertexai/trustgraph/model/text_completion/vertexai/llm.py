"""
Simple LLM service, performs text prompt completion using VertexAI on
Google Cloud.   Input is prompt, output is response.
Supports both Google's Gemini models and Anthropic's Claude models.
"""

# 
# Somewhat perplexed by the Google Cloud SDK choices.  We're going off this
# one, which uses the google-cloud-aiplatform library:
#   https://cloud.google.com/python/docs/reference/vertexai/1.94.0
# It seems it is possible to invoke VertexAI from the google-genai
# SDK too:
#   https://googleapis.github.io/python-genai/genai.html#module-genai.client
# That would make this code look very much like the GoogleAIStudio
# code.  And maybe not reliant on the google-cloud-aiplatform library?
#
# This module's imports bring in a lot of libraries.

from google.oauth2 import service_account
import google.auth
import google.api_core.exceptions
import vertexai
import logging

# Why is preview here?
from vertexai.generative_models import (
    Content, FunctionDeclaration, GenerativeModel, GenerationConfig,
    HarmCategory, HarmBlockThreshold, Part, Tool, SafetySetting,
)

# Added for Anthropic model support
from anthropic import AnthropicVertex, RateLimitError

from .... exceptions import TooManyRequests
from .... base import LlmService, LlmResult

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

        # Model client caches
        self.model_clients = {}  # Cache for model instances
        self.generation_configs = {}  # Cache for generation configs (Gemini only)
        self.anthropic_client = None  # Single Anthropic client (handles multiple models)

        # Shared parameters for both model types
        self.api_params = {
            "temperature": temperature,
            "top_p": 1.0,
            "top_k": 32,
            "max_output_tokens": max_output,
        }

        logger.info("Initializing VertexAI...")

        # Unified credential and project ID loading
        if private_key:
            credentials = (
                service_account.Credentials.from_service_account_file(
                    private_key
                )
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

        # Initialize Vertex AI SDK for Gemini models
        init_kwargs = {'location': region, 'project': project_id}
        if credentials and private_key: # Pass credentials only if from a file
            init_kwargs['credentials'] = credentials

        vertexai.init(**init_kwargs)

        # Pre-initialize Anthropic client if needed (single client handles all Claude models)
        if 'claude' in self.default_model.lower():
            self._get_anthropic_client()

        # Safety settings for Gemini models
        block_level = HarmBlockThreshold.BLOCK_ONLY_HIGH
        self.safety_settings = [
            SafetySetting(
                category = HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold = block_level,
            ),
            SafetySetting(
                category = HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold = block_level,
            ),
            SafetySetting(
                category = HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold = block_level,
            ),
            SafetySetting(
                category = HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold = block_level,
            ),
        ]

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

    def _get_gemini_model(self, model_name, temperature=None):
        """Get or create a Gemini model instance"""
        if model_name not in self.model_clients:
            logger.info(f"Creating GenerativeModel instance for '{model_name}'")
            self.model_clients[model_name] = GenerativeModel(model_name)

        # Use provided temperature or fall back to default
        effective_temperature = temperature if temperature is not None else self.temperature

        # Create generation config with the effective temperature
        generation_config = GenerationConfig(
            temperature=effective_temperature,
            top_p=1.0,
            top_k=10,
            candidate_count=1,
            max_output_tokens=self.max_output,
        )

        return self.model_clients[model_name], generation_config

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
                # Gemini API combines system and user prompts
                logger.debug(f"Sending request to Gemini model '{model_name}'...")
                full_prompt = system + "\n\n" + prompt

                llm, generation_config = self._get_gemini_model(model_name, effective_temperature)

                response = llm.generate_content(
                    full_prompt, generation_config = generation_config,
                    safety_settings = self.safety_settings,
                )

                resp = LlmResult(
                    text = response.text,
                    in_token = response.usage_metadata.prompt_token_count,
                    out_token = response.usage_metadata.candidates_token_count,
                    model = model_name
                )

            logger.info(f"Input Tokens: {resp.in_token}")
            logger.info(f"Output Tokens: {resp.out_token}")
            logger.debug("Send response...")

            return resp

        except (google.api_core.exceptions.ResourceExhausted, RateLimitError) as e:
            logger.warning(f"Hit rate limit: {e}")
            # Leave rate limit retries to the base handler
            raise TooManyRequests()

        except Exception as e:
            # Apart from rate limits, treat all exceptions as unrecoverable
            logger.error(f"VertexAI LLM exception: {e}", exc_info=True)
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
