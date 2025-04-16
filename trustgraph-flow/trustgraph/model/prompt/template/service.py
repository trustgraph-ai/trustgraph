
"""
Language service abstracts prompt engineering from LLM.
"""

import asyncio
import json
import re

from .... schema import Definition, Relationship, Triple
from .... schema import Topic
from .... schema import PromptRequest, PromptResponse, Error
from .... schema import TextCompletionRequest, TextCompletionResponse
from .... base import FlowProcessor, SubscriberSpec, ConsumerSpec
from .... base import ProducerSpec

from . prompt_manager import PromptConfiguration, Prompt, PromptManager

default_ident = "prompt"

class Processor(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")

        # Config key for prompts
        self.config_key = params.get("config_type", "prompt")

        super(Processor, self).__init__(
            **params | {
                "id": id,
            }
        )

        # self.llm = LlmClient(
        #     subscriber=subscriber,
        #     input_queue=tc_request_queue,
        #     output_queue=tc_response_queue,
        #     pulsar_host = self.pulsar_host,
        #     pulsar_api_key=self.pulsar_api_key,
        # )

        self.register_specification(
            ConsumerSpec(
                name = "request",
                schema = PromptRequest,
                handler = self.on_request
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "text-completion-request",
                schema = TextCompletionRequest
            )
        )

        self.register_specification(
            SubscriberSpec(
                name = "text-completion-response",
                schema = TextCompletionResponse,
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "response",
                schema = PromptResponse
            )
        )

        self.register_config_handler(self.on_prompt_config)

        # Null configuration, should reload quickly
        self.manager = PromptManager(
            config = PromptConfiguration("", {}, {})
        )

    async def on_prompt_config(self, config, version):

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

    async def on_request(self, msg, consumer, flow):

        v = msg.value()

        # Sender-produced ID

        id = msg.properties()["id"]

        kind = v.id

        try:

            print(v.terms, flush=True)

            input = {
                k: json.loads(v)
                for k, v in v.terms.items()
            }
            
            print(f"Handling kind {kind}...", flush=True)

            q = await flow.consumer["text-completion-response"].subscribe(id)

            async def llm(system, prompt):

                print(system, flush=True)
                print(prompt, flush=True)

                await flow.producer["text-completion-request"].send(
                    TextCompletionRequest(
                        system=system, prompt=prompt
                    ),
                    properties={"id": id}
                )

                # FIXME: hard-coded?
                resp = await asyncio.wait_for(
                    q.get(),
                    timeout=600
                )

                try:
                    return resp.response
                except Exception as e:
                    print("LLM Exception:", e, flush=True)
                    return None

            try:
                resp = await self.manager.invoke(kind, input, llm)
            except Exception as e:
                print("Invocation exception:", e, flush=True)
                raise e
            finally:
                await flow.consumer["text-completion-response"].unsubscribe(id)

            if isinstance(resp, str):

                print("Send text response...", flush=True)
                print(resp, flush=True)

                r = PromptResponse(
                    text=resp,
                    object=None,
                    error=None,
                )

                await flow.response.send(r, properties={"id": id})

                return

            else:

                print("Send object response...", flush=True)
                print(json.dumps(resp, indent=4), flush=True)

                r = PromptResponse(
                    text=None,
                    object=json.dumps(resp),
                    error=None,
                )

                await flow.response.send(r, properties={"id": id})

                return
            
        except Exception as e:

            print(f"Exception: {e}", flush=True)

            print("Send error response...", flush=True)

            r = PromptResponse(
                error=Error(
                    type = "llm-error",
                    message = str(e),
                ),
                response=None,
            )

            await flow.response.send(r, properties={"id": id})

        except Exception as e:

            print(f"Exception: {e}", flush=True)

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

        FlowProcessor.add_args(parser)

        parser.add_argument(
            '--config-type',
            default="prompt",
            help=f'Configuration key for prompts (default: prompt)',
        )

def run():

    Processor.launch(default_ident, __doc__)

