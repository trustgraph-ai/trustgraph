
import json
import asyncio

from . request_response_spec import RequestResponse, RequestResponseSpec
from .. schema import PromptRequest, PromptResponse

class PromptClient(RequestResponse):

    async def prompt(self, id, variables, timeout=600, streaming=False, chunk_callback=None):

        if not streaming:

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

            last_text = ""
            last_object = None

            async def forward_chunks(resp):
                nonlocal last_text, last_object

                if resp.error:
                    raise RuntimeError(resp.error.message)

                end_stream = getattr(resp, 'end_of_stream', False)

                if resp.text is not None:
                    last_text = resp.text
                    if chunk_callback:
                        if asyncio.iscoroutinefunction(chunk_callback):
                            await chunk_callback(resp.text, end_stream)
                        else:
                            chunk_callback(resp.text, end_stream)
                elif resp.object:
                    last_object = resp.object

                return end_stream

            req = PromptRequest(
                id = id,
                terms = {
                    k: json.dumps(v)
                    for k, v in variables.items()
                },
                streaming = True
            )

            await self.request(
                req,
                recipient=forward_chunks,
                timeout=timeout
            )

            if last_text:
                return last_text

            return json.loads(last_object) if last_object else None

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

    async def kg_prompt(self, query, kg, timeout=600, streaming=False, chunk_callback=None):
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
            streaming = streaming,
            chunk_callback = chunk_callback,
        )

    async def document_prompt(self, query, documents, timeout=600, streaming=False, chunk_callback=None):
        return await self.prompt(
            id = "document-prompt",
            variables = {
                "query": query,
                "documents": documents,
            },
            timeout = timeout,
            streaming = streaming,
            chunk_callback = chunk_callback,
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

