
from . request_response_spec import RequestResponse, RequestResponseSpec
from .. schema import TextCompletionRequest, TextCompletionResponse

class TextCompletionClient(RequestResponse):
    async def text_completion(self, system, prompt, timeout=600):
        resp = await self.request(
            TextCompletionRequest(
                system = system, prompt = prompt
            ),
            timeout=timeout
        )

        if resp.error:
            raise RuntimeError(resp.error.message)

        return resp.response

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

