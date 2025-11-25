
"""
Language service abstracts prompt engineering from LLM.
"""

import asyncio
import json
import re
import logging

from ...schema import Definition, Relationship, Triple
from ...schema import Topic
from ...schema import PromptRequest, PromptResponse, Error
from ...schema import TextCompletionRequest, TextCompletionResponse

from ...base import FlowProcessor
from ...base import ProducerSpec, ConsumerSpec, TextCompletionClientSpec

from ...template import PromptManager

# Module logger
logger = logging.getLogger(__name__)

default_ident = "prompt"
default_concurrency = 1

class Processor(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")
        concurrency = params.get("concurrency", 1)

        # Config key for prompts
        self.config_key = params.get("config_type", "prompt")

        super(Processor, self).__init__(
            **params | {
                "id": id,
                "config_type": self.config_key,
                "concurrency": concurrency,
            }
        )

        self.register_specification(
            ConsumerSpec(
                name = "request",
                schema = PromptRequest,
                handler = self.on_request,
                concurrency = concurrency,
            )
        )

        self.register_specification(
            TextCompletionClientSpec(
                request_name = "text-completion-request",
                response_name = "text-completion-response",
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
        self.manager = PromptManager()

    async def on_prompt_config(self, config, version):

        logger.info(f"Loading prompt configuration version {version}")

        if self.config_key not in config:
            logger.warning(f"No key {self.config_key} in config")
            return

        config = config[self.config_key]

        try:

            self.manager.load_config(config)

            logger.info("Prompt configuration reloaded")

        except Exception as e:

            logger.error(f"Prompt configuration exception: {e}", exc_info=True)
            logger.error("Configuration reload failed")

    async def on_request(self, msg, consumer, flow):

        v = msg.value()

        # Sender-produced ID

        id = msg.properties()["id"]

        kind = v.id

        # Check if streaming is requested
        streaming = getattr(v, 'streaming', False)

        try:

            logger.debug(f"Prompt terms: {v.terms}")

            input = {
                k: json.loads(v)
                for k, v in v.terms.items()
            }

            logger.debug(f"Handling prompt kind {kind}... (streaming={streaming})")

            # If streaming, we need to handle it differently
            if streaming:
                # For streaming, we need to intercept LLM responses
                # and forward them as they arrive

                async def llm_streaming(system, prompt):
                    logger.debug(f"System prompt: {system}")
                    logger.debug(f"User prompt: {prompt}")

                    # Use the text completion client with recipient handler
                    client = flow("text-completion-request")

                    async def forward_chunks(resp):
                        if resp.error:
                            raise RuntimeError(resp.error.message)

                        if resp.response:
                            # Forward each chunk immediately
                            r = PromptResponse(
                                text=resp.response,
                                object=None,
                                error=None,
                                end_of_stream=getattr(resp, 'end_of_stream', False),
                            )
                            await flow("response").send(r, properties={"id": id})

                        # Return True when end_of_stream
                        return getattr(resp, 'end_of_stream', False)

                    await client.request(
                        TextCompletionRequest(
                            system=system, prompt=prompt, streaming=True
                        ),
                        recipient=forward_chunks,
                        timeout=600
                    )

                    # Return empty string since we already sent all chunks
                    return ""

                try:
                    await self.manager.invoke(kind, input, llm_streaming)
                except Exception as e:
                    logger.error(f"Prompt streaming exception: {e}", exc_info=True)
                    raise e

                return

            # Non-streaming path (original behavior)
            async def llm(system, prompt):

                logger.debug(f"System prompt: {system}")
                logger.debug(f"User prompt: {prompt}")

                resp = await flow("text-completion-request").text_completion(
                    system = system, prompt = prompt, streaming = False,
                )

                try:
                    return resp
                except Exception as e:
                    logger.error(f"LLM Exception: {e}", exc_info=True)
                    return None

            try:
                resp = await self.manager.invoke(kind, input, llm)
            except Exception as e:
                logger.error(f"Prompt invocation exception: {e}", exc_info=True)
                raise e

            logger.debug(f"Prompt response: {resp}")

            if isinstance(resp, str):

                logger.debug("Sending text response...")

                r = PromptResponse(
                    text=resp,
                    object=None,
                    error=None,
                    end_of_stream=True,
                )

                await flow("response").send(r, properties={"id": id})

                return

            else:

                logger.debug("Sending object response...")
                logger.debug(f"Response object: {json.dumps(resp, indent=4)}")

                r = PromptResponse(
                    text=None,
                    object=json.dumps(resp),
                    error=None,
                    end_of_stream=True,
                )

                await flow("response").send(r, properties={"id": id})

                return
            
        except Exception as e:

            logger.error(f"Prompt service exception: {e}", exc_info=True)

            logger.debug("Sending error response...")

            r = PromptResponse(
                error=Error(
                    type = "llm-error",
                    message = str(e),
                ),
                text=None,
                object=None,
                end_of_stream=True,
            )

            await flow("response").send(r, properties={"id": id})

    @staticmethod
    def add_args(parser):

        parser.add_argument(
            '-c', '--concurrency',
            type=int,
            default=default_concurrency,
            help=f'Concurrent processing threads (default: {default_concurrency})'
        )

        parser.add_argument(
            '--config-type',
            default="prompt",
            help=f'Configuration key for prompts (default: prompt)',
        )

        FlowProcessor.add_args(parser)

def run():

    Processor.launch(default_ident, __doc__)

