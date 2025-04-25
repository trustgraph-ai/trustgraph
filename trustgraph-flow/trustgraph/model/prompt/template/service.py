
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

        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)
        tc_request_queue = params.get(
            "text_completion_request_queue", text_completion_request_queue
        )
        tc_response_queue = params.get(
            "text_completion_response_queue", text_completion_response_queue
        )

        self.config_key = params.get("config_type", "prompt")

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
            pulsar_host = self.pulsar_host,
            pulsar_api_key=self.pulsar_api_key,
        )

        # System prompt hack
        class Llm:
            def __init__(self, llm):
                self.llm = llm
            def request(self, system, prompt):
                print(system)
                print(prompt, flush=True)
                return self.llm.request(system, prompt)

        self.llm = Llm(self.llm)

        # Null configuration, should reload quickly
        self.manager = PromptManager(
            llm = self.llm,
            config = PromptConfiguration("", {}, {})
        )

    async def on_config(self, version, config):

        print("Loading configuration version", version)

        if self.config_key not in config:
            print(f"No key {self.config_key} in config", flush=True)
            return

        config = config[self.config_key]

        try:

            system = json.loads(config["system"])
            ix = json.loads(config["template-index"])

            prompts = {}

            for k in ix:

                pc = config[f"template.{k}"]
                data = json.loads(pc)

                prompt = data.get("prompt")
                rtype = data.get("response-type", "text")
                schema = data.get("schema", None)

                prompts[k] = Prompt(
                    template = prompt,
                    response_type = rtype,
                    schema = schema,
                    terms = {}
                )

            self.manager = PromptManager(
                self.llm,
                PromptConfiguration(
                    system,
                    {},
                    prompts
                )
            )

            print("Prompt configuration reloaded.", flush=True)

        except Exception as e:

            print("Exception:", e, flush=True)
            print("Configuration reload failed", flush=True)

    async def handle(self, msg):

        v = msg.value()

        # Sender-produced ID

        id = msg.properties()["id"]

        kind = v.id

        try:

            print(v.terms)

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

                await self.send(r, properties={"id": id})

                return

            else:

                print("Send object response...", flush=True)
                print(json.dumps(resp, indent=4), flush=True)

                r = PromptResponse(
                    text=None,
                    object=json.dumps(resp),
                    error=None,
                )

                await self.send(r, properties={"id": id})

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

            await self.send(r, properties={"id": id})

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

            await self.send(r, properties={"id": id})

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
            '--config-type',
            default="prompt",
            help=f'Configuration key for prompts (default: prompt)',
        )

def run():

    Processor.launch(module, __doc__)

