
import json
import asyncio
import logging

from . request_response_spec import RequestResponse, RequestResponseSpec
from .. schema import PromptRequest, PromptResponse

logger = logging.getLogger(__name__)

class PromptClient(RequestResponse):

    async def prompt(self, id, variables, timeout=600, streaming=False, chunk_callback=None):
        logger.info(f"DEBUG prompt_client: prompt called, id={id}, streaming={streaming}, chunk_callback={chunk_callback is not None}")

        if not streaming:
            logger.info("DEBUG prompt_client: Non-streaming path")
            # Non-streaming path
            resp = await self.request(
                PromptRequest(
                    id = id,
                    terms = {
                        k: json.dumps(v)
                        for k, v in variables.items()
                    },
                    streaming = False
                ),
                timeout=timeout
            )

            if resp.error:
                raise RuntimeError(resp.error.message)

            if resp.text: return resp.text

            return json.loads(resp.object)

        else:
            logger.info("DEBUG prompt_client: Streaming path")
            # Streaming path - collect all chunks
            full_text = ""
            full_object = None

            async def collect_chunks(resp):
                nonlocal full_text, full_object
                logger.info(f"DEBUG prompt_client: collect_chunks called, resp.text={resp.text[:50] if resp.text else None}, end_of_stream={getattr(resp, 'end_of_stream', False)}")

                if resp.error:
                    logger.error(f"DEBUG prompt_client: Error in response: {resp.error.message}")
                    raise RuntimeError(resp.error.message)

                if resp.text:
                    full_text += resp.text
                    logger.info(f"DEBUG prompt_client: Accumulated {len(full_text)} chars")
                    # Call chunk callback if provided
                    if chunk_callback:
                        logger.info(f"DEBUG prompt_client: Calling chunk_callback")
                        if asyncio.iscoroutinefunction(chunk_callback):
                            await chunk_callback(resp.text)
                        else:
                            chunk_callback(resp.text)
                elif resp.object:
                    logger.info(f"DEBUG prompt_client: Got object response")
                    full_object = resp.object

                end_stream = getattr(resp, 'end_of_stream', False)
                logger.info(f"DEBUG prompt_client: Returning end_of_stream={end_stream}")
                return end_stream

            logger.info("DEBUG prompt_client: Creating PromptRequest")
            req = PromptRequest(
                id = id,
                terms = {
                    k: json.dumps(v)
                    for k, v in variables.items()
                },
                streaming = True
            )
            logger.info(f"DEBUG prompt_client: About to call self.request with recipient, timeout={timeout}")
            await self.request(
                req,
                recipient=collect_chunks,
                timeout=timeout
            )
            logger.info(f"DEBUG prompt_client: self.request returned, full_text has {len(full_text)} chars")

            if full_text:
                logger.info("DEBUG prompt_client: Returning full_text")
                return full_text

            logger.info("DEBUG prompt_client: Returning parsed full_object")
            return json.loads(full_object)

    async def extract_definitions(self, text, timeout=600):
        return await self.prompt(
            id = "extract-definitions",
            variables = { "text": text },
            timeout = timeout,
        )

    async def extract_relationships(self, text, timeout=600):
        return await self.prompt(
            id = "extract-relationships",
            variables = { "text": text },
            timeout = timeout,
        )

    async def extract_objects(self, text, schema, timeout=600):
        return await self.prompt(
            id = "extract-rows",
            variables = { "text": text, "schema": schema, },
            timeout = timeout,
        )

    async def kg_prompt(self, query, kg, timeout=600):
        return await self.prompt(
            id = "kg-prompt",
            variables = {
                "query": query,
                "knowledge": [
                    { "s": v[0], "p": v[1], "o": v[2] }
                    for v in kg
                ]
            },
            timeout = timeout,
        )

    async def document_prompt(self, query, documents, timeout=600):
        return await self.prompt(
            id = "document-prompt",
            variables = {
                "query": query,
                "documents": documents,
            },
            timeout = timeout,
        )

    async def agent_react(self, variables, timeout=600, streaming=False, chunk_callback=None):
        return await self.prompt(
            id = "agent-react",
            variables = variables,
            timeout = timeout,
            streaming = streaming,
            chunk_callback = chunk_callback,
        )

    async def question(self, question, timeout=600):
        return await self.prompt(
            id = "question",
            variables = {
                "question": question,
            },
            timeout = timeout,
        )

class PromptClientSpec(RequestResponseSpec):
    def __init__(
            self, request_name, response_name,
    ):
        super(PromptClientSpec, self).__init__(
            request_name = request_name,
            request_schema = PromptRequest,
            response_name = response_name,
            response_schema = PromptResponse,
            impl = PromptClient,
        )

