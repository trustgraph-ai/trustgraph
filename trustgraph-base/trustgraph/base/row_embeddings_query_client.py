from . request_response_spec import RequestResponse, RequestResponseSpec
from .. schema import RowEmbeddingsRequest, RowEmbeddingsResponse

class RowEmbeddingsQueryClient(RequestResponse):
    async def row_embeddings_query(
            self, vectors, schema_name, user="trustgraph", collection="default",
            index_name=None, limit=10, timeout=600
    ):
        request = RowEmbeddingsRequest(
            vectors=vectors,
            schema_name=schema_name,
            user=user,
            collection=collection,
            limit=limit
        )
        if index_name:
            request.index_name = index_name

        resp = await self.request(request, timeout=timeout)

        if resp.error:
            raise RuntimeError(resp.error.message)

        # Return matches as list of dicts
        return [
            {
                "index_name": match.index_name,
                "index_value": match.index_value,
                "text": match.text,
                "score": match.score
            }
            for match in (resp.matches or [])
        ]

class RowEmbeddingsQueryClientSpec(RequestResponseSpec):
    def __init__(
            self, request_name, response_name,
    ):
        super(RowEmbeddingsQueryClientSpec, self).__init__(
            request_name = request_name,
            request_schema = RowEmbeddingsRequest,
            response_name = response_name,
            response_schema = RowEmbeddingsResponse,
            impl = RowEmbeddingsQueryClient,
        )
