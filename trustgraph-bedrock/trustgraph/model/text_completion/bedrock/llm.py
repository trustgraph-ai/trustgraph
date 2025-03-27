
"""
Simple LLM service, performs text prompt completion using AWS Bedrock.
Input is prompt, output is response. Mistral is default.
"""

import boto3
import json
from prometheus_client import Histogram
import os
import enum

from .... schema import TextCompletionRequest, TextCompletionResponse, Error
from .... schema import text_completion_request_queue
from .... schema import text_completion_response_queue
from .... log_level import LogLevel
from .... base import ConsumerProducer
from .... exceptions import TooManyRequests

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = text_completion_request_queue
default_output_queue = text_completion_response_queue
default_subscriber = module
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

class Processor(ConsumerProducer):

    def __init__(self, **params):

        print(params)
    
        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)

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
                "input_queue": input_queue,
                "output_queue": output_queue,
                "subscriber": subscriber,
                "input_schema": TextCompletionRequest,
                "output_schema": TextCompletionResponse,
                "model": model,
                "temperature": temperature,
                "max_output": max_output,
            }
        )

        if not hasattr(__class__, "text_completion_metric"):
            __class__.text_completion_metric = Histogram(
                'text_completion_duration',
                'Text completion duration (seconds)',
                buckets=[
                    0.25, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0,
                    8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0,
                    17.0, 18.0, 19.0, 20.0, 21.0, 22.0, 23.0, 24.0, 25.0,
                    30.0, 35.0, 40.0, 45.0, 50.0, 60.0, 80.0, 100.0,
                    120.0
                ]
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

        print("Initialised", flush=True)

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
                        
    async def handle(self, msg):

        v = msg.value()

        # Sender-produced ID

        id = msg.properties()["id"]

        print(f"Handling prompt {id}...", flush=True)

        try:

            promptbody = self.variant.encode_request(v.system, v.prompt)

            accept = 'application/json'
            contentType = 'application/json'

            with __class__.text_completion_metric.time():
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

            print(outputtext, flush=True)
            print(f"Input Tokens: {inputtokens}", flush=True)
            print(f"Output Tokens: {outputtokens}", flush=True)

            print("Send response...", flush=True)
            r = TextCompletionResponse(
                error=None,
                response=outputtext,
                in_token=inputtokens,
                out_token=outputtokens,
                model=str(self.model),
            )

            await self.send(r, properties={"id": id})

            print("Done.", flush=True)

        except self.bedrock.exceptions.ThrottlingException as e:

            print("Hit rate limit:", e, flush=True)

            # Leave rate limit retries to the base handler
            raise TooManyRequests()

        except Exception as e:

            # Apart from rate limits, treat all exceptions as unrecoverable

            print(type(e))
            print(f"Exception: {e}")

            print("Send error response...", flush=True)

            r = TextCompletionResponse(
                error=Error(
                    type = "llm-error",
                    message = str(e),
                ),
                response=None,
                in_token=None,
                out_token=None,
                model=None,
            )

            await self.send(r, properties={"id": id})

            self.consumer.acknowledge(msg)

    @staticmethod
    def add_args(parser):

        ConsumerProducer.add_args(
            parser, default_input_queue, default_subscriber,
            default_output_queue,
        )

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

    Processor.launch(module, __doc__)

