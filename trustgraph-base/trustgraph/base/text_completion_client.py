
from . request_response_spec import RequestResponse, RequestResponseSpec
from .. schema import EmbeddingsReqeust, EmbeddingsResponse

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
        super(EmbeddingsRequestResponseSpec, self).__init__(
            request_name = request_name,
            request_schema = EmbeddingsRequest,
            response_name = response_name,
            response_schema = EmbeddingsResponse,
            impl = TextCompletionClient,
        )

