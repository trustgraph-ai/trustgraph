
"""
Language service abstracts prompt engineering from LLM.
"""

import json

from ..... schema import Definition, Relationship, Triple
from ..... schema import PromptRequest, PromptResponse
from ..... schema import TextCompletionRequest, TextCompletionResponse
from ..... schema import text_completion_request_queue
from ..... schema import text_completion_response_queue
from ..... schema import prompt_request_queue, prompt_response_queue
from ..... base import ConsumerProducer
from ..... llm_client import LlmClient

from . prompts import to_definitions, to_relationships, to_kg_query

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = prompt_request_queue
default_output_queue = prompt_response_queue
default_subscriber = module

class Processor(ConsumerProducer):

    def __init__(self, **params):

        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)
        tc_request_queue = params.get(
            "text_completion_request_queue", text_completion_request_queue
        )
        tc_response_queue = params.get(
            "text_completion_response_queue", text_completion_response_queue
        )

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "output_queue": output_queue,
                "subscriber": subscriber,
                "input_schema": PromptRequest,
                "output_schema": PromptResponse,
                "text_completion_request_queue": tc_request_queue,
                "text_completion_response_queue": tc_response_queue,
            }
        )

        self.llm = LlmClient(
            subscriber=subscriber,
            input_queue=tc_request_queue,
            output_queue=tc_response_queue,
            pulsar_host = self.pulsar_host
        )

    def handle(self, msg):

        v = msg.value()

        # Sender-produced ID

        id = msg.properties()["id"]

        kind = v.kind

        print(f"Handling kind {kind}...", flush=True)

        if kind == "extract-definitions":

            self.handle_extract_definitions(id, v)
            return

        elif kind == "extract-relationships":

            self.handle_extract_relationships(id, v)
            return

        elif kind == "kg-prompt":

            self.handle_kg_prompt(id, v)
            return

        else:

            print("Invalid kind.", flush=True)
            return

    def handle_extract_definitions(self, id, v):

        prompt = to_definitions(v.chunk)

        print(prompt)

        ans = self.llm.request(prompt)

        print(ans)

        defs = json.loads(ans)

        output = []

        for defn in defs:

            try:
                e = defn["entity"]
                d = defn["definition"]

                output.append(
                    Definition(
                        name=e, definition=d
                    )
                )

            except:
                pass

        print("Send response...", flush=True)
        r = PromptResponse(definitions=output)
        self.producer.send(r, properties={"id": id})

        print("Done.", flush=True)
        
    def handle_extract_relationships(self, id, v):

        prompt = to_relationships(v.chunk)

        ans = self.llm.request(prompt)

        defs = json.loads(ans)

        output = []

        for defn in defs:

            try:
                output.append(
                    Relationship(
                        s = defn["subject"],
                        p = defn["predicate"],
                        o = defn["object"],
                        o_entity = defn["object-entity"],
                    )
                )

            except Exception as e:
                print(e)

        print("Send response...", flush=True)
        r = PromptResponse(relationships=output)
        self.producer.send(r, properties={"id": id})

        print("Done.", flush=True)
        
    def handle_kg_prompt(self, id, v):

        prompt = to_kg_query(v.query, v.kg)

        print(prompt)

        ans = self.llm.request(prompt)

        print(ans)

        print("Send response...", flush=True)
        r = PromptResponse(answer=ans)
        self.producer.send(r, properties={"id": id})

        print("Done.", flush=True)
        
    @staticmethod
    def add_args(parser):

        ConsumerProducer.add_args(
            parser, default_input_queue, default_subscriber,
            default_output_queue,
        )

        parser.add_argument(
            '--text-completion-request-queue',
            default=text_completion_request_queue,
            help=f'Text completion request queue (default: {text_completion_request_queue})',
        )

        parser.add_argument(
            '--text-completion-response-queue',
            default=text_completion_response_queue,
            help=f'Text completion response queue (default: {text_completion_response_queue})',
        )

def run():

    Processor.start(module, __doc__)

