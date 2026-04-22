
import logging

from . request_response_spec import RequestResponse, RequestResponseSpec
from .. schema import DocumentEmbeddingsRequest, DocumentEmbeddingsResponse
from .. knowledge import Uri, Literal

# Module logger
logger = logging.getLogger(__name__)

class DocumentEmbeddingsClient(RequestResponse):
    async def query(self, vector, limit=20, collection="default", timeout=30):

        resp = await self.request(
            DocumentEmbeddingsRequest(
                vector = vector,
                limit = limit,
                collection = collection
            ),
            timeout=timeout
        )

        logger.debug(f"Document embeddings response: {resp}")

        if resp.error:
            raise RuntimeError(resp.error.message)

        # Return ChunkMatch objects with chunk_id and score
        return resp.chunks

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

