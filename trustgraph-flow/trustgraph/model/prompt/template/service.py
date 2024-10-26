
"""
Language service abstracts prompt engineering from LLM.
"""

import json
import re

from .... schema import Definition, Relationship, Triple
from .... schema import Topic
from .... schema import PromptRequest, PromptResponse, Error
from .... schema import TextCompletionRequest, TextCompletionResponse
from .... schema import text_completion_request_queue
from .... schema import text_completion_response_queue
from .... schema import prompt_request_queue, prompt_response_queue
from .... base import ConsumerProducer
from .... clients.llm_client import LlmClient

from . prompt_manager import PromptConfiguration, Prompt, PromptManager

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = prompt_request_queue
default_output_queue = prompt_response_queue
default_subscriber = module

class Processor(ConsumerProducer):

    def __init__(self, **params):

        prompt_base = {}

        # Parsing the prompt information to the prompt configuration
        # structure
        prompt_arg = params.get("prompt", [])
        if prompt_arg:
            for p in prompt_arg:
                toks = p.split("=", 1)
                if len(toks) < 2:
                    raise RuntimeError(f"Prompt string not well-formed: {p}")
                prompt_base[toks[0]] = {
                    "template": toks[1]
                }

        prompt_response_type_arg = params.get("prompt_response_type", [])
        if prompt_response_type_arg:
            for p in prompt_response_type_arg:
                toks = p.split("=", 1)
                if len(toks) < 2:
                    raise RuntimeError(f"Response type not well-formed: {p}")
                if toks[0] not in prompt_base:
                    raise RuntimeError(f"Response-type, {toks[0]} not known")
                prompt_base[toks[0]]["response_type"] = toks[1]

        prompt_schema_arg = params.get("prompt_schema", [])
        if prompt_schema_arg:
            for p in prompt_schema_arg:
                toks = p.split("=", 1)
                if len(toks) < 2:
                    raise RuntimeError(f"Schema arg not well-formed: {p}")
                if toks[0] not in prompt_base:
                    raise RuntimeError(f"Schema, {toks[0]} not known")
                try:
                    prompt_base[toks[0]]["schema"] = json.loads(toks[1])
                except:
                    raise RuntimeError(f"Failed to parse JSON schema: {p}")

        prompt_term_arg = params.get("prompt_term", [])
        if prompt_term_arg:
            for p in prompt_term_arg:
                toks = p.split("=", 1)
                if len(toks) < 2:
                    raise RuntimeError(f"Term arg not well-formed: {p}")
                if toks[0] not in prompt_base:
                    raise RuntimeError(f"Term, {toks[0]} not known")
                kvtoks = toks[1].split(":", 1)
                if len(kvtoks) < 2:
                    raise RuntimeError(f"Term not well-formed: {toks[1]}")
                k, v = kvtoks
                if "terms" not in prompt_base[toks[0]]:
                    prompt_base[toks[0]]["terms"] = {}
                prompt_base[toks[0]]["terms"][k] = v

        global_terms = {}

        global_term_arg = params.get("global_term", [])
        if global_term_arg:
            for t in global_term_arg:
                toks = t.split("=", 1)
                if len(toks) < 2:
                    raise RuntimeError(f"Global term arg not well-formed: {t}")
                global_terms[toks[0]] = toks[1]

        print(global_terms)

        prompts = {
            k: Prompt(**v)
            for k, v in prompt_base.items()
        }

        prompt_configuration = PromptConfiguration(
            system_template = params.get("system_prompt", ""),
            global_terms = global_terms,
            prompts = prompts
        )

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
        topic_template = params.get("topic_template")
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

        # System prompt hack
        class Llm:
            def __init__(self, llm):
                self.llm = llm
            def request(self, system, prompt):
                print(system)
                print(prompt, flush=True)
                return self.llm.request(system + "\n\n" + prompt)

        self.llm = Llm(self.llm)

        self.manager = PromptManager(
            llm = self.llm,
            config = prompt_configuration,
        )

    def handle(self, msg):

        v = msg.value()

        # Sender-produced ID

        id = msg.properties()["id"]

        kind = v.id

        try:
            input = {
                k: json.loads(v)
                for k, v in v.terms.items()
            }
            
            print(f"Handling kind {kind}...", flush=True)
            print(input, flush=True)

            resp = self.manager.invoke(kind, input)

            if isinstance(resp, str):

                print("Send text response...", flush=True)
                print(resp, flush=True)

                r = PromptResponse(
                    text=resp,
                    object=None,
                    error=None,
                )

                self.producer.send(r, properties={"id": id})

                return

            else:

                print("Send object response...", flush=True)
                print(json.dumps(resp, indent=4), flush=True)

                r = PromptResponse(
                    text=None,
                    object=json.dumps(resp),
                    error=None,
                )

                self.producer.send(r, properties={"id": id})

                return
            
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
            '--prompt', nargs='*',
            help=f'Prompt template form id=template',
        )

        parser.add_argument(
            '--prompt-response-type', nargs='*',
            help=f'Prompt response type, form id=json|text',
        )

        parser.add_argument(
            '--prompt-term', nargs='*',
            help=f'Prompt response type, form id=key:value',
        )

        parser.add_argument(
            '--prompt-schema', nargs='*',
            help=f'Prompt response schema, form id=schema',
        )

        parser.add_argument(
            '--system-prompt',
            help=f'System prompt template',
        )

        parser.add_argument(
            '--global-term', nargs='+',
            help=f'Global term, form key:value'
        )

def run():

    Processor.start(module, __doc__)

