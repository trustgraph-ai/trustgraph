
"""
Simple LLM service, performs text prompt completion using Cohere.
Input is prompt, output is response.
"""

import cohere
import re

from .... schema import TextCompletionRequest, TextCompletionResponse
from .... schema import text_completion_request_queue
from .... schema import text_completion_response_queue
from .... log_level import LogLevel
from .... base import ConsumerProducer

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = text_completion_request_queue
default_output_queue = text_completion_response_queue
default_subscriber = module
default_model = 'c4ai-aya-23-8b'

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

        self.cohere = cohere.Client(api_key=api_key)

        print("Initialised", flush=True)

    def handle(self, msg):

        v = msg.value()

        # Sender-produced ID

        id = msg.properties()["id"]

        print(f"Handling prompt {id}...", flush=True)

        prompt = v.prompt

        stream = self.cohere.chat_stream( 
        model=self.model,
        #model='c4ai-aya-23-8b',
        message=prompt,
        preamble = "You are an AI-assistant chatbot. You are trained to read text and find entities in that text. You respond only with well-formed JSON.",
        temperature=0.0,
        chat_history=[],
        prompt_truncation='auto',
        connectors=[]
        ) 

        for event in stream:
            if event.event_type == "text-generation":
                resp = event.text
                print(resp, flush=True)

        # Parse output for ```json``` delimiters
        pattern = r'```json\s*([\s\S]*?)\s*```'
        match = re.search(pattern, resp)

        if match:
            # If delimiters are found, extract the JSON content
            json_content = match.group(1)
            json_resp = json_content.strip()
        
        else:
            # If no delimiters are found, return the original text
            json_resp = resp.strip()
        
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
            default="c4ai-aya-23-8b",
            help=f'Cohere model (default: c4ai-aya-23-8b)'
        )

        parser.add_argument(
            '-k', '--api-key',
            help=f'Cohere API key'
        )

def run():

    Processor.start(module, __doc__)

    
