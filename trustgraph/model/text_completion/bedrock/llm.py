
"""
Simple LLM service, performs text prompt completion using AWS Bedrock.
Input is prompt, output is response. Mistral is default.
"""

import boto3
import json

from .... schema import TextCompletionRequest, TextCompletionResponse
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
default_region = 'us-west-2'
default_temperature = 0.0
default_max_output = 2048


class Processor(ConsumerProducer):

    def __init__(self, **params):
    
        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)
        model = params.get("model", default_model)
        aws_id = params.get("aws_id_key")
        aws_secret = params.get("aws_secret")
        aws_region = params.get("aws_region", default_region)
        temperature = params.get("temperature", default_temperature)
        max_output = params.get("max_output", default_max_output)

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

        self.model = model
        self.temperature = temperature
        self.max_output = max_output

        self.session = boto3.Session(
            aws_access_key_id=aws_id,
            aws_secret_access_key=aws_secret,
            region_name=aws_region
        )

        self.bedrock = self.session.client(service_name='bedrock-runtime')

        print("Initialised", flush=True)

    def handle(self, msg):

        v = msg.value()

        # Sender-produced ID

        id = msg.properties()["id"]

        print(f"Handling prompt {id}...", flush=True)

        prompt = v.prompt

       # Mistral Input Format
        if self.model.startswith("mistral"):
            promptbody = json.dumps({
                "prompt": prompt,
                "max_tokens": self.max_output,
                "temperature": self.temperature,
                "top_p": 0.99,
                "top_k": 40
            })

        # Llama 3.1 Input Format
        elif self.model.startswith("meta"):
            promptbody = json.dumps({
                "prompt": prompt,
                "max_gen_len": self.max_output,
                "temperature": self.temperature,
                "top_p": 0.95,
            })

        # Anthropic Input Format
        elif self.model.startswith("anthropic"):
            promptbody = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": self.max_output,
                "temperature": self.temperature,
                "top_p": 0.999,
                "messages": [
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
            })

            # Use Mistral format as defualt
        else:
            promptbody = json.dumps({
                "prompt": prompt,
                "max_tokens": self.max_output,
                "temperature": self.temperature,
                "top_p": 0.99,
                "top_k": 40
            })

        accept = 'application/json'
        contentType = 'application/json'

        # FIXME: Consider catching request limits and raise TooManyRequests
        # See https://boto3.amazonaws.com/v1/documentation/api/latest/guide/retries.html
        response = self.bedrock.invoke_model(body=promptbody, modelId=self.model, accept=accept, contentType=contentType)
        
        # Mistral Response Structure
        if self.model.startswith("mistral"):
            response_body = json.loads(response.get("body").read())
            outputtext = response_body['outputs'][0]['text']

        # Claude Response Structure
        elif self.model.startswith("anthropic"):
            model_response = json.loads(response["body"].read())
            outputtext = model_response['content'][0]['text']

        # Llama 3.1 Response Structure
        elif self.model.startswith("meta"):
            model_response = json.loads(response["body"].read())
            outputtext = model_response["generation"]

        # Use Mistral as default
        else:
            response_body = json.loads(response.get("body").read())
            outputtext = response_body['outputs'][0]['text']            
 
        print(outputtext, flush=True)

        resp = outputtext.replace("```json", "")
        resp = outputtext.replace("```", "")    
    
        print("Send response...", flush=True)
        r = TextCompletionResponse(response=resp)
        self.send(r, properties={"id": id})

        print("Done.", flush=True)

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
            '-z', '--aws-id-key',
            help=f'AWS ID Key'
        )

        parser.add_argument(
            '-k', '--aws-secret',
            help=f'AWS Secret Key'
        )

        parser.add_argument(
            '-r', '--aws-region',
            help=f'AWS Region (default: us-west-2)'
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

    Processor.start(module, __doc__)

    
