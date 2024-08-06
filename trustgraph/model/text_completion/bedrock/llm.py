
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

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = text_completion_request_queue
default_output_queue = text_completion_response_queue
default_subscriber = module
default_model = 'mistral.mistral-large-2407-v1:0'

class Processor(ConsumerProducer):

    def __init__(self, **params):
    
        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)
        model = params.get("model", default_model)
        api_key = params.get("api_key")

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

        self.bedrock = boto3.client(service_name='bedrock-runtime', region_name="us-west-2")

        print("Initialised", flush=True)

    def handle(self, msg):

        v = msg.value()

        # Sender-produced ID

        id = msg.properties()["id"]

        print(f"Handling prompt {id}...", flush=True)

        prompt = v.prompt

        promptbody = json.dumps({
            "prompt": prompt,
            "max_tokens": 8192,
            "temperature": 0.0,
            "top_p": 0.99,
            "top_k": 40
        })

        accept = 'application/json'
        contentType = 'application/json'

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
 
        resp = outputtext
        print(resp, flush=True)
        
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

def run():

    Processor.start(module, __doc__)

    
