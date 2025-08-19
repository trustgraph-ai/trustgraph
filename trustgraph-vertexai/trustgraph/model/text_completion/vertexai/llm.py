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

        self.model = model
        self.is_anthropic = 'claude' in self.model.lower()

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

        # Initialize the appropriate client based on the model type
        if self.is_anthropic:
            logger.info(f"Initializing Anthropic model '{model}' via AnthropicVertex SDK")
            # Initialize AnthropicVertex with credentials if provided, otherwise use ADC
            anthropic_kwargs = {'region': region, 'project_id': project_id}
            if credentials and private_key:  # Pass credentials only if from a file
                anthropic_kwargs['credentials'] = credentials
                logger.debug(f"Using service account credentials for Anthropic model")
            else:
                logger.debug(f"Using Application Default Credentials for Anthropic model")
            
            self.llm = AnthropicVertex(**anthropic_kwargs)
        else:
            # For Gemini models, initialize the Vertex AI SDK
            logger.info(f"Initializing Google model '{model}' via Vertex AI SDK")
            init_kwargs = {'location': region, 'project': project_id}
            if credentials and private_key: # Pass credentials only if from a file
                init_kwargs['credentials'] = credentials
            
            vertexai.init(**init_kwargs)

            self.llm = GenerativeModel(model)

            self.generation_config = GenerationConfig(
                temperature=temperature,
                top_p=1.0,
                top_k=10,
                candidate_count=1,
                max_output_tokens=max_output,
            )

            # Block none doesn't seem to work
            block_level = HarmBlockThreshold.BLOCK_ONLY_HIGH
            #     block_level = HarmBlockThreshold.BLOCK_NONE

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

    async def generate_content(self, system, prompt):

        try:
            if self.is_anthropic:
                # Anthropic API uses a dedicated system prompt
                logger.debug("Sending request to Anthropic model...")
                response = self.llm.messages.create(
                    model=self.model,
                    system=system,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=self.api_params['max_output_tokens'],
                    temperature=self.api_params['temperature'],
                    top_p=self.api_params['top_p'],
                    top_k=self.api_params['top_k'],
                )

                resp = LlmResult(
                    text=response.content[0].text,
                    in_token=response.usage.input_tokens,
                    out_token=response.usage.output_tokens,
                    model=self.model
                )
            else:
                # Gemini API combines system and user prompts
                logger.debug("Sending request to Gemini model...")
                full_prompt = system + "\n\n" + prompt

                response = self.llm.generate_content(
                    full_prompt, generation_config = self.generation_config,
                    safety_settings = self.safety_settings,
                )

                resp = LlmResult(
                    text = response.text,
                    in_token = response.usage_metadata.prompt_token_count,
                    out_token = response.usage_metadata.candidates_token_count,
                    model = self.model
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