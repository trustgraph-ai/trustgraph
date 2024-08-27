
"""
Language service abstracts prompt engineering from LLM.
"""

import json

from .... schema import Definition, Relationship, Triple
from .... schema import PromptRequest, PromptResponse, Error
from .... schema import TextCompletionRequest, TextCompletionResponse
from .... schema import text_completion_request_queue
from .... schema import text_completion_response_queue
from .... schema import prompt_request_queue, prompt_response_queue
from .... base import ConsumerProducer
from .... clients.llm_client import LlmClient

from . prompts import to_definitions, to_relationships, to_rows
from . prompts import to_kg_query, to_document_query

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
        definition_template = params.get("definition_template")
        relationship_template = params.get("relationship_template")
        rows_template = params.get("rows_template")
        knowledge_query_template = params.get("knowledge_query_template")
        document_query_template = params.get("document_query_template")

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

        self.definition_template = definition_template
        self.relationship_template = relationship_template
        self.rows_template = rows_template
        self.knowledge_query_template = knowledge_query_template
        self.document_query_template = document_query_template

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

        elif kind == "extract-rows":

            self.handle_extract_rows(id, v)
            return

        elif kind == "kg-prompt":

            self.handle_kg_prompt(id, v)
            return

        elif kind == "document-prompt":

            self.handle_document_prompt(id, v)
            return

        else:

            print("Invalid kind.", flush=True)
            return

    def handle_extract_definitions(self, id, v):

        try:

            prompt = to_definitions(self.definition_template, v.chunk)

            ans = self.llm.request(prompt)

            # Silently ignore JSON parse error
            try:
                defs = json.loads(ans)
            except:
                print("JSON parse error, ignored", flush=True)
                defs = []

            output = []

            for defn in defs:

                try:
                    e = defn["entity"]
                    d = defn["definition"]

                    if e == "": continue
                    if e is None: continue
                    if d == "": continue
                    if d is None: continue

                    output.append(
                        Definition(
                            name=e, definition=d
                        )
                    )

                except:
                    print("definition fields missing, ignored", flush=True)

            print("Send response...", flush=True)
            r = PromptResponse(definitions=output, error=None)
            self.producer.send(r, properties={"id": id})

            print("Done.", flush=True)
        
        except Exception as e:

            print(f"Exception: {e}")

            print("Send error response...", flush=True)

            r = PromptResponse(
                error=Error(
                    type = "llm-error",
                    message = str(e),
                ),
                response=None,
            )

            self.producer.send(r, properties={"id": id})

    def handle_extract_relationships(self, id, v):

        try:

            prompt = to_relationships(self.relationship_template, v.chunk)

            ans = self.llm.request(prompt)

            # Silently ignore JSON parse error
            try:
                defs = json.loads(ans)
            except:
                print("JSON parse error, ignored", flush=True)
                defs = []

            output = []

            for defn in defs:

                try:

                    s = defn["subject"]
                    p = defn["predicate"]
                    o = defn["object"]
                    o_entity = defn["object-entity"]

                    if s == "": continue
                    if s is None: continue

                    if p == "": continue
                    if p is None: continue

                    if o == "": continue
                    if o is None: continue

                    if o_entity == "" or o_entity is None:
                        o_entity = False

                    output.append(
                        Relationship(
                            s = s,
                            p = p,
                            o = o,
                            o_entity = o_entity,
                        )
                    )

                except Exception as e:
                    print("relationship fields missing, ignored", flush=True)

            print("Send response...", flush=True)
            r = PromptResponse(relationships=output, error=None)
            self.producer.send(r, properties={"id": id})

            print("Done.", flush=True)

        except Exception as e:

            print(f"Exception: {e}")

            print("Send error response...", flush=True)

            r = PromptResponse(
                error=Error(
                    type = "llm-error",
                    message = str(e),
                ),
                response=None,
            )

            self.producer.send(r, properties={"id": id})

    def handle_extract_rows(self, id, v):

        try:

            fields = v.row_schema.fields

            prompt = to_rows(self.rows_template, v.row_schema, v.chunk)

            print(prompt)

            ans = self.llm.request(prompt)

            print(ans)

            # Silently ignore JSON parse error
            try:
                objs = json.loads(ans)
            except:
                print("JSON parse error, ignored", flush=True)
                objs = []

            output = []

            for obj in objs:

                try:

                    row = {}

                    for f in fields:

                        if f.name not in obj:
                            print(f"Object ignored, missing field {f.name}")
                            row = {}
                            break

                        row[f.name] = obj[f.name]

                    if row == {}:
                        continue

                    output.append(row)

                except Exception as e:
                    print("row fields missing, ignored", flush=True)

            for row in output:
                print(row)

            print("Send response...", flush=True)
            r = PromptResponse(rows=output, error=None)
            self.producer.send(r, properties={"id": id})

            print("Done.", flush=True)

        except Exception as e:

            print(f"Exception: {e}")

            print("Send error response...", flush=True)

            r = PromptResponse(
                error=Error(
                    type = "llm-error",
                    message = str(e),
                ),
                response=None,
            )

            self.producer.send(r, properties={"id": id})
        
    def handle_kg_prompt(self, id, v):

        try:

            prompt = to_kg_query(self.knowledge_query_template, v.query, v.kg)

            print(prompt)

            ans = self.llm.request(prompt)

            print(ans)

            print("Send response...", flush=True)
            r = PromptResponse(answer=ans, error=None)
            self.producer.send(r, properties={"id": id})

            print("Done.", flush=True)

        except Exception as e:

            print(f"Exception: {e}")

            print("Send error response...", flush=True)

            r = PromptResponse(
                error=Error(
                    type = "llm-error",
                    message = str(e),
                ),
                response=None,
            )

            self.producer.send(r, properties={"id": id})
        
    def handle_document_prompt(self, id, v):

        try:

            prompt = to_document_query(
                self.document_query_template, v.query, v.documents
            )

            print(prompt)

            ans = self.llm.request(prompt)

            print(ans)

            print("Send response...", flush=True)
            r = PromptResponse(answer=ans, error=None)
            self.producer.send(r, properties={"id": id})

            print("Done.", flush=True)

        except Exception as e:

            print(f"Exception: {e}")

            print("Send error response...", flush=True)

            r = PromptResponse(
                error=Error(
                    type = "llm-error",
                    message = str(e),
                ),
                response=None,
            )

            self.producer.send(r, properties={"id": id})
        
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

        parser.add_argument(
            '--definition-template',
            required=True,
            help=f'Definition extraction template',
        )

        parser.add_argument(
            '--rows-template',
            required=True,
            help=f'Rows extraction template',
        )

        parser.add_argument(
            '--relationship-template',
            required=True,
            help=f'Relationship extraction template',
        )

        parser.add_argument(
            '--knowledge-query-template',
            required=True,
            help=f'Knowledge query template',
        )

        parser.add_argument(
            '--document-query-template',
            required=True,
            help=f'Document query template',
        )

def run():

    Processor.start(module, __doc__)

