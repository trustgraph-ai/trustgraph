
"""
Simple LLM service, performs text prompt completion using AWS Bedrock.
Input is prompt, output is response. Mistral is default.
"""

import boto3
import json
import os
import enum
import logging

from .... exceptions import TooManyRequests
from .... base import LlmService, LlmResult, LlmChunk

# Module logger
logger = logging.getLogger(__name__)

default_ident = "text-completion"

default_model = 'mistral.mistral-large-2407-v1:0'
default_temperature = 0.0
default_max_output = 2048

# Actually, these could all just be None, no need to get environment
# variables, as Boto3 would pick all these up if not passed in as args
default_access_key_id = os.getenv("AWS_ACCESS_KEY_ID", None)
default_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY", None)
default_session_token = os.getenv("AWS_SESSION_TOKEN", None)
default_profile = os.getenv("AWS_PROFILE", None)
default_region = os.getenv("AWS_DEFAULT_REGION", None)

# Variant API handling depends on the model type

class ModelHandler:
    def __init__(self):
        self.temperature = default_temperature
        self.max_output = default_max_output
    def set_temperature(self, temperature):
        self.temperature = temperature
    def set_max_output(self, max_output):
        self.max_output = max_output
    def encode_request(self, system, prompt):
        raise RuntimeError("format_request not implemented")
    def decode_response(self, response):
        raise RuntimeError("format_request not implemented")
    def decode_stream_chunk(self, chunk):
        raise RuntimeError("decode_stream_chunk not implemented")

class Mistral(ModelHandler):
    def __init__(self):
        pass
    def encode_request(self, system, prompt):
        return json.dumps({
            "prompt": f"{system}\n\n{prompt}",
            "max_tokens": self.max_output,
            "temperature": self.temperature,
        })
    def decode_response(self, response):
        response_body = json.loads(response.get("body").read())
        return response_body['outputs'][0]['text']
    def decode_stream_chunk(self, chunk):
        chunk_obj = json.loads(chunk.get('chunk').get('bytes').decode())
        if 'outputs' in chunk_obj and len(chunk_obj['outputs']) > 0:
            return chunk_obj['outputs'][0].get('text', '')
        return ''

# Llama 3
class Meta(ModelHandler):
    def __init__(self):
        pass
    def encode_request(self, system, prompt):
        return json.dumps({
            "prompt": f"{system}\n\n{prompt}",
            "max_gen_len": self.max_output,
            "temperature": self.temperature,
        })
    def decode_response(self, response):
        model_response = json.loads(response["body"].read())
        return model_response["generation"]
    def decode_stream_chunk(self, chunk):
        chunk_obj = json.loads(chunk.get('chunk').get('bytes').decode())
        return chunk_obj.get('generation', '')

class Anthropic(ModelHandler):
    def __init__(self):
        pass
    def encode_request(self, system, prompt):
        return json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self.max_output,
            "temperature": self.temperature,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"{system}\n\n{prompt}",
                        }
                    ]
                }
            ]
        })
    def decode_response(self, response):
        model_response = json.loads(response["body"].read())
        return model_response['content'][0]['text']
    def decode_stream_chunk(self, chunk):
        chunk_obj = json.loads(chunk.get('chunk').get('bytes').decode())
        if chunk_obj.get('type') == 'content_block_delta':
            if 'delta' in chunk_obj and 'text' in chunk_obj['delta']:
                return chunk_obj['delta']['text']
        return ''

class Ai21(ModelHandler):
    def __init__(self):
        pass
    def encode_request(self, system, prompt):
        return json.dumps({
            "max_tokens": self.max_output,
            "temperature": self.temperature,
            "messages": [
                {
                    "role": "user",
                    "content": f"{system}\n\n{prompt}"
                }
            ]
        })
    def decode_response(self, response):
        content = response['body'].read()
        content_str = content.decode('utf-8')
        content_json = json.loads(content_str)
        return content_json['choices'][0]['message']['content']
    def decode_stream_chunk(self, chunk):
        chunk_obj = json.loads(chunk.get('chunk').get('bytes').decode())
        if 'choices' in chunk_obj and len(chunk_obj['choices']) > 0:
            delta = chunk_obj['choices'][0].get('delta', {})
            return delta.get('content', '')
        return ''

