
from . request_response_spec import RequestResponse, RequestResponseSpec
from .. schema import TextCompletionRequest, TextCompletionResponse

class TextCompletionClient(RequestResponse):
    async def text_completion(self, system, prompt, streaming=False, timeout=600):
        # If not streaming, use original behavior
        if not streaming:
            resp = await self.request(
                TextCompletionRequest(
                    system = system, prompt = prompt, streaming = False
                ),
                timeout=timeout
            )

            if resp.error:
                raise RuntimeError(resp.error.message)

            return resp.response

        # For streaming: collect all chunks and return complete response
        full_response = ""

        async def collect_chunks(resp):
            nonlocal full_response

            if resp.error:
                raise RuntimeError(resp.error.message)

            if resp.response:
                full_response += resp.response

            # Return True when end_of_stream is reached
            return getattr(resp, 'end_of_stream', False)

        await self.request(
            TextCompletionRequest(
                system = system, prompt = prompt, streaming = True
            ),
            recipient=collect_chunks,
            timeout=timeout
        )

        return full_response

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

