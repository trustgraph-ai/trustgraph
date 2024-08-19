
"""
Simple LLM service, performs text prompt completion using AWS Bedrock.
Input is prompt, output is response. Mistral is default.
"""

import boto3
import json
import re

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

class Processor(ConsumerProducer):

    def __init__(self, **params):
    
        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)
        model = params.get("model", default_model)
        aws_id = params.get("aws_id_key")
        aws_secret = params.get("aws_secret")
        aws_region = params.get("aws_region", default_region)

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "output_queue": output_queue,
                "subscriber": subscriber,
                "input_schema": TextCompletionRequest,
                "output_schema": TextCompletionResponse,
                "model": model,
            }
        )

        self.model = model

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
                "max_tokens": 8192,
                "temperature": 0.0,
                "top_p": 0.99,
                "top_k": 40
            })

        # Llama 3.1 Input Format
        elif self.model.startswith("meta"):
            promptbody = json.dumps({
                "prompt": prompt,
                "max_gen_len": 2048,
                "temperature": 0.0,
                "top_p": 0.95,
            })

        # Anthropic Input Format
        elif self.model.startswith("anthropic"):
            promptbody = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 8192,
                "temperature": 0,
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
                "max_tokens": 8192,
                "temperature": 0.0,
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
       
        # Parse output for ```json``` delimiters
        pattern = r'```json\s*([\s\S]*?)\s*```'
        match = re.search(pattern, outputtext)

        if match:
            # If delimiters are found, extract the JSON content
            json_content = match.group(1)
            json_resp = json_content.strip()
        
        else:
            # If no delimiters are found, return the original text
            json_resp = outputtext.strip()
        
        print("Send response...", flush=True)
        r = TextCompletionResponse(response=json_resp)
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

def run():

    Processor.start(module, __doc__)

    
