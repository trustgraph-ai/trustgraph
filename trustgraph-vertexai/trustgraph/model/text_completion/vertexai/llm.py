
"""
Simple LLM service, performs text prompt completion using VertexAI on
Google Cloud.   Input is prompt, output is response.
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
import google
import vertexai
import logging

# Why is preview here?
from vertexai.generative_models import (
    Content, FunctionDeclaration, GenerativeModel, GenerationConfig,
    HarmCategory, HarmBlockThreshold, Part, Tool, SafetySetting,
)

from .... exceptions import TooManyRequests
from .... base import LlmService, LlmResult

# Module logger
logger = logging.getLogger(__name__)

default_ident = "text-completion"

default_model = 'gemini-2.0-flash-001'
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
            raise RuntimeError("Private key file not specified")

        super(Processor, self).__init__(**params)

        self.parameters = {
            "temperature": temperature,
            "top_p": 1.0,
            "top_k": 32,
            "candidate_count": 1,
            "max_output_tokens": max_output,
        }

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

        logger.info("Initializing VertexAI...")

        if private_key:
            credentials = (
                service_account.Credentials.from_service_account_file(
                    private_key
                )
            )
        else:
            credentials = None

        if credentials:
            vertexai.init(
                location=region,
                credentials=credentials,
                project=credentials.project_id,
            )
        else:
            vertexai.init(
                location=region
            )

        logger.info(f"Initializing model {model}")
        self.llm = GenerativeModel(model)
        self.model = model

        logger.info("VertexAI initialization complete")

    async def generate_content(self, system, prompt):

        try:

            prompt = system + "\n\n" + prompt

            response = self.llm.generate_content(
                prompt, generation_config = self.generation_config,
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

        except google.api_core.exceptions.ResourceExhausted as e:

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
            help=f'LLM model (default: {default_model})'
        )

        parser.add_argument(
            '-k', '--private-key',
            help=f'Google Cloud private JSON file'
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

