
from dataclasses import dataclass
from typing import Optional

from . request_response_spec import RequestResponse, RequestResponseSpec
from .. schema import TextCompletionRequest, TextCompletionResponse

@dataclass
class TextCompletionResult:
    text: Optional[str]
    in_token: Optional[int] = None
    out_token: Optional[int] = None
    model: Optional[str] = None

class TextCompletionClient(RequestResponse):

    async def text_completion(self, system, prompt, timeout=600):

        resp = await self.request(
            TextCompletionRequest(
                system = system, prompt = prompt, streaming = False
            ),
            timeout=timeout
        )

        if resp.error:
            raise RuntimeError(resp.error.message)

        return TextCompletionResult(
            text = resp.response,
            in_token = resp.in_token,
            out_token = resp.out_token,
            model = resp.model,
        )

    async def text_completion_stream(
            self, system, prompt, handler, timeout=600,
    ):
        """
        Streaming text completion. `handler` is an async callable invoked
        once per chunk with the chunk's TextCompletionResponse. Returns a
        TextCompletionResult with text=None and token counts / model taken
        from the end_of_stream message.
        """

        async def on_chunk(resp):

            if resp.error:
                raise RuntimeError(resp.error.message)

            await handler(resp)

            return getattr(resp, "end_of_stream", False)

        final = await self.request(
            TextCompletionRequest(
                system = system, prompt = prompt, streaming = True
            ),
            recipient=on_chunk,
            timeout=timeout,
        )

        return TextCompletionResult(
            text = None,
            in_token = final.in_token,
            out_token = final.out_token,
            model = final.model,
        )

class TextCompletionClientSpec(RequestResponseSpec):
    def __init__(
            self, request_name, response_name,
    ):
        super(TextCompletionClientSpec, self).__init__(
            request_name = request_name,
            request_schema = TextCompletionRequest,
            response_name = response_name,
            response_schema = TextCompletionResponse,
            impl = TextCompletionClient,
        )
