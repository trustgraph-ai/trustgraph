
import logging

from . request_response_spec import RequestResponse, RequestResponseSpec
from .. schema import GraphEmbeddingsRequest, GraphEmbeddingsResponse
from .. knowledge import Uri, Literal

# Module logger
logger = logging.getLogger(__name__)

def to_value(x):
    if x.is_uri: return Uri(x.value)
    return Literal(x.value)

class GraphEmbeddingsClient(RequestResponse):
    async def query(self, vectors, limit=20, user="trustgraph",
                    collection="default", timeout=30):

        resp = await self.request(
            GraphEmbeddingsRequest(
                vectors = vectors,
                limit = limit,
                user = user,
                collection = collection
            ),
            timeout=timeout
        )

        logger.debug(f"Graph embeddings response: {resp}")

        if resp.error:
            raise RuntimeError(resp.error.message)

        return [
            to_value(v)
            for v in resp.entities
        ]

class GraphEmbeddingsClientSpec(RequestResponseSpec):
    def __init__(
            self, request_name, response_name,
    ):
        super(GraphEmbeddingsClientSpec, self).__init__(
            request_name = request_name,
            request_schema = GraphEmbeddingsRequest,
            response_name = response_name,
            response_schema = GraphEmbeddingsResponse,
            impl = GraphEmbeddingsClient,
        )

