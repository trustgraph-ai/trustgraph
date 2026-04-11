
import json
import asyncio
from dataclasses import dataclass
from typing import Optional, Any

from . request_response_spec import RequestResponse, RequestResponseSpec
from .. schema import PromptRequest, PromptResponse

@dataclass
class PromptResult:
    response_type: str              # "text", "json", or "jsonl"
    text: Optional[str] = None      # populated for "text"
    object: Any = None              # populated for "json"
    objects: Optional[list] = None  # populated for "jsonl"
    in_token: Optional[int] = None
    out_token: Optional[int] = None
    model: Optional[str] = None

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

            if resp.text:
                return PromptResult(
                    response_type="text",
                    text=resp.text,
                    in_token=resp.in_token,
                    out_token=resp.out_token,
                    model=resp.model,
                )

            parsed = json.loads(resp.object)

            if isinstance(parsed, list):
                return PromptResult(
                    response_type="jsonl",
                    objects=parsed,
                    in_token=resp.in_token,
                    out_token=resp.out_token,
                    model=resp.model,
                )

            return PromptResult(
                response_type="json",
                object=parsed,
                in_token=resp.in_token,
                out_token=resp.out_token,
                model=resp.model,
            )

        else:

            last_resp = None

            async def forward_chunks(resp):
                nonlocal last_resp

                if resp.error:
                    raise RuntimeError(resp.error.message)

                end_stream = getattr(resp, 'end_of_stream', False)

                if resp.text is not None:
                    if chunk_callback:
                        if asyncio.iscoroutinefunction(chunk_callback):
                            await chunk_callback(resp.text, end_stream)
                        else:
                            chunk_callback(resp.text, end_stream)

                last_resp = resp

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

            if last_resp is None:
                return PromptResult(response_type="text")

            if last_resp.object:
                parsed = json.loads(last_resp.object)

                if isinstance(parsed, list):
                    return PromptResult(
                        response_type="jsonl",
                        objects=parsed,
                        in_token=last_resp.in_token,
                        out_token=last_resp.out_token,
                        model=last_resp.model,
                    )

                return PromptResult(
                    response_type="json",
                    object=parsed,
                    in_token=last_resp.in_token,
                    out_token=last_resp.out_token,
                    model=last_resp.model,
                )

            return PromptResult(
                response_type="text",
                text=last_resp.text,
                in_token=last_resp.in_token,
                out_token=last_resp.out_token,
                model=last_resp.model,
            )

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
