
"""
Simple LLM service, performs text prompt completion using AWS Bedrock.
Input is prompt, output is response. Mistral is default.
"""

import boto3
import json
from prometheus_client import Histogram

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

        try:

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

            # Jamba Input Format
            elif self.model.startswith("ai21"):
                promptbody = json.dumps({
                    "max_tokens": self.max_output,
                    "temperature": self.temperature,
                    "top_p": 0.9,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                })

            # Cohere Input Format
            elif self.model.startswith("cohere"):
                promptbody = json.dumps({
                    "max_tokens": self.max_output,
                    "temperature": self.temperature,
                    "message": prompt
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

            with __class__.text_completion_metric.time():
                response = self.bedrock.invoke_model(
                    body=promptbody, modelId=self.model, accept=accept,
                    contentType=contentType
                )

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

            # Jamba Response Structure
            elif self.model.startswith("ai21"):
                content = response['body'].read()
                content_str = content.decode('utf-8')
                content_json = json.loads(content_str)
                outputtext = content_json['choices'][0]['message']['content']

            # Cohere Input Format
            elif self.model.startswith("cohere"):
                content = response['body'].read()
                content_str = content.decode('utf-8')
                content_json = json.loads(content_str)
                outputtext = content_json['text']

            # Use Mistral as default
            else:
                response_body = json.loads(response.get("body").read())
                outputtext = response_body['outputs'][0]['text']            

            print(outputtext, flush=True)

            resp = outputtext.replace("```json", "")
            resp = resp.replace("```", "")    

            print("Send response...", flush=True)
            r = TextCompletionResponse(
                error=None,
                response=resp
            )

            self.send(r, properties={"id": id})

            print("Done.", flush=True)


        # FIXME: Wrong exception, don't know what Bedrock throws
        # for a rate limit
        except TooManyRequests:

            print("Send rate limit response...", flush=True)

            r = TextCompletionResponse(
                error=Error(
                    type = "rate-limit",
                    message = str(e),
                ),
                response=None,
            )

            self.producer.send(r, properties={"id": id})

            self.consumer.acknowledge(msg)

        except Exception as e:

            print(f"Exception: {e}")

            print("Send error response...", flush=True)

            r = TextCompletionResponse(
                error=Error(
                    type = "llm-error",
                    message = str(e),
                ),
                response=None,
            )

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

    
