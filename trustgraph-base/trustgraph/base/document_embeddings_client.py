
from . request_response_spec import RequestResponse, RequestResponseSpec
from .. schema import DocumentEmbeddingsRequest, DocumentEmbeddingsResponse
from .. knowledge import Uri, Literal

class DocumentEmbeddingsClient(RequestResponse):
    async def query(self, vectors, limit=20, user="trustgraph",
                    collection="default", timeout=30):

        resp = await self.request(
            DocumentEmbeddingsRequest(
                vectors = vectors,
                limit = limit,
                user = user,
                collection = collection
            ),
            timeout=timeout
        )

        print(resp, flush=True)

        if resp.error:
            raise RuntimeError(resp.error.message)

        return resp.documents

class DocumentEmbeddingsClientSpec(RequestResponseSpec):
    def __init__(
            self, request_name, response_name,
    ):
        super(DocumentEmbeddingsClientSpec, self).__init__(
            request_name = request_name,
            request_schema = DocumentEmbeddingsRequest,
            response_name = response_name,
            response_schema = DocumentEmbeddingsResponse,
            impl = DocumentEmbeddingsClient,
        )

