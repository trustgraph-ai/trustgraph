
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
from .... base import LlmService, LlmResult

# Module logger
logger = logging.getLogger(__name__)

default_ident = "text-completion"

default_model = 'mistral.mistral-large-2407-v1:0'
default_temperature = 0.0
default_max_output = 2048
default_top_p = 0.99
default_top_k = 40

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
        self.top_p = default_top_p
        self.top_k = default_top_k
    def set_temperature(self, temperature):
        self.temperature = temperature
    def set_max_output(self, max_output):
        self.max_output = max_output
    def set_top_p(self, top_p):
        self.top_p = top_p
    def set_top_k(self, top_k):
        self.top_k = top_k
    def encode_request(self, system, prompt):
        raise RuntimeError("format_request not implemented")
    def decode_response(self, response):
        raise RuntimeError("format_request not implemented")

class Mistral(ModelHandler):
    def __init__(self):
        self.top_p = 0.99
        self.top_k = 40
    def encode_request(self, system, prompt):
        return json.dumps({
            "prompt": f"{system}\n\n{prompt}",
            "max_tokens": self.max_output,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
        })
    def decode_response(self, response):
        response_body = json.loads(response.get("body").read())
        return response_body['outputs'][0]['text']

# Llama 3
class Meta(ModelHandler):
    def __init__(self):
        self.top_p = 0.95
    def encode_request(self, system, prompt):
        return json.dumps({
            "prompt": f"{system}\n\n{prompt}",
            "max_gen_len": self.max_output,
            "temperature": self.temperature,
            "top_p": self.top_p,
        })
    def decode_response(self, response):
        model_response = json.loads(response["body"].read())
        return model_response["generation"]

class Anthropic(ModelHandler):
    def __init__(self):
        self.top_p = 0.999
    def encode_request(self, system, prompt):
        return json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self.max_output,
            "temperature": self.temperature,
            "top_p": self.top_p,
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

class Ai21(ModelHandler):
    def __init__(self):
        self.top_p = 0.9
    def encode_request(self, system, prompt):
        return json.dumps({
            "max_tokens": self.max_output,
            "temperature": self.temperature,
            "top_p": self.top_p,
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

        self.model = model
        self.temperature = temperature
        self.max_output = max_output

        self.variant = self.determine_variant(self.model)()
        self.variant.set_temperature(temperature)
        self.variant.set_max_output(max_output)

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

        # FIXME: Missing, Amazon models, Deepseek

        # This set of conditions deals with normal bedrock on-demand usage
        if self.model.startswith("mistral"):
            return Mistral
        elif self.model.startswith("meta"):
            return Meta
        elif self.model.startswith("anthropic"):
            return Anthropic
        elif self.model.startswith("ai21"):
            return Ai21
        elif self.model.startswith("cohere"):
            return Cohere

        # The inference profiles
        if self.model.startswith("us.meta"):
            return Meta
        elif self.model.startswith("us.anthropic"):
            return Anthropic
        elif self.model.startswith("eu.meta"):
            return Meta
        elif self.model.startswith("eu.anthropic"):
            return Anthropic

        return Default
                        
    async def generate_content(self, system, prompt):

        try:

            promptbody = self.variant.encode_request(system, prompt)

            accept = 'application/json'
            contentType = 'application/json'

            response = self.bedrock.invoke_model(
                body=promptbody,
                modelId=self.model,
                accept=accept,
                contentType=contentType
            )

            # Response structure decode
            outputtext = self.variant.decode_response(response)

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
                model = self.model
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
