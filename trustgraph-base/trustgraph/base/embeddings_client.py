
from . request_response_spec import RequestResponse, RequestResponseSpec
from .. schema import EmbeddingsRequest, EmbeddingsResponse

class EmbeddingsClient(RequestResponse):
    async def embed(self, text, timeout=30):

        resp = await self.request(
            EmbeddingsRequest(
                text = text
            ),
            timeout=timeout
        )

        if resp.error:
            raise RuntimeError(resp.error.message)

        return resp.vectors

class EmbeddingsClientSpec(RequestResponseSpec):
    def __init__(
            self, request_name, response_name,
    ):
        super(EmbeddingsRequestResponseSpec, self).__init__(
            request_name = request_name,
            request_schema = EmbeddingsRequest,
            response_name = response_name,
            response_schema = EmbeddingsResponse,
            impl = EmbeddingsClient,
        )