class Cohere(ModelHandler):
    def encode_request(self, system, prompt):
        return json.dumps({
            "max_tokens": self.max_output,
            "temperature": self.temperature,
            "message": f"{system}\n\n{prompt}",
        })
    def decode_response(self, response):
        content = response['body'].read()
        content_str = content.decode('utf-8')
        content_json = json.loads(content_str)
        return content_json['text']
    def decode_stream_chunk(self, chunk):
        chunk_obj = json.loads(chunk.get('chunk').get('bytes').decode())
        return chunk_obj.get('text', '')

Default=Mistral

class Processor(LlmService):

    def __init__(self, **params):

        logger.debug(f"Bedrock LLM initialized with params: {params}")
    
        model = params.get("model", default_model)
        temperature = params.get("temperature", default_temperature)
        max_output = params.get("max_output", default_max_output)

        aws_access_key_id = params.get(
            "aws_access_key_id", default_access_key_id
        )

        aws_secret_access_key = params.get(
            "aws_secret_access_key", default_secret_access_key
        )

        aws_session_token = params.get(
            "aws_session_token", default_session_token
        )

        aws_region = params.get(
            "aws_region", default_region
        )

        aws_profile = params.get(
            "aws_profile", default_profile
        )

        super(Processor, self).__init__(
            **params | {
                "model": model,
                "temperature": temperature,
                "max_output": max_output,
            }
        )

        # Store default configuration
        self.default_model = model
        self.temperature = temperature
        self.max_output = max_output

        # Cache for model variants to avoid re-initialization
        self.model_variants = {}

        self.session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
            profile_name=aws_profile,
            region_name=aws_region,
        )

        self.bedrock = self.session.client(service_name='bedrock-runtime')

        logger.info("Bedrock LLM service initialized")

    def determine_variant(self, model):

        if ".anthropic." in model or model.startswith("anthropic"):
            return Anthropic
        elif ".meta." in model or model.startswith("meta"):
            return Meta
        elif ".mistral." in model or model.startswith("mistral"):
            return Mistral
        elif ".ai21." in model or model.startswith("ai21"):
            return Ai21
        elif ".cohere." in model or model.startswith("cohere"):
            return Cohere

        return Default
                        
    def _get_or_create_variant(self, model_name, temperature=None):
        """Get cached model variant or create new one"""
        # Use provided temperature or fall back to default
        effective_temperature = temperature if temperature is not None else self.temperature

        # Create a cache key that includes temperature to avoid conflicts
        cache_key = f"{model_name}:{effective_temperature}"

        if cache_key not in self.model_variants:
            logger.info(f"Creating model variant for '{model_name}' with temperature {effective_temperature}")
            variant_class = self.determine_variant(model_name)
            variant = variant_class()
            variant.set_temperature(effective_temperature)
            variant.set_max_output(self.max_output)
            self.model_variants[cache_key] = variant

        return self.model_variants[cache_key]

    async def generate_content(self, system, prompt, model=None, temperature=None):

        # Use provided model or fall back to default
        model_name = model or self.default_model
        # Use provided temperature or fall back to default
        effective_temperature = temperature if temperature is not None else self.temperature

        logger.debug(f"Using model: {model_name}")
        logger.debug(f"Using temperature: {effective_temperature}")

        try:
            # Get the appropriate variant for this model
            variant = self._get_or_create_variant(model_name, effective_temperature)

            promptbody = variant.encode_request(system, prompt)

            accept = 'application/json'
            contentType = 'application/json'

            response = self.bedrock.invoke_model(
                body=promptbody,
                modelId=model_name,
                accept=accept,
                contentType=contentType
            )

            # Response structure decode
            outputtext = variant.decode_response(response)

            metadata = response['ResponseMetadata']['HTTPHeaders']
            inputtokens = int(metadata['x-amzn-bedrock-input-token-count'])
            outputtokens = int(metadata['x-amzn-bedrock-output-token-count'])

            logger.debug(f"LLM output: {outputtext}")
            logger.info(f"Input Tokens: {inputtokens}")
            logger.info(f"Output Tokens: {outputtokens}")

            resp = LlmResult(
                text = outputtext,
                in_token = inputtokens,
                out_token = outputtokens,
                model = model_name
            )

            return resp

        except self.bedrock.exceptions.ThrottlingException as e:

            logger.warning(f"Hit rate limit: {e}")

            # Leave rate limit retries to the base handler
            raise TooManyRequests()

        except Exception as e:

            # Apart from rate limits, treat all exceptions as unrecoverable

            logger.error(f"Bedrock LLM exception ({type(e).__name__}): {e}", exc_info=True)
            raise e

    def supports_streaming(self):
        """Bedrock supports streaming"""
        return True

    async def generate_content_stream(self, system, prompt, model=None, temperature=None):
        """Stream content generation from Bedrock"""
        model_name = model or self.default_model
        effective_temperature = temperature if temperature is not None else self.temperature

        logger.debug(f"Using model (streaming): {model_name}")
        logger.debug(f"Using temperature: {effective_temperature}")

        try:
            variant = self._get_or_create_variant(model_name, effective_temperature)
            promptbody = variant.encode_request(system, prompt)

            accept = 'application/json'
            contentType = 'application/json'

            response = self.bedrock.invoke_model_with_response_stream(
                body=promptbody,
                modelId=model_name,
                accept=accept,
                contentType=contentType
            )

            total_input_tokens = 0
            total_output_tokens = 0

            stream = response.get('body')
            if stream:
                for event in stream:
                    chunk = event.get('chunk')
                    if chunk:
                        # Decode the chunk text
                        text = variant.decode_stream_chunk(event)
                        if text:
                            yield LlmChunk(
                                text=text,
                                in_token=None,
                                out_token=None,
                                model=model_name,
                                is_final=False
                            )

                    # Try to extract metadata from the event
                    metadata = event.get('metadata')
                    if metadata:
                        usage = metadata.get('usage')
                        if usage:
                            total_input_tokens = usage.get('inputTokens', 0)
                            total_output_tokens = usage.get('outputTokens', 0)

            # Send final chunk with token counts
            yield LlmChunk(
                text="",
                in_token=total_input_tokens,
                out_token=total_output_tokens,
                model=model_name,
                is_final=True
            )

            logger.debug("Streaming complete")

        except self.bedrock.exceptions.ThrottlingException as e:
            logger.warning(f"Hit rate limit during streaming: {e}")
            raise TooManyRequests()

        except Exception as e:
            logger.error(f"Bedrock streaming exception ({type(e).__name__}): {e}", exc_info=True)
            raise e

    @staticmethod
    def add_args(parser):

        LlmService.add_args(parser)

        parser.add_argument(
            '-m', '--model',
            default="mistral.mistral-large-2407-v1:0",
            help=f'Bedrock model (default: Mistral-Large-2407)'
        )

        parser.add_argument(
            '-z', '--aws-access-key-id',
            default=default_access_key_id,
            help=f'AWS access key ID'
        )

        parser.add_argument(
            '-k', '--aws-secret-access-key',
            default=default_secret_access_key,
            help=f'AWS secret access key'
        )

        parser.add_argument(
            '-r', '--aws-region',
            default=default_region,
            help=f'AWS region'
        )

        parser.add_argument(
            '--aws-profile', '--profile', 
            default=default_profile,
            help=f'AWS profile name'
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
